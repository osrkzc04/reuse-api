"""
Schemas para ofertas.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from enum import Enum


class OfferStatus(str, Enum):
    """Enum de estados de oferta."""
    active = "active"
    reserved = "reserved"
    completed = "completed"
    cancelled = "cancelled"
    flagged = "flagged"


class OfferCondition(str, Enum):
    """Enum de condición de oferta."""
    nuevo = "nuevo"
    como_nuevo = "como_nuevo"
    buen_estado = "buen_estado"
    usado = "usado"
    para_reparar = "para_reparar"


class OfferPhotoResponse(BaseModel):
    """Schema de respuesta de foto de oferta."""

    id: int
    photo_url: str
    is_primary: bool
    display_order: int

    model_config = {"from_attributes": True}


class OfferBase(BaseModel):
    """Schema base de oferta."""

    title: str = Field(..., min_length=5, max_length=200)
    description: str = Field(..., min_length=20)
    category_id: int
    condition: OfferCondition
    location_id: Optional[int] = None
    credits_value: int = Field(default=0, ge=0)

    model_config = {"from_attributes": True}


class OfferCreate(OfferBase):
    """Schema para crear oferta."""
    pass


class OfferUpdate(BaseModel):
    """Schema para actualizar oferta."""

    title: Optional[str] = Field(None, min_length=5, max_length=200)
    description: Optional[str] = Field(None, min_length=20)
    category_id: Optional[int] = None
    condition: Optional[OfferCondition] = None
    location_id: Optional[int] = None
    status: Optional[OfferStatus] = None
    credits_value: Optional[int] = Field(None, ge=0)

    model_config = {"from_attributes": True}


class OfferResponse(BaseModel):
    """Schema de respuesta de oferta."""

    id: UUID
    user_id: UUID
    title: str
    description: str
    category_id: int
    condition: str
    location_id: Optional[int] = None
    status: str
    credits_value: int
    views_count: int
    interests_count: int
    is_featured: bool

    # Relaciones
    photos: List[OfferPhotoResponse] = []

    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class OfferDetailResponse(OfferResponse):
    """Schema detallado de oferta (incluye info del usuario)."""

    user_name: Optional[str] = None
    user_photo: Optional[str] = None
    user_rating: Optional[float] = None
    category_name: Optional[str] = None
    location_name: Optional[str] = None

    model_config = {"from_attributes": True}


class CategoryResponse(BaseModel):
    """Schema de respuesta de categoría."""

    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    is_active: bool

    model_config = {"from_attributes": True}


class LocationResponse(BaseModel):
    """Schema de respuesta de ubicación."""

    id: int
    name: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: bool

    model_config = {"from_attributes": True}
