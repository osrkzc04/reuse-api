"""
Endpoints de usuarios.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID

from app.core.deps import get_db, get_current_active_user, get_current_user_allow_unverified
from app.crud.user import user as crud_user
from app.schemas.user import UserResponse, UserUpdate, UserPublicProfile, UserStats
from app.models.user import User

router = APIRouter()


@router.get("/me", response_model=UserResponse)
def get_current_user_info(
    current_user: User = Depends(get_current_user_allow_unverified)
):
    """
    Obtener información del usuario actual.

    Requiere autenticación.
    Retorna toda la información del usuario autenticado.
    Permite usuarios con email no verificado para que el frontend
    pueda redirigirlos a la página de verificación.
    """
    return current_user


@router.put("/me", response_model=UserResponse)
def update_current_user(
    user_update: UserUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Actualizar información del usuario actual.

    Requiere autenticación.

    Campos actualizables:
    - full_name
    - faculty_id
    - whatsapp
    - whatsapp_visible
    - bio
    - profile_photo_url
    """
    updated_user = crud_user.update(db, db_obj=current_user, obj_in=user_update)
    return updated_user


@router.get("/{user_id}", response_model=UserPublicProfile)
def get_user_public_profile(
    user_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Obtener perfil público de un usuario.

    No requiere autenticación.
    Retorna solo información pública del usuario.
    """
    user = crud_user.get(db, id=user_id)

    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    # Construir perfil público
    from app.models.user_reputation_metrics import UserReputationMetrics

    metrics = db.query(UserReputationMetrics).filter(
        UserReputationMetrics.user_id == user_id
    ).first()

    return UserPublicProfile(
        id=user.id,
        full_name=user.full_name,
        faculty_id=user.faculty_id,
        profile_photo_url=user.profile_photo_url,
        bio=user.bio,
        sustainability_points=user.sustainability_points,
        level=user.level,
        total_exchanges=metrics.total_exchanges if metrics else 0,
        average_rating=float(metrics.average_rating) if metrics else 0.0,
        created_at=user.created_at
    )


@router.get("/me/stats", response_model=UserStats)
def get_current_user_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener estadísticas del usuario actual.

    Requiere autenticación.

    Retorna:
    - Estadísticas de ofertas
    - Estadísticas de intercambios
    - Puntos y nivel
    - Rankings
    - Badges
    """
    from app.models.offer import Offer
    from app.models.user_reputation_metrics import UserReputationMetrics
    from app.models.user_badge import UserBadge

    # Contar ofertas
    total_offers = db.query(Offer).filter(Offer.user_id == current_user.id).count()
    active_offers = db.query(Offer).filter(
        Offer.user_id == current_user.id,
        Offer.status == "active"
    ).count()

    # Obtener métricas
    metrics = db.query(UserReputationMetrics).filter(
        UserReputationMetrics.user_id == current_user.id
    ).first()

    # Contar badges
    badges_count = db.query(UserBadge).filter(UserBadge.user_id == current_user.id).count()

    if not metrics:
        # Crear métricas por defecto
        metrics = UserReputationMetrics(user_id=current_user.id)
        db.add(metrics)
        db.commit()

    return UserStats(
        total_offers=total_offers,
        active_offers=active_offers,
        total_exchanges=metrics.total_exchanges,
        successful_exchanges=metrics.successful_exchanges,
        success_rate=metrics.success_rate,
        average_rating=float(metrics.average_rating),
        total_ratings_received=metrics.total_ratings_received,
        sustainability_points=current_user.sustainability_points,
        level=current_user.level,
        badges_count=badges_count,
        rank_in_faculty=metrics.rank_in_faculty,
        rank_overall=metrics.rank_overall
    )
