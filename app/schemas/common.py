"""
Schemas comunes reutilizables.
"""
from pydantic import BaseModel
from typing import Generic, TypeVar, List, Optional


T = TypeVar('T')


class PaginatedResponse(BaseModel, Generic[T]):
    """Schema de respuesta paginada."""

    items: List[T]
    total: int
    skip: int
    limit: int
    has_more: bool = False

    model_config = {"from_attributes": True}

    def __init__(self, **data):
        super().__init__(**data)
        # Calcular has_more automáticamente
        self.has_more = (self.skip + self.limit) < self.total


class MessageResponse(BaseModel):
    """Schema de respuesta con mensaje simple."""

    message: str
    success: bool = True

    model_config = {"from_attributes": True}


class ErrorResponse(BaseModel):
    """Schema de respuesta de error."""

    detail: str
    error_code: Optional[str] = None

    model_config = {"from_attributes": True}


class SuccessResponse(BaseModel):
    """Schema de respuesta exitosa genérica."""

    success: bool = True
    message: Optional[str] = None
    data: Optional[dict] = None

    model_config = {"from_attributes": True}
