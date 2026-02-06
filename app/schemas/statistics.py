"""
Schemas para Estadísticas y Dashboard.
"""
from pydantic import BaseModel
from typing import Optional, List, Any
from datetime import datetime
from uuid import UUID
from decimal import Decimal


# ================================================================
# DASHBOARD ADMIN
# ================================================================

class AdminDashboard(BaseModel):
    """Estadísticas del dashboard de administrador."""
    # Usuarios
    total_active_users: int
    pending_verification_users: int
    new_users_week: int
    new_users_month: int
    # Ofertas
    total_active_offers: int
    flagged_offers: int
    new_offers_week: int
    # Intercambios
    total_completed_exchanges: int
    pending_exchanges: int
    disputed_exchanges: int
    exchanges_completed_week: int
    # Moderación
    pending_flags: int
    # Créditos
    total_credits_issued: int
    # Sostenibilidad
    total_sustainability_points: int


# ================================================================
# LEADERBOARD
# ================================================================

class LeaderboardEntry(BaseModel):
    """Entrada del leaderboard."""
    id: UUID
    full_name: str
    profile_photo_url: Optional[str] = None
    faculty_name: Optional[str] = None
    sustainability_points: int
    level: int
    total_exchanges: int
    successful_exchanges: int
    average_rating: Decimal
    overall_rank: int
    faculty_rank: int

    class Config:
        from_attributes = True


class LeaderboardResponse(BaseModel):
    """Respuesta del leaderboard."""
    data: List[LeaderboardEntry]
    total: int
    page: int
    per_page: int


# ================================================================
# ESTADÍSTICAS DE USUARIO
# ================================================================

class UserExchangeStats(BaseModel):
    """Estadísticas de intercambios de usuario."""
    total_exchanges: int
    completed_exchanges: int
    cancelled_exchanges: int
    success_rate: Decimal


class UserRanking(BaseModel):
    """Ranking de usuario."""
    user_id: UUID
    full_name: str
    sustainability_points: int
    rank_overall: int
    rank_faculty: int
    faculty_name: Optional[str] = None


class EnvironmentalImpact(BaseModel):
    """Impacto ambiental estimado."""
    total_items_exchanged: int
    estimated_kg_co2_saved: Decimal
    estimated_kg_waste_avoided: Decimal
    equivalent_trees_planted: Decimal


class UserCreditsBalance(BaseModel):
    """Balance de créditos de usuario."""
    current_balance: int
    total_earned: int
    total_spent: int
    last_transaction_at: Optional[datetime] = None


# ================================================================
# ESTADÍSTICAS DE CATEGORÍAS
# ================================================================

class CategoryStats(BaseModel):
    """Estadísticas por categoría."""
    category_id: int
    category_name: str
    total_offers: int
    active_offers: int
    completed_exchanges: int
    avg_credits_value: Decimal


# ================================================================
# MÉTRICAS DE INTERCAMBIOS
# ================================================================

class ExchangeMetrics(BaseModel):
    """Métricas de intercambios por mes."""
    month: datetime
    total_exchanges: int
    completed: int
    cancelled: int
    disputed: int
    completion_rate: Optional[Decimal] = None
    avg_days_to_complete: Optional[Decimal] = None
    total_credits_exchanged: Optional[int] = None


# ================================================================
# SALUD DE OFERTAS
# ================================================================

class OffersHealth(BaseModel):
    """Salud de ofertas por categoría."""
    category_id: int
    category_name: str
    total_offers: int
    active_offers: int
    completed_offers: int
    cancelled_offers: int
    flagged_offers: int
    expired_offers: int
    offers_last_month: int
    avg_views: Optional[Decimal] = None
    avg_interests: Optional[Decimal] = None


# ================================================================
# ACTIVIDAD RECIENTE
# ================================================================

class RecentActivity(BaseModel):
    """Actividad reciente del sistema."""
    activity_type: str
    entity_id: str
    description: str
    user_id: UUID
    user_name: str
    created_at: datetime


# ================================================================
# PROGRESO DE RETOS
# ================================================================

class ChallengeProgress(BaseModel):
    """Progreso de retos."""
    id: int
    title: str
    description: str
    frequency: str
    difficulty: str
    points_reward: int
    credits_reward: int
    start_date: datetime
    end_date: datetime
    requirement_type: str
    requirement_value: int
    total_participants: int
    completions: int
    completion_rate: Optional[Decimal] = None
    challenge_status: str


# ================================================================
# COLA DE MODERACIÓN
# ================================================================

class ModerationQueueItem(BaseModel):
    """Item de la cola de moderación."""
    id: int
    flag_type: str
    description: str
    status: str
    created_at: datetime
    reporter_id: UUID
    reporter_name: str
    reporter_email: str
    offer_id: Optional[UUID] = None
    offer_title: Optional[str] = None
    offer_owner_id: Optional[UUID] = None
    offer_owner_name: Optional[str] = None
    exchange_id: Optional[UUID] = None
    exchange_status: Optional[str] = None
    hours_in_queue: float


# ================================================================
# ANÁLISIS DE CRÉDITOS
# ================================================================

class CreditsAnalysis(BaseModel):
    """Análisis de créditos por mes y tipo."""
    month: datetime
    transaction_type: str
    transaction_count: int
    total_amount: int
    avg_amount: int


# ================================================================
# RESUMEN DE FACULTADES
# ================================================================

class FacultySummary(BaseModel):
    """Resumen por facultad."""
    id: int
    name: str
    code: str
    total_users: int
    active_users: int
    total_points: Optional[int] = None
    avg_points_per_user: Optional[Decimal] = None
    total_offers: int
    completed_exchanges: int
    faculty_rank: int


# ================================================================
# USUARIOS INACTIVOS
# ================================================================

class InactiveUser(BaseModel):
    """Usuario inactivo."""
    user_id: UUID
    email: str
    full_name: str
    last_activity: datetime
    days_inactive: int


# ================================================================
# AUDITORÍA
# ================================================================

class AuditHistoryEntry(BaseModel):
    """Entrada del historial de auditoría."""
    id: int
    table_name: str
    record_id: str
    operation: str
    old_data: Optional[dict] = None
    new_data: Optional[dict] = None
    changed_fields: Optional[List[str]] = None
    changed_by: Optional[UUID] = None
    ip_address: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class AuditHistoryResponse(BaseModel):
    """Respuesta de historial de auditoría."""
    data: List[AuditHistoryEntry]
    total: int
    page: int
    per_page: int
