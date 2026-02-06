"""
Schemas para los reportes del panel de administracion.
"""
from pydantic import BaseModel
from typing import Optional, List, Any, Dict
from uuid import UUID
from datetime import datetime


# ================================================================
# REPORTE DE TRANSACCIONES (Ofertas)
# ================================================================

class TransactionReportItem(BaseModel):
    """Schema de un item del reporte de transacciones."""

    id: UUID
    title: str
    description: Optional[str] = None
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
    category_id: Optional[int] = None
    category_name: Optional[str] = None

    # Ubicacion
    location_id: Optional[int] = None
    location_name: Optional[str] = None

    # Facultad del propietario
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None

    # Estadisticas de intercambio
    total_exchanges: int = 0
    completed_exchanges: int = 0

    # Fotos
    photos_count: int = 0
    primary_photo_url: Optional[str] = None

    model_config = {"from_attributes": True}


class TransactionReportResponse(BaseModel):
    """Schema de respuesta paginada del reporte de transacciones."""

    data: List[TransactionReportItem]
    total: int
    page: int
    per_page: int

    # Estadisticas resumidas
    summary: Optional[Dict[str, Any]] = None


# ================================================================
# REPORTE DE AUDITORIA (Activity Log)
# ================================================================

class AuditReportItem(BaseModel):
    """Schema de un item del reporte de auditoria."""

    id: int
    action_type: str
    entity_type: Optional[str] = None
    entity_id: Optional[UUID] = None
    extra_data: Optional[Dict[str, Any]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    # Usuario que realizo la accion
    user_id: Optional[UUID] = None
    user_name: Optional[str] = None
    user_email: Optional[str] = None
    user_role: Optional[str] = None
    user_faculty: Optional[str] = None

    model_config = {"from_attributes": True}


class AuditReportResponse(BaseModel):
    """Schema de respuesta paginada del reporte de auditoria."""

    data: List[AuditReportItem]
    total: int
    page: int
    per_page: int

    # Estadisticas resumidas
    summary: Optional[Dict[str, Any]] = None


# ================================================================
# REPORTE DE TRIGGERS (Audit History)
# ================================================================

class TriggerReportItem(BaseModel):
    """Schema de un item del reporte de triggers."""

    id: int
    table_name: str
    record_id: str
    operation: str
    old_data: Optional[Dict[str, Any]] = None
    new_data: Optional[Dict[str, Any]] = None
    changed_fields: Optional[List[str]] = None
    ip_address: Optional[str] = None
    user_agent: Optional[str] = None
    created_at: datetime

    # Usuario que realizo el cambio
    changed_by_id: Optional[UUID] = None
    changed_by_name: Optional[str] = None
    changed_by_email: Optional[str] = None
    changed_by_role: Optional[str] = None

    # Resumen
    operation_summary: Optional[str] = None
    hours_ago: Optional[float] = None

    model_config = {"from_attributes": True}


class TriggerReportResponse(BaseModel):
    """Schema de respuesta paginada del reporte de triggers."""

    data: List[TriggerReportItem]
    total: int
    page: int
    per_page: int

    # Estadisticas resumidas
    summary: Optional[Dict[str, Any]] = None


# ================================================================
# EXPORTACION CSV
# ================================================================

class ExportRequest(BaseModel):
    """Schema para solicitud de exportacion."""

    format: str = "csv"
    include_headers: bool = True
    date_from: Optional[datetime] = None
    date_to: Optional[datetime] = None
