"""
Endpoints de administracion para gestion de usuarios y ofertas.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import Optional
from uuid import UUID

from app.core.deps import get_db, get_current_admin_user, get_current_superadmin_user
from app.models.user import User
from app.models.offer import Offer
from app.schemas.admin import (
    AdminUserResponse,
    AdminUserListResponse,
    AdminUserStatusUpdate,
    AdminUserRoleUpdate,
    AdminOfferResponse,
    AdminOfferListResponse,
    AdminOfferStatusUpdate,
)
from app.services.activity_log_service import log_activity, ActionTypes, EntityTypes

router = APIRouter()


# ================================================================
# GESTION DE USUARIOS
# ================================================================

@router.get("/users", response_model=AdminUserListResponse)
async def list_users(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    role: Optional[str] = Query(None, description="Filtrar por rol"),
    faculty_id: Optional[int] = Query(None, description="Filtrar por facultad"),
    search: Optional[str] = Query(None, description="Buscar por nombre o email"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Listar usuarios con filtros y paginacion.
    Requiere rol de administrador o moderador.
    """
    offset = (page - 1) * per_page

    # Construir query
    base_query = """
        SELECT
            u.id, u.email, u.full_name, u.faculty_id, u.role, u.status,
            u.sustainability_points, u.level, u.is_email_verified,
            u.last_login, u.created_at, u.updated_at,
            f.name as faculty_name,
            COALESCE((SELECT COUNT(*) FROM offers o WHERE o.user_id = u.id), 0) as total_offers,
            COALESCE((SELECT COUNT(*) FROM exchanges e WHERE e.buyer_id = u.id OR e.seller_id = u.id), 0) as total_exchanges
        FROM users u
        LEFT JOIN faculties f ON u.faculty_id = f.id
    """

    where_clauses = []
    params = {"limit": per_page, "offset": offset}

    if status:
        where_clauses.append("u.status = :status")
        params["status"] = status

    if role:
        where_clauses.append("u.role = :role")
        params["role"] = role

    if faculty_id:
        where_clauses.append("u.faculty_id = :faculty_id")
        params["faculty_id"] = faculty_id

    if search:
        where_clauses.append("(u.full_name ILIKE :search OR u.email ILIKE :search)")
        params["search"] = f"%{search}%"

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"{base_query} {where_sql} ORDER BY u.created_at DESC LIMIT :limit OFFSET :offset"
    count_query = f"SELECT COUNT(*) FROM users u {where_sql}"

    results = db.execute(text(query), params).fetchall()
    total = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]}).scalar()

    users = [
        AdminUserResponse(
            id=row.id,
            email=row.email,
            full_name=row.full_name,
            faculty_id=row.faculty_id,
            faculty_name=row.faculty_name,
            role=row.role,
            status=row.status,
            sustainability_points=row.sustainability_points,
            level=row.level,
            is_email_verified=row.is_email_verified,
            last_login=row.last_login,
            created_at=row.created_at,
            updated_at=row.updated_at,
            total_offers=row.total_offers,
            total_exchanges=row.total_exchanges
        )
        for row in results
    ]

    return AdminUserListResponse(
        data=users,
        total=total or 0,
        page=page,
        per_page=per_page
    )


@router.get("/users/{user_id}", response_model=AdminUserResponse)
async def get_user(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener detalle de un usuario.
    Requiere rol de administrador o moderador.
    """
    result = db.execute(
        text("""
            SELECT
                u.id, u.email, u.full_name, u.faculty_id, u.role, u.status,
                u.sustainability_points, u.level, u.is_email_verified,
                u.last_login, u.created_at, u.updated_at,
                f.name as faculty_name,
                COALESCE((SELECT COUNT(*) FROM offers o WHERE o.user_id = u.id), 0) as total_offers,
                COALESCE((SELECT COUNT(*) FROM exchanges e WHERE e.buyer_id = u.id OR e.seller_id = u.id), 0) as total_exchanges
            FROM users u
            LEFT JOIN faculties f ON u.faculty_id = f.id
            WHERE u.id = :user_id
        """),
        {"user_id": str(user_id)}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return AdminUserResponse(
        id=result.id,
        email=result.email,
        full_name=result.full_name,
        faculty_id=result.faculty_id,
        faculty_name=result.faculty_name,
        role=result.role,
        status=result.status,
        sustainability_points=result.sustainability_points,
        level=result.level,
        is_email_verified=result.is_email_verified,
        last_login=result.last_login,
        created_at=result.created_at,
        updated_at=result.updated_at,
        total_offers=result.total_offers,
        total_exchanges=result.total_exchanges
    )


@router.patch("/users/{user_id}/status", response_model=AdminUserResponse)
async def update_user_status(
    user_id: UUID,
    status_update: AdminUserStatusUpdate,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar status de un usuario.
    Requiere rol de administrador o moderador.
    """
    valid_statuses = ["active", "suspended", "banned", "pending_verification"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Status invalido. Valores permitidos: {valid_statuses}"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # No permitir modificar usuarios administradores si no eres superadmin
    if user.role == "administrador" and current_user.role != "administrador":
        raise HTTPException(
            status_code=403,
            detail="Solo administradores pueden modificar otros administradores"
        )

    old_status = user.status
    user.status = status_update.status
    db.commit()
    db.refresh(user)

    # Registrar actividad
    log_activity(
        db=db,
        action_type=ActionTypes.ADMIN_UPDATE_USER_STATUS,
        user_id=current_user.id,
        entity_type=EntityTypes.USER,
        entity_id=user_id,
        extra_data={"old_status": old_status, "new_status": status_update.status, "target_user_email": user.email},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    return await get_user(user_id, db, current_user)


@router.patch("/users/{user_id}/role", response_model=AdminUserResponse)
async def update_user_role(
    user_id: UUID,
    role_update: AdminUserRoleUpdate,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_superadmin_user)
):
    """
    Actualizar rol de un usuario.
    Requiere rol de SOLO administrador (no moderador).
    """
    valid_roles = ["estudiante", "moderador", "administrador"]
    if role_update.role not in valid_roles:
        raise HTTPException(
            status_code=400,
            detail=f"Rol invalido. Valores permitidos: {valid_roles}"
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # No permitir modificarse a si mismo
    if user.id == current_user.id:
        raise HTTPException(
            status_code=400,
            detail="No puedes modificar tu propio rol"
        )

    old_role = user.role
    user.role = role_update.role
    db.commit()
    db.refresh(user)

    # Registrar actividad
    log_activity(
        db=db,
        action_type=ActionTypes.ADMIN_UPDATE_USER_ROLE,
        user_id=current_user.id,
        entity_type=EntityTypes.USER,
        entity_id=user_id,
        extra_data={"old_role": old_role, "new_role": role_update.role, "target_user_email": user.email},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    return await get_user(user_id, db, current_user)


# ================================================================
# GESTION DE OFERTAS
# ================================================================

@router.get("/offers", response_model=AdminOfferListResponse)
async def list_offers(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    status: Optional[str] = Query(None, description="Filtrar por status"),
    category_id: Optional[int] = Query(None, description="Filtrar por categoria"),
    user_id: Optional[UUID] = Query(None, description="Filtrar por propietario"),
    search: Optional[str] = Query(None, description="Buscar por titulo"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Listar ofertas con filtros y paginacion.
    Requiere rol de administrador o moderador.
    """
    offset = (page - 1) * per_page

    base_query = """
        SELECT
            o.id, o.title, o.description, o.status, o.condition, o.credits_value,
            o.views_count, o.interests_count, o.is_featured, o.created_at, o.updated_at,
            u.id as owner_id, u.full_name as owner_name, u.email as owner_email,
            c.id as category_id, c.name as category_name,
            l.id as location_id, l.name as location_name,
            (SELECT photo_url FROM offer_photos op WHERE op.offer_id = o.id AND op.is_primary = TRUE AND op.deleted_at IS NULL LIMIT 1) as primary_photo_url
        FROM offers o
        JOIN users u ON o.user_id = u.id
        LEFT JOIN categories c ON o.category_id = c.id
        LEFT JOIN locations l ON o.location_id = l.id
    """

    where_clauses = []
    params = {"limit": per_page, "offset": offset}

    if status:
        where_clauses.append("o.status = :status")
        params["status"] = status

    if category_id:
        where_clauses.append("o.category_id = :category_id")
        params["category_id"] = category_id

    if user_id:
        where_clauses.append("o.user_id = :user_id")
        params["user_id"] = str(user_id)

    if search:
        where_clauses.append("o.title ILIKE :search")
        params["search"] = f"%{search}%"

    where_sql = " WHERE " + " AND ".join(where_clauses) if where_clauses else ""

    query = f"{base_query} {where_sql} ORDER BY o.created_at DESC LIMIT :limit OFFSET :offset"
    count_query = f"SELECT COUNT(*) FROM offers o {where_sql}"

    results = db.execute(text(query), params).fetchall()
    total = db.execute(text(count_query), {k: v for k, v in params.items() if k not in ["limit", "offset"]}).scalar()

    offers = [
        AdminOfferResponse(
            id=row.id,
            title=row.title,
            description=row.description,
            status=row.status,
            condition=row.condition,
            credits_value=row.credits_value,
            views_count=row.views_count,
            interests_count=row.interests_count,
            is_featured=row.is_featured,
            created_at=row.created_at,
            updated_at=row.updated_at,
            owner_id=row.owner_id,
            owner_name=row.owner_name,
            owner_email=row.owner_email,
            category_id=row.category_id,
            category_name=row.category_name,
            location_id=row.location_id,
            location_name=row.location_name,
            primary_photo_url=row.primary_photo_url
        )
        for row in results
    ]

    return AdminOfferListResponse(
        data=offers,
        total=total or 0,
        page=page,
        per_page=per_page
    )


@router.get("/offers/{offer_id}", response_model=AdminOfferResponse)
async def get_offer(
    offer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener detalle de una oferta.
    Requiere rol de administrador o moderador.
    """
    result = db.execute(
        text("""
            SELECT
                o.id, o.title, o.description, o.status, o.condition, o.credits_value,
                o.views_count, o.interests_count, o.is_featured, o.created_at, o.updated_at,
                u.id as owner_id, u.full_name as owner_name, u.email as owner_email,
                c.id as category_id, c.name as category_name,
                l.id as location_id, l.name as location_name,
                (SELECT photo_url FROM offer_photos op WHERE op.offer_id = o.id AND op.is_primary = TRUE AND op.deleted_at IS NULL LIMIT 1) as primary_photo_url
            FROM offers o
            JOIN users u ON o.user_id = u.id
            LEFT JOIN categories c ON o.category_id = c.id
            LEFT JOIN locations l ON o.location_id = l.id
            WHERE o.id = :offer_id
        """),
        {"offer_id": str(offer_id)}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    return AdminOfferResponse(
        id=result.id,
        title=result.title,
        description=result.description,
        status=result.status,
        condition=result.condition,
        credits_value=result.credits_value,
        views_count=result.views_count,
        interests_count=result.interests_count,
        is_featured=result.is_featured,
        created_at=result.created_at,
        updated_at=result.updated_at,
        owner_id=result.owner_id,
        owner_name=result.owner_name,
        owner_email=result.owner_email,
        category_id=result.category_id,
        category_name=result.category_name,
        location_id=result.location_id,
        location_name=result.location_name,
        primary_photo_url=result.primary_photo_url
    )


@router.patch("/offers/{offer_id}/status", response_model=AdminOfferResponse)
async def update_offer_status(
    offer_id: UUID,
    status_update: AdminOfferStatusUpdate,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar status de una oferta.
    Requiere rol de administrador o moderador.
    """
    valid_statuses = ["active", "reserved", "completed", "cancelled", "flagged"]
    if status_update.status not in valid_statuses:
        raise HTTPException(
            status_code=400,
            detail=f"Status invalido. Valores permitidos: {valid_statuses}"
        )

    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(status_code=404, detail="Oferta no encontrada")

    old_status = offer.status
    offer.status = status_update.status
    db.commit()
    db.refresh(offer)

    # Registrar actividad
    log_activity(
        db=db,
        action_type=ActionTypes.ADMIN_UPDATE_OFFER_STATUS,
        user_id=current_user.id,
        entity_type=EntityTypes.OFFER,
        entity_id=offer_id,
        extra_data={"old_status": old_status, "new_status": status_update.status, "offer_title": offer.title},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    return await get_offer(offer_id, db, current_user)
