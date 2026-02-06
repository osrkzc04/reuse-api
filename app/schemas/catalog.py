"""
Schemas para catalogos (Facultades, Categorias, Ubicaciones).
"""
from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


# ================================================================
# FACULTADES
# ================================================================

class FacultyBase(BaseModel):
    """Schema base de facultad."""

    name: str = Field(..., min_length=2, max_length=200)
    code: str = Field(..., min_length=2, max_length=20)


class FacultyCreate(FacultyBase):
    """Schema para crear facultad."""
    pass


class FacultyUpdate(BaseModel):
    """Schema para actualizar facultad."""

    name: Optional[str] = Field(None, min_length=2, max_length=200)
    code: Optional[str] = Field(None, min_length=2, max_length=20)
    is_active: Optional[bool] = None


class FacultyResponse(BaseModel):
    """Schema de respuesta de facultad."""

    id: int
    name: str
    code: str
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class FacultyListResponse(BaseModel):
    """Schema de respuesta paginada de facultades."""

    data: List[FacultyResponse]
    total: int


# ================================================================
# CATEGORIAS
# ================================================================

class CategoryBase(BaseModel):
    """Schema base de categoria."""

    name: str = Field(..., min_length=2, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    icon: Optional[str] = Field(None, max_length=50)


class CategoryCreate(CategoryBase):
    """Schema para crear categoria."""
    pass


class CategoryUpdate(BaseModel):
    """Schema para actualizar categoria."""

    name: Optional[str] = Field(None, min_length=2, max_length=100)
    description: Optional[str] = None
    parent_id: Optional[int] = None
    icon: Optional[str] = Field(None, max_length=50)
    is_active: Optional[bool] = None


class CategoryResponse(BaseModel):
    """Schema de respuesta de categoria."""

    id: int
    name: str
    description: Optional[str] = None
    parent_id: Optional[int] = None
    icon: Optional[str] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class CategoryTreeResponse(CategoryResponse):
    """Schema de respuesta de categoria con hijos."""

    children: List["CategoryTreeResponse"] = []


class CategoryListResponse(BaseModel):
    """Schema de respuesta paginada de categorias."""

    data: List[CategoryResponse]
    total: int


# ================================================================
# UBICACIONES
# ================================================================

class LocationBase(BaseModel):
    """Schema base de ubicacion."""

    name: str = Field(..., min_length=2, max_length=200)
    description: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)


class LocationCreate(LocationBase):
    """Schema para crear ubicacion."""
    pass


class LocationUpdate(BaseModel):
    """Schema para actualizar ubicacion."""

    name: Optional[str] = Field(None, min_length=2, max_length=200)
    description: Optional[str] = None
    latitude: Optional[float] = Field(None, ge=-90, le=90)
    longitude: Optional[float] = Field(None, ge=-180, le=180)
    is_active: Optional[bool] = None


class LocationResponse(BaseModel):
    """Schema de respuesta de ubicacion."""

    id: int
    name: str
    description: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class LocationListResponse(BaseModel):
    """Schema de respuesta paginada de ubicaciones."""

    data: List[LocationResponse]
    total: int
