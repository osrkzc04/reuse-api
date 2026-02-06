"""
CRUD para preferencias de usuario.
"""
from typing import Optional
from sqlalchemy.orm import Session
from uuid import UUID

from app.crud.base import CRUDBase
from app.models.user_preferences import UserPreferences


class CRUDUserPreferences(CRUDBase[UserPreferences, dict, dict]):
    """CRUD específico para preferencias de usuario."""

    def get_by_user_id(
        self, db: Session, *, user_id: UUID
    ) -> Optional[UserPreferences]:
        """
        Obtener preferencias de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Preferencias del usuario o None
        """
        return (
            db.query(UserPreferences)
            .filter(UserPreferences.user_id == user_id)
            .first()
        )

    def create_default(
        self, db: Session, *, user_id: UUID
    ) -> UserPreferences:
        """
        Crear preferencias por defecto para un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Preferencias creadas con valores por defecto
        """
        # Verificar que no existan ya
        existing = self.get_by_user_id(db, user_id=user_id)
        if existing:
            return existing

        new_prefs = UserPreferences(user_id=user_id)
        db.add(new_prefs)
        db.commit()
        db.refresh(new_prefs)
        return new_prefs

    def update_preferences(
        self,
        db: Session,
        *,
        user_id: UUID,
        preferences_data: dict
    ) -> UserPreferences:
        """
        Actualizar preferencias de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            preferences_data: Diccionario con los campos a actualizar

        Returns:
            Preferencias actualizadas
        """
        prefs = self.get_by_user_id(db, user_id=user_id)

        # Si no existen, crear con valores por defecto
        if not prefs:
            prefs = self.create_default(db, user_id=user_id)

        # Actualizar solo los campos proporcionados
        for field, value in preferences_data.items():
            if hasattr(prefs, field):
                setattr(prefs, field, value)

        db.commit()
        db.refresh(prefs)
        return prefs

    def reset_to_default(
        self, db: Session, *, user_id: UUID
    ) -> UserPreferences:
        """
        Restaurar preferencias a valores por defecto.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Preferencias restauradas
        """
        # Eliminar preferencias existentes
        db.query(UserPreferences).filter(
            UserPreferences.user_id == user_id
        ).delete()
        db.commit()

        # Crear nuevas preferencias por defecto
        return self.create_default(db, user_id=user_id)

    def update_notification_settings(
        self,
        db: Session,
        *,
        user_id: UUID,
        email_notifications: Optional[bool] = None,
        push_notifications: Optional[bool] = None,
        notify_new_messages: Optional[bool] = None,
        notify_interests: Optional[bool] = None,
        notify_exchanges: Optional[bool] = None,
        notify_challenges: Optional[bool] = None,
        notify_badges: Optional[bool] = None,
        notify_marketing: Optional[bool] = None
    ) -> UserPreferences:
        """
        Actualizar configuración de notificaciones.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            **kwargs: Configuraciones de notificaciones

        Returns:
            Preferencias actualizadas
        """
        notification_data = {}
        if email_notifications is not None:
            notification_data['email_notifications'] = email_notifications
        if push_notifications is not None:
            notification_data['push_notifications'] = push_notifications
        if notify_new_messages is not None:
            notification_data['notify_new_messages'] = notify_new_messages
        if notify_interests is not None:
            notification_data['notify_interests'] = notify_interests
        if notify_exchanges is not None:
            notification_data['notify_exchanges'] = notify_exchanges
        if notify_challenges is not None:
            notification_data['notify_challenges'] = notify_challenges
        if notify_badges is not None:
            notification_data['notify_badges'] = notify_badges
        if notify_marketing is not None:
            notification_data['notify_marketing'] = notify_marketing

        return self.update_preferences(
            db, user_id=user_id, preferences_data=notification_data
        )

    def update_privacy_settings(
        self,
        db: Session,
        *,
        user_id: UUID,
        profile_visibility: Optional[str] = None,
        show_email: Optional[bool] = None,
        show_whatsapp: Optional[bool] = None,
        show_stats: Optional[bool] = None,
        show_badges: Optional[bool] = None
    ) -> UserPreferences:
        """
        Actualizar configuración de privacidad.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            **kwargs: Configuraciones de privacidad

        Returns:
            Preferencias actualizadas
        """
        privacy_data = {}
        if profile_visibility is not None:
            privacy_data['profile_visibility'] = profile_visibility
        if show_email is not None:
            privacy_data['show_email'] = show_email
        if show_whatsapp is not None:
            privacy_data['show_whatsapp'] = show_whatsapp
        if show_stats is not None:
            privacy_data['show_stats'] = show_stats
        if show_badges is not None:
            privacy_data['show_badges'] = show_badges

        return self.update_preferences(
            db, user_id=user_id, preferences_data=privacy_data
        )


# Instancia global del CRUD
user_preferences = CRUDUserPreferences(UserPreferences)
