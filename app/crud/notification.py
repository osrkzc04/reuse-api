"""
CRUD para notificaciones.
"""
from typing import List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from uuid import UUID
from datetime import datetime
from app.crud.base import CRUDBase
from app.models.notification import Notification
from app.schemas.notification import NotificationCreate
from pydantic import BaseModel


class NotificationUpdate(BaseModel):
    """Schema para actualizar notificación."""
    pass


class CRUDNotification(CRUDBase[Notification, NotificationCreate, NotificationUpdate]):
    """CRUD específico para notificaciones."""

    def get_by_user(
        self, db: Session, *, user_id: UUID, limit: int = 50
    ) -> List[Notification]:
        """
        Obtener notificaciones de un usuario.

        Args:
            db: Sesion de base de datos
            user_id: ID del usuario
            limit: Limite de registros (default 50)

        Returns:
            Lista de notificaciones
        """
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id)
            .order_by(desc(Notification.created_at))
            .limit(limit)
            .all()
        )

    def get_unread_count(self, db: Session, *, user_id: UUID) -> int:
        """
        Obtener cantidad de notificaciones no leídas.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Cantidad de notificaciones no leídas
        """
        return (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .count()
        )

    def mark_as_read(self, db: Session, *, notification_id: UUID) -> Notification:
        """
        Marcar notificación como leída.

        Args:
            db: Sesión de base de datos
            notification_id: ID de la notificación

        Returns:
            Notificación actualizada
        """
        notification = self.get(db, id=notification_id)
        if notification and not notification.is_read:
            notification.is_read = True
            notification.read_at = datetime.utcnow()
            db.commit()
            db.refresh(notification)
        return notification

    def mark_all_as_read(self, db: Session, *, user_id: UUID) -> int:
        """
        Marcar todas las notificaciones de un usuario como leídas.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Cantidad de notificaciones marcadas
        """
        updated = (
            db.query(Notification)
            .filter(Notification.user_id == user_id, Notification.is_read == False)
            .update({"is_read": True, "read_at": datetime.utcnow()})
        )
        db.commit()
        return updated


# Instancia global del CRUD
notification = CRUDNotification(Notification)
