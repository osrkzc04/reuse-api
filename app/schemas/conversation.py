"""
Schemas para conversaciones.
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID
from datetime import datetime


class ConversationResponse(BaseModel):
    """Schema de respuesta de conversación."""

    id: UUID
    offer_id: UUID
    user1_id: UUID
    user2_id: UUID
    is_active: bool
    created_at: datetime
    updated_at: datetime

    # Info adicional
    other_user_id: Optional[UUID] = None
    other_user_name: Optional[str] = None
    other_user_photo: Optional[str] = None
    offer_title: Optional[str] = None
    offer_photo: Optional[str] = None
    last_message: Optional[str] = None
    last_message_at: Optional[datetime] = None
    unread_count: int = 0

    model_config = {"from_attributes": True}
