"""
Endpoints de preferencias de usuario.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_active_user
from app.schemas.preferences import UserPreferencesResponse, UserPreferencesUpdate
from app.schemas.common import MessageResponse
from app.models.user import User
from app.models.user_preferences import UserPreferences

router = APIRouter()


@router.get("/my", response_model=UserPreferencesResponse)
def get_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener mis preferencias actuales.

    Retorna todas las configuraciones de notificaciones, privacidad y preferencias generales.
    """
    preferences = (
        db.query(UserPreferences)
        .filter(UserPreferences.user_id == current_user.id)
        .first()
    )

    if not preferences:
        # Crear preferencias por defecto si no existen
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)
        db.commit()
        db.refresh(preferences)

    return UserPreferencesResponse.model_validate(preferences)


@router.patch("/my", response_model=UserPreferencesResponse)
def update_my_preferences(
    preferences_update: UserPreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Actualizar mis preferencias.

    Permite actualizar cualquier campo de las preferencias del usuario.
    Solo se actualizan los campos enviados (parcial).
    """
    preferences = (
        db.query(UserPreferences)
        .filter(UserPreferences.user_id == current_user.id)
        .first()
    )

    if not preferences:
        # Crear preferencias si no existen
        preferences = UserPreferences(user_id=current_user.id)
        db.add(preferences)

    # Actualizar campos proporcionados
    update_data = preferences_update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(preferences, field, value)

    db.commit()
    db.refresh(preferences)

    return UserPreferencesResponse.model_validate(preferences)


@router.post("/my/reset", response_model=MessageResponse)
def reset_my_preferences(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Restaurar preferencias a valores por defecto.

    Elimina las preferencias actuales y crea nuevas con valores predeterminados.
    """
    # Eliminar preferencias existentes
    db.query(UserPreferences).filter(
        UserPreferences.user_id == current_user.id
    ).delete()

    # Crear nuevas preferencias por defecto
    new_preferences = UserPreferences(user_id=current_user.id)
    db.add(new_preferences)
    db.commit()

    return MessageResponse(message="Preferencias restauradas a valores por defecto")
