"""
Schemas para el panel de administracion.
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from uuid import UUID
from datetime import datetime


# ================================================================
# GESTION DE USUARIOS
# ================================================================

class AdminUserResponse(BaseModel):
    """Schema de respuesta de usuario para admin."""

    id: UUID
    email: str
    full_name: str
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None
    role: str
    status: str
    sustainability_points: int
    level: int
    is_email_verified: bool
    last_login: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Estadisticas resumidas
    total_offers: int = 0
    total_exchanges: int = 0

    model_config = {"from_attributes": True}


class AdminUserListResponse(BaseModel):
    """Schema de respuesta paginada de usuarios para admin."""

    data: List[AdminUserResponse]
    total: int
    page: int
    per_page: int


class AdminUserStatusUpdate(BaseModel):
    """Schema para actualizar status de usuario."""

    status: str = Field(..., description="Nuevo status: active, suspended, banned")


class AdminUserRoleUpdate(BaseModel):
    """Schema para actualizar rol de usuario."""

    role: str = Field(..., description="Nuevo rol: estudiante, moderador, administrador")


# ================================================================
# GESTION DE OFERTAS
# ================================================================

class AdminOfferResponse(BaseModel):
    """Schema de respuesta de oferta para admin."""

    id: UUID
    title: str
    description: str
    status: str
    condition: str
    credits_value: int
    views_count: int
    interests_count: int
    is_featured: bool
    created_at: datetime
    updated_at: Optional[datetime] = None

    # Propietario
    owner_id: UUID
    owner_name: str
    owner_email: str

    # Categoria
    category_id: int
    category_name: str

    # Ubicacion
    location_id: Optional[int] = None
    location_name: Optional[str] = None

    # Foto principal
    primary_photo_url: Optional[str] = None

    model_config = {"from_attributes": True}


class AdminOfferListResponse(BaseModel):
    """Schema de respuesta paginada de ofertas para admin."""

    data: List[AdminOfferResponse]
    total: int
    page: int
    per_page: int


class AdminOfferStatusUpdate(BaseModel):
    """Schema para actualizar status de oferta."""

    status: str = Field(..., description="Nuevo status: active, reserved, completed, cancelled, flagged")
    reason: Optional[str] = Field(None, description="Razon del cambio de status")
