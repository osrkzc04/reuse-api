"""
Schemas para estadísticas.
"""
from pydantic import BaseModel
from typing import Optional, Dict, Any
from datetime import datetime


class OfferStats(BaseModel):
    """Estadísticas de ofertas del usuario."""

    total_offers: int
    active_offers: int
    reserved_offers: int
    completed_offers: int
    cancelled_offers: int
    flagged_offers: int

    total_views: int
    avg_views_per_offer: float
    total_interests: int
    conversion_rate: float  # intereses que se convirtieron en intercambios

    model_config = {"from_attributes": True}


class ExchangeStats(BaseModel):
    """Estadísticas de intercambios del usuario."""

    # Como comprador
    total_as_buyer: int
    completed_as_buyer: int
    pending_as_buyer: int
    cancelled_as_buyer: int

    # Como vendedor
    total_as_seller: int
    completed_as_seller: int
    pending_as_seller: int
    cancelled_as_seller: int

    # General
    total_exchanges: int
    completed_exchanges: int
    success_rate: float  # porcentaje de intercambios completados
    avg_rating_received: Optional[float] = None
    total_ratings_received: int

    model_config = {"from_attributes": True}


class SustainabilityStats(BaseModel):
    """Estadísticas de sostenibilidad y gamificación."""

    # Puntos y nivel
    sustainability_points: int
    level: int
    experience_points: int
    points_to_next_level: int
    level_progress_percentage: float

    # Rankings
    rank_overall: Optional[int] = None
    rank_in_faculty: Optional[int] = None
    percentile_overall: Optional[float] = None
    percentile_in_faculty: Optional[float] = None

    # Gamificación
    total_badges: int
    total_challenges_joined: int
    total_challenges_completed: int
    challenges_completion_rate: float

    # Créditos
    current_credits_balance: int
    total_credits_earned: int
    total_credits_spent: int

    # Impacto ambiental estimado
    estimated_co2_saved_kg: float  # basado en intercambios
    estimated_waste_avoided_kg: float

    model_config = {"from_attributes": True}


class DashboardStats(BaseModel):
    """Dashboard completo del usuario."""

    # Información básica
    user_id: str
    user_name: str
    member_since: datetime
    last_active: Optional[datetime] = None

    # Estadísticas principales
    offers: OfferStats
    exchanges: ExchangeStats
    sustainability: SustainabilityStats

    # Métricas de actividad reciente (últimos 30 días)
    recent_activity: Dict[str, Any] = {
        "offers_created": 0,
        "exchanges_completed": 0,
        "messages_sent": 0,
        "sustainability_points_earned": 0
    }

    # Reputación
    trust_score: Optional[float] = None
    response_rate: Optional[float] = None
    avg_response_time_minutes: Optional[int] = None

    model_config = {"from_attributes": True}


class CategoryPopularity(BaseModel):
    """Estadística de popularidad de categoría."""

    category_id: int
    category_name: str
    total_offers: int
    active_offers: int
    total_exchanges: int
    avg_credits_value: float

    model_config = {"from_attributes": True}


class MonthlyActivity(BaseModel):
    """Actividad mensual del usuario."""

    month: str  # formato YYYY-MM
    offers_created: int
    exchanges_completed: int
    sustainability_points_earned: int
    challenges_completed: int

    model_config = {"from_attributes": True}


class ComparisonStats(BaseModel):
    """Comparación con otros usuarios."""

    metric_name: str
    my_value: float
    platform_average: float
    faculty_average: Optional[float] = None
    percentile: float  # donde estoy respecto a otros (0-100)

    model_config = {"from_attributes": True}
