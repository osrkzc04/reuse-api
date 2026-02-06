"""
Endpoints de notificaciones.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.core.deps import get_db, get_current_active_user
from app.crud.notification import notification as crud_notification
from app.schemas.notification import NotificationResponse, UnreadCountResponse
from app.schemas.common import MessageResponse
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[NotificationResponse])
def get_notifications(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener notificaciones del usuario actual.

    Requiere autenticacion.
    Retorna las 50 notificaciones mas recientes.
    """
    notifications = crud_notification.get_by_user(
        db, user_id=current_user.id, limit=50
    )
    return notifications


@router.get("/unread-count", response_model=UnreadCountResponse)
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener cantidad de notificaciones no leídas.

    Requiere autenticación.
    """
    count = crud_notification.get_unread_count(db, user_id=current_user.id)
    return UnreadCountResponse(unread_count=count)


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def mark_notification_as_read(
    notification_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Marcar notificación como leída.

    Requiere autenticación.
    Solo se pueden marcar las propias notificaciones.
    """
    notification = crud_notification.get(db, id=notification_id)

    if not notification:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificación no encontrada"
        )

    if str(notification.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para esta notificación"
        )

    updated_notification = crud_notification.mark_as_read(db, notification_id=notification_id)
    return updated_notification


@router.post("/mark-all-read", response_model=MessageResponse)
def mark_all_notifications_as_read(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Marcar todas las notificaciones como leídas.

    Requiere autenticación.
    """
    count = crud_notification.mark_all_as_read(db, user_id=current_user.id)
    return MessageResponse(
        message=f"{count} notificaciones marcadas como leídas"
    )
