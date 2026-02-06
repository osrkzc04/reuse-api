"""
Schemas para mensajes.
"""
from pydantic import BaseModel, Field
from uuid import UUID
from datetime import datetime
from typing import Optional


class MessageCreate(BaseModel):
    """Schema para crear mensaje."""

    content: str = Field(..., min_length=1, max_length=2000)

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    """Schema de respuesta de mensaje."""

    id: UUID
    conversation_id: UUID
    from_user_id: UUID
    content: str
    is_read: bool
    read_at: Optional[datetime] = None
    created_at: datetime

    # Info adicional
    from_user_name: Optional[str] = None
    from_user_photo: Optional[str] = None

    model_config = {"from_attributes": True}
