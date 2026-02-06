"""
Schemas para notificaciones.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class NotificationResponse(BaseModel):
    """Schema de respuesta de notificación."""

    id: UUID
    user_id: UUID
    type: str
    title: str
    content: Optional[str] = None
    reference_id: Optional[UUID] = None
    reference_type: Optional[str] = None
    is_read: bool
    read_at: Optional[datetime] = None
    action_url: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class NotificationCreate(BaseModel):
    """Schema para crear notificación."""

    user_id: UUID
    type: str
    title: str
    content: Optional[str] = None
    reference_id: Optional[UUID] = None
    reference_type: Optional[str] = None
    action_url: Optional[str] = None
    extra_data: Optional[Dict[str, Any]] = None

    model_config = {"from_attributes": True}


class UnreadCountResponse(BaseModel):
    """Schema de respuesta de contador de no leídas."""

    unread_count: int

    model_config = {"from_attributes": True}
