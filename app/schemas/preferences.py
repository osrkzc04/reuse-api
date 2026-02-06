"""
Schemas para preferencias de usuario.
"""
from pydantic import BaseModel
from typing import Optional, List, Dict, Any


class UserPreferencesResponse(BaseModel):
    """Schema de respuesta de preferencias."""

    # Notificaciones
    email_notifications: bool
    push_notifications: bool
    notify_new_messages: bool
    notify_interests: bool
    notify_exchanges: bool
    notify_challenges: bool
    notify_badges: bool
    notify_marketing: bool

    # Privacidad
    profile_visibility: str
    show_email: bool
    show_whatsapp: bool
    show_stats: bool
    show_badges: bool

    # Preferencias
    language: str
    theme: str
    items_per_page: int
    saved_filters: List[Dict[str, Any]] = []

    model_config = {"from_attributes": True}


class UserPreferencesUpdate(BaseModel):
    """Schema para actualizar preferencias."""

    # Notificaciones
    email_notifications: Optional[bool] = None
    push_notifications: Optional[bool] = None
    notify_new_messages: Optional[bool] = None
    notify_interests: Optional[bool] = None
    notify_exchanges: Optional[bool] = None
    notify_challenges: Optional[bool] = None
    notify_badges: Optional[bool] = None
    notify_marketing: Optional[bool] = None

    # Privacidad
    profile_visibility: Optional[str] = None
    show_email: Optional[bool] = None
    show_whatsapp: Optional[bool] = None
    show_stats: Optional[bool] = None
    show_badges: Optional[bool] = None

    # Preferencias
    language: Optional[str] = None
    theme: Optional[str] = None
    items_per_page: Optional[int] = None
    saved_filters: Optional[List[Dict[str, Any]]] = None

    model_config = {"from_attributes": True}
