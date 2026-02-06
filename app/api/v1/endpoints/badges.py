"""
Endpoints de insignias/badges de gamificacion.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import Optional, List

from app.core.deps import get_db, get_current_active_user
from app.crud.badge import badge as crud_badge
from app.schemas.badge import BadgeResponse, UserBadgeResponse
from app.schemas.common import MessageResponse
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[BadgeResponse])
def get_badges(
    db: Session = Depends(get_db)
):
    """
    Obtener catalogo de insignias disponibles.

    No requiere autenticacion.
    Retorna las 50 insignias activas.
    """
    badges = crud_badge.get_active_badges(db, limit=50)
    return [BadgeResponse.model_validate(b) for b in badges]


@router.get("/{badge_id}", response_model=BadgeResponse)
def get_badge(
    badge_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtener detalle de una insignia específica.
    """
    badge = crud_badge.get(db, id=badge_id)

    if not badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insignia no encontrada"
        )

    return BadgeResponse.model_validate(badge)


@router.get("/users/{user_id}/badges", response_model=List[UserBadgeResponse])
def get_user_badges(
    user_id: str,
    db: Session = Depends(get_db)
):
    """
    Obtener insignias de un usuario especifico.

    Endpoint publico.
    Retorna las 50 insignias mas recientes del usuario.
    """
    from uuid import UUID

    try:
        user_uuid = UUID(user_id)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="ID de usuario invalido"
        )

    # Verificar que el usuario existe
    user = db.query(User).filter(User.id == user_uuid).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    user_badges = crud_badge.get_user_badges(db, user_id=user_uuid, limit=50)

    # Enriquecer respuesta con info del badge
    enriched_badges = []
    for ub in user_badges:
        badge = crud_badge.get(db, id=ub.badge_id)

        response = UserBadgeResponse.model_validate(ub)
        response.badge_name = badge.name if badge else None
        response.badge_description = badge.description if badge else None
        response.badge_icon = badge.icon if badge else None
        response.badge_rarity = badge.rarity if badge else None

        enriched_badges.append(response)

    return enriched_badges


@router.get("/my/badges", response_model=List[UserBadgeResponse])
def get_my_badges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener mis insignias.

    Requiere autenticacion.
    Retorna las 50 insignias mas recientes.
    """
    user_badges = crud_badge.get_user_badges(db, user_id=current_user.id, limit=50)

    # Enriquecer respuesta
    enriched_badges = []
    for ub in user_badges:
        badge = crud_badge.get(db, id=ub.badge_id)

        response = UserBadgeResponse.model_validate(ub)
        response.badge_name = badge.name if badge else None
        response.badge_description = badge.description if badge else None
        response.badge_icon = badge.icon if badge else None
        response.badge_rarity = badge.rarity if badge else None

        enriched_badges.append(response)

    return enriched_badges


@router.patch("/my/badges/{user_badge_id}/toggle", response_model=MessageResponse)
def toggle_badge_display(
    user_badge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Alternar visibilidad de una insignia en el perfil.

    Permite mostrar u ocultar una insignia en el perfil público.
    """
    from app.models.gamification import UserBadge

    # Verificar que la insignia pertenece al usuario
    user_badge = db.query(UserBadge).filter(
        UserBadge.id == user_badge_id,
        UserBadge.user_id == current_user.id
    ).first()

    if not user_badge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Insignia no encontrada"
        )

    # Toggle display
    user_badge_updated = crud_badge.toggle_display(db, user_badge_id=user_badge_id)

    status_msg = "visible" if user_badge_updated.is_displayed else "oculta"
    return MessageResponse(message=f"Insignia ahora {status_msg} en tu perfil")
