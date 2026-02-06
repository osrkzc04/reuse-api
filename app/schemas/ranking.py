"""
Schemas para ranking.
"""
from pydantic import BaseModel
from typing import Optional
from uuid import UUID


class RankingEntry(BaseModel):
    """Schema de entrada en el ranking."""

    rank: int
    user_id: UUID
    user_name: str
    user_photo: Optional[str] = None
    faculty_id: Optional[int] = None
    faculty_name: Optional[str] = None
    sustainability_points: int
    level: int
    total_exchanges: int
    badges_count: int

    model_config = {"from_attributes": True}


class RankingResponse(BaseModel):
    """Schema de respuesta de ranking."""

    entries: list[RankingEntry]
    total_users: int
    my_rank: Optional[int] = None
    ranking_type: str  # 'general' o 'faculty'

    model_config = {"from_attributes": True}


class MyPositionResponse(BaseModel):
    """Schema de mi posición en el ranking."""

    rank_overall: Optional[int] = None
    rank_in_faculty: Optional[int] = None
    total_users: int
    total_users_in_faculty: Optional[int] = None
    percentile_overall: Optional[float] = None
    percentile_in_faculty: Optional[float] = None

    model_config = {"from_attributes": True}
