"""
Schemas para insignias/badges.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class BadgeCreate(BaseModel):
    """Schema para crear badge (admin)."""

    id: str = Field(..., min_length=1, max_length=50)
    name: str = Field(..., min_length=1, max_length=100)
    description: str
    icon: str = Field(..., max_length=100)
    category: str = Field(..., max_length=50)
    unlock_criteria: str
    unlock_type: str = Field(..., max_length=50)
    unlock_value: int = Field(default=0, ge=0)
    unlock_metadata: Optional[Dict[str, Any]] = None
    rarity: str = Field(default='common', max_length=20)
    points_value: int = Field(default=0, ge=0)
    display_order: int = Field(default=0, ge=0)

    model_config = {"from_attributes": True}


class BadgeUpdate(BaseModel):
    """Schema para actualizar badge (admin)."""

    name: Optional[str] = Field(None, min_length=1, max_length=100)
    description: Optional[str] = None
    icon: Optional[str] = Field(None, max_length=100)
    unlock_criteria: Optional[str] = None
    unlock_value: Optional[int] = Field(None, ge=0)
    unlock_metadata: Optional[Dict[str, Any]] = None
    points_value: Optional[int] = Field(None, ge=0)
    display_order: Optional[int] = Field(None, ge=0)
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}


class BadgeResponse(BaseModel):
    """Schema de respuesta de badge del catálogo."""

    id: str
    name: str
    description: str
    icon: str
    category: str
    unlock_criteria: str
    unlock_type: str
    unlock_value: int
    unlock_metadata: Optional[Dict[str, Any]] = None
    rarity: str
    points_value: int
    is_active: bool

    model_config = {"from_attributes": True}


class UserBadgeResponse(BaseModel):
    """Schema de respuesta de badge obtenido por usuario."""

    id: int
    user_id: str
    badge_id: str
    earned_at: datetime
    progress: int
    is_displayed: bool

    # Info del badge
    badge_name: Optional[str] = None
    badge_description: Optional[str] = None
    badge_icon: Optional[str] = None
    badge_rarity: Optional[str] = None
    points_value: Optional[int] = None

    model_config = {"from_attributes": True}
