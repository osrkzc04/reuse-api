"""
Schemas para intereses en ofertas.
"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class OfferInterestCreate(BaseModel):
    """Schema para crear interés en oferta."""

    notes: Optional[str] = Field(None, max_length=500)

    model_config = {"from_attributes": True}


class OfferInterestResponse(BaseModel):
    """Schema de respuesta de interés."""

    id: int
    offer_id: UUID
    user_id: UUID
    conversation_id: Optional[UUID] = None
    status: str
    notes: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class OfferInterestDetailResponse(OfferInterestResponse):
    """Schema detallado de interés (incluye info de oferta y usuario)."""

    offer_title: Optional[str] = None
    offer_photo: Optional[str] = None
    user_name: Optional[str] = None
    user_photo: Optional[str] = None

    model_config = {"from_attributes": True}
