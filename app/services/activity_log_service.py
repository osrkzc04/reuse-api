"""
Servicio de registro de actividad (auditoría).
"""
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, Any
from fastapi import Request

from app.models.moderation import ActivityLog


def log_activity(
    db: Session,
    action_type: str,
    user_id: Optional[UUID] = None,
    entity_type: Optional[str] = None,
    entity_id: Optional[UUID] = None,
    extra_data: Optional[dict] = None,
    ip_address: Optional[str] = None,
    user_agent: Optional[str] = None,
) -> ActivityLog:
    """
    Registra una actividad en el log de auditoría.

    Args:
        db: Sesión de base de datos
        action_type: Tipo de acción (ej: 'LOGIN', 'CREATE_OFFER', 'EXCHANGE_COMPLETED')
        user_id: ID del usuario que realiza la acción
        entity_type: Tipo de entidad afectada (ej: 'offer', 'exchange', 'user')
        entity_id: ID de la entidad afectada
        extra_data: Datos adicionales en formato JSON
        ip_address: Dirección IP del cliente
        user_agent: User-Agent del navegador/cliente

    Returns:
        ActivityLog: El registro de actividad creado
    """
    activity = ActivityLog(
        user_id=user_id,
        action_type=action_type,
        entity_type=entity_type,
        entity_id=entity_id,
        extra_data=extra_data,
        ip_address=ip_address,
        user_agent=user_agent,
    )
    db.add(activity)
    db.commit()
    db.refresh(activity)
    return activity


def extract_client_info(request: Request) -> tuple[Optional[str], Optional[str]]:
    """
    Extrae información del cliente desde la request.

    Args:
        request: Request de FastAPI

    Returns:
        Tupla con (ip_address, user_agent)
    """
    # Obtener IP (considerando proxies)
    ip_address = None
    if request:
        # Verificar headers de proxy primero
        forwarded_for = request.headers.get("X-Forwarded-For")
        if forwarded_for:
            # Tomar la primera IP (cliente original)
            ip_address = forwarded_for.split(",")[0].strip()
        else:
            ip_address = request.client.host if request.client else None

    # Obtener User-Agent
    user_agent = None
    if request:
        user_agent = request.headers.get("User-Agent")

    return ip_address, user_agent


# Constantes de tipos de acción para consistencia
class ActionTypes:
    """Tipos de acción para el log de actividad."""

    # Auth
    LOGIN = "LOGIN"
    LOGIN_FAILED = "LOGIN_FAILED"
    LOGOUT = "LOGOUT"
    REGISTER = "REGISTER"
    PASSWORD_RESET = "PASSWORD_RESET"
    EMAIL_VERIFIED = "EMAIL_VERIFIED"

    # Offers
    CREATE_OFFER = "CREATE_OFFER"
    UPDATE_OFFER = "UPDATE_OFFER"
    DELETE_OFFER = "DELETE_OFFER"
    VIEW_OFFER = "VIEW_OFFER"

    # Exchanges
    CREATE_EXCHANGE = "CREATE_EXCHANGE"
    ACCEPT_EXCHANGE = "ACCEPT_EXCHANGE"
    REJECT_EXCHANGE = "REJECT_EXCHANGE"
    CONFIRM_EXCHANGE = "CONFIRM_EXCHANGE"
    CANCEL_EXCHANGE = "CANCEL_EXCHANGE"
    COMPLETE_EXCHANGE = "COMPLETE_EXCHANGE"
    RATE_EXCHANGE = "RATE_EXCHANGE"

    # Messages
    SEND_MESSAGE = "SEND_MESSAGE"
    START_CONVERSATION = "START_CONVERSATION"

    # Challenges
    JOIN_CHALLENGE = "JOIN_CHALLENGE"
    COMPLETE_CHALLENGE = "COMPLETE_CHALLENGE"

    # Admin
    ADMIN_UPDATE_USER = "ADMIN_UPDATE_USER"
    ADMIN_UPDATE_USER_STATUS = "ADMIN_UPDATE_USER_STATUS"
    ADMIN_UPDATE_USER_ROLE = "ADMIN_UPDATE_USER_ROLE"
    ADMIN_UPDATE_OFFER_STATUS = "ADMIN_UPDATE_OFFER_STATUS"
    ADMIN_DELETE_OFFER = "ADMIN_DELETE_OFFER"

    # Notifications
    MARK_NOTIFICATION_READ = "MARK_NOTIFICATION_READ"
    MARK_ALL_NOTIFICATIONS_READ = "MARK_ALL_NOTIFICATIONS_READ"


class EntityTypes:
    """Tipos de entidad para el log de actividad."""
    USER = "user"
    OFFER = "offer"
    EXCHANGE = "exchange"
    MESSAGE = "message"
    CONVERSATION = "conversation"
    CHALLENGE = "challenge"
    NOTIFICATION = "notification"
    BADGE = "badge"
