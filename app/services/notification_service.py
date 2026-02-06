"""
Servicio de notificaciones.
Crea y gestiona notificaciones para usuarios.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session

from app.models.notification import Notification
from app.models.user_preferences import UserPreferences


def create_notification(
    db: Session,
    user_id: UUID,
    notification_type: str,
    title: str,
    content: Optional[str] = None,
    reference_id: Optional[UUID] = None,
    reference_type: Optional[str] = None,
    action_url: Optional[str] = None,
    extra_data: Optional[Dict[str, Any]] = None
) -> Optional[Notification]:
    """
    Crear notificación para un usuario.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        notification_type: Tipo de notificación
        title: Título
        content: Contenido
        reference_id: ID de referencia
        reference_type: Tipo de referencia
        action_url: URL de acción
        extra_data: Datos adicionales en formato JSON

    Returns:
        Notificación creada o None si el usuario no acepta notificaciones
    """
    # Verificar preferencias de notificación del usuario
    preferences = db.query(UserPreferences).filter(
        UserPreferences.user_id == user_id
    ).first()

    # Si no se deben enviar notificaciones de este tipo, retornar None
    if preferences and not should_send_notification(preferences, notification_type):
        return None

    notification = Notification(
        user_id=user_id,
        type=notification_type,
        title=title,
        content=content,
        reference_id=reference_id,
        reference_type=reference_type,
        action_url=action_url,
        extra_data=extra_data
    )

    db.add(notification)
    db.commit()
    db.refresh(notification)

    return notification


def should_send_notification(preferences: UserPreferences, notification_type: str) -> bool:
    """
    Verificar si se debe enviar una notificación según preferencias.

    Args:
        preferences: Preferencias del usuario
        notification_type: Tipo de notificación

    Returns:
        True si se debe enviar, False en caso contrario
    """
    type_mapping = {
        "new_message": preferences.notify_new_messages,
        "new_interest": preferences.notify_interests,
        "exchange_update": preferences.notify_exchanges,
        "exchange_confirmed": preferences.notify_exchanges,
        "exchange_completed": preferences.notify_exchanges,
        "challenge_completed": preferences.notify_challenges,
        "badge_earned": preferences.notify_badges,
        "marketing": preferences.notify_marketing,
    }

    return type_mapping.get(notification_type, True)


def notify_new_interest(db: Session, offer_owner_id: UUID, interested_user_name: str, offer_title: str, offer_id: UUID):
    """Notificar al dueño de la oferta sobre un nuevo interés."""
    create_notification(
        db=db,
        user_id=offer_owner_id,
        notification_type="new_interest",
        title="¡Nuevo interés en tu oferta!",
        content=f"{interested_user_name} está interesado en '{offer_title}'",
        reference_id=offer_id,
        reference_type="offer",
        action_url=f"/offers/{offer_id}"
    )


def notify_new_message(db: Session, recipient_id: UUID, sender_name: str, conversation_id: UUID):
    """Notificar al usuario sobre un nuevo mensaje."""
    create_notification(
        db=db,
        user_id=recipient_id,
        notification_type="new_message",
        title="Nuevo mensaje",
        content=f"Tienes un nuevo mensaje de {sender_name}",
        reference_id=conversation_id,
        reference_type="conversation",
        action_url=f"/conversations/{conversation_id}"
    )


def notify_exchange_confirmed(db: Session, user_id: UUID, exchange_id: UUID):
    """Notificar sobre confirmación de intercambio."""
    create_notification(
        db=db,
        user_id=user_id,
        notification_type="exchange_confirmed",
        title="Intercambio confirmado",
        content="El intercambio ha sido confirmado por ambas partes",
        reference_id=exchange_id,
        reference_type="exchange",
        action_url=f"/exchanges/{exchange_id}"
    )


def notify_badge_earned(db: Session, user_id: UUID, badge_name: str, badge_id: str):
    """Notificar sobre insignia ganada."""
    create_notification(
        db=db,
        user_id=user_id,
        notification_type="badge_earned",
        title="¡Nueva insignia!",
        content=f"¡Felicidades! Has ganado la insignia '{badge_name}'",
        reference_id=None,
        reference_type="badge",
        extra_data={"badge_id": badge_id}
    )


def notify_challenge_completed(db: Session, user_id: UUID, challenge_title: str, points_reward: int):
    """Notificar sobre reto completado."""
    create_notification(
        db=db,
        user_id=user_id,
        notification_type="challenge_completed",
        title="¡Reto completado!",
        content=f"Has completado '{challenge_title}' y ganado {points_reward} puntos",
        reference_type="challenge"
    )


def notify_exchange_created(db: Session, seller_id: UUID, buyer_name: str, offer_title: str, exchange_id: UUID):
    """Notificar al vendedor sobre una nueva propuesta de intercambio."""
    create_notification(
        db=db,
        user_id=seller_id,
        notification_type="exchange_update",
        title="Nueva propuesta de intercambio",
        content=f"{buyer_name} quiere intercambiar por '{offer_title}'",
        reference_id=exchange_id,
        reference_type="exchange",
        action_url=f"/exchanges/{exchange_id}"
    )


def notify_exchange_accepted(db: Session, buyer_id: UUID, offer_title: str, exchange_id: UUID):
    """Notificar al comprador que su propuesta fue aceptada."""
    create_notification(
        db=db,
        user_id=buyer_id,
        notification_type="exchange_update",
        title="¡Propuesta aceptada!",
        content=f"Tu propuesta por '{offer_title}' ha sido aceptada",
        reference_id=exchange_id,
        reference_type="exchange",
        action_url=f"/exchanges/{exchange_id}"
    )


def notify_exchange_cancelled(db: Session, user_id: UUID, offer_title: str, cancelled_by: str, exchange_id: UUID):
    """Notificar que el intercambio fue cancelado."""
    create_notification(
        db=db,
        user_id=user_id,
        notification_type="exchange_update",
        title="Intercambio cancelado",
        content=f"El intercambio por '{offer_title}' fue cancelado por {cancelled_by}",
        reference_id=exchange_id,
        reference_type="exchange",
        action_url=f"/exchanges/{exchange_id}"
    )


def notify_exchange_completed(db: Session, user_id: UUID, offer_title: str, exchange_id: UUID, points_earned: int):
    """Notificar que el intercambio se completó exitosamente."""
    create_notification(
        db=db,
        user_id=user_id,
        notification_type="exchange_completed",
        title="¡Intercambio completado!",
        content=f"El intercambio por '{offer_title}' se completó. +{points_earned} puntos de sostenibilidad",
        reference_id=exchange_id,
        reference_type="exchange",
        action_url=f"/exchanges/{exchange_id}"
    )


def notify_level_up(db: Session, user_id: UUID, new_level: int):
    """Notificar al usuario que subió de nivel."""
    create_notification(
        db=db,
        user_id=user_id,
        notification_type="badge_earned",  # Usamos badge_earned porque es similar
        title=f"¡Subiste al nivel {new_level}!",
        content=f"¡Felicidades! Has alcanzado el nivel {new_level}. Sigue contribuyendo a la sostenibilidad.",
        reference_type="level",
        extra_data={"level": new_level}
    )
