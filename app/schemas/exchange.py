"""
Schemas para intercambios.
"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime
from enum import Enum


class ExchangeStatus(str, Enum):
    """Enum de estados de intercambio."""
    pending = "pending"
    accepted = "accepted"
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"
    disputed = "disputed"


class ExchangeCreate(BaseModel):
    """Schema para crear intercambio."""

    offer_id: UUID
    location_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ExchangeUpdate(BaseModel):
    """Schema para actualizar intercambio."""

    location_id: Optional[int] = None
    scheduled_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    model_config = {"from_attributes": True}


class ExchangeConfirm(BaseModel):
    """Schema para confirmar intercambio."""

    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class ExchangeResponse(BaseModel):
    """Schema de respuesta de intercambio."""

    id: UUID
    offer_id: UUID
    buyer_id: UUID
    seller_id: UUID
    location_id: Optional[int] = None
    status: str
    credits_amount: int

    buyer_confirmed: bool
    seller_confirmed: bool
    buyer_confirmed_at: Optional[datetime] = None
    seller_confirmed_at: Optional[datetime] = None

    scheduled_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    cancellation_reason: Optional[str] = None

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class ExchangeDetailResponse(ExchangeResponse):
    """Schema detallado de intercambio."""

    offer_title: Optional[str] = None
    offer_photo: Optional[str] = None
    buyer_name: Optional[str] = None
    buyer_photo: Optional[str] = None
    seller_name: Optional[str] = None
    seller_photo: Optional[str] = None
    location_name: Optional[str] = None

    model_config = {"from_attributes": True}


class ExchangeRatingCreate(BaseModel):
    """Schema para crear valoración de intercambio."""

    rating: int = Field(..., ge=1, le=5)
    comment: Optional[str] = Field(None, max_length=500)

    model_config = {"from_attributes": True}


class ExchangeRatingResponse(BaseModel):
    """Schema de respuesta de valoración."""

    id: int
    exchange_id: UUID
    rater_user_id: UUID
    rated_user_id: UUID
    rating: int
    comment: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}
