"""
Schemas para usuarios.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserBase(BaseModel):
    """Schema base de usuario."""

    email: EmailStr
    full_name: str = Field(..., min_length=2, max_length=200)
    faculty_id: Optional[int] = None
    whatsapp: Optional[str] = Field(None, max_length=20)
    bio: Optional[str] = None

    model_config = {"from_attributes": True}


class UserCreate(UserBase):
    """Schema para crear usuario."""

    password: str = Field(..., min_length=8)


class UserUpdate(BaseModel):
    """Schema para actualizar usuario."""

    full_name: Optional[str] = Field(None, min_length=2, max_length=200)
    faculty_id: Optional[int] = None
    whatsapp: Optional[str] = Field(None, max_length=20)
    whatsapp_visible: Optional[bool] = None
    bio: Optional[str] = None
    profile_photo_url: Optional[str] = None

    model_config = {"from_attributes": True}


class UserResponse(BaseModel):
    """Schema de respuesta de usuario."""

    id: UUID
    email: EmailStr
    full_name: str
    faculty_id: Optional[int] = None
    role: str
    status: str
    whatsapp: Optional[str] = None
    whatsapp_visible: bool
    profile_photo_url: Optional[str] = None
    bio: Optional[str] = None

    # Gamificación
    sustainability_points: int
    level: int
    experience_points: int

    is_email_verified: bool
    created_at: datetime

    model_config = {"from_attributes": True}


class UserPublicProfile(BaseModel):
    """Schema de perfil público de usuario (sin datos sensibles)."""

    id: UUID
    full_name: str
    faculty_id: Optional[int] = None
    profile_photo_url: Optional[str] = None
    bio: Optional[str] = None

    # Gamificación pública
    sustainability_points: int
    level: int

    # Estadísticas (si el usuario las hace públicas)
    total_exchanges: Optional[int] = None
    average_rating: Optional[float] = None

    created_at: datetime

    model_config = {"from_attributes": True}


class UserStats(BaseModel):
    """Schema de estadísticas de usuario."""

    total_offers: int
    active_offers: int
    total_exchanges: int
    successful_exchanges: int
    success_rate: float
    average_rating: float
    total_ratings_received: int
    sustainability_points: int
    level: int
    badges_count: int
    rank_in_faculty: Optional[int] = None
    rank_overall: Optional[int] = None

    model_config = {"from_attributes": True}


class FacultyResponse(BaseModel):
    """Schema de respuesta de facultad."""

    id: int
    name: str
    code: str
    is_active: bool

    model_config = {"from_attributes": True}
