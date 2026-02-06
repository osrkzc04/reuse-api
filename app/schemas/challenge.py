"""
Schemas para retos/challenges.
"""
from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from datetime import datetime


class ChallengeCreate(BaseModel):
    """Schema para crear challenge (admin)."""

    title: str = Field(..., min_length=1, max_length=200)
    description: str
    frequency: str = Field(..., pattern="^(weekly|monthly|special|permanent)$")
    difficulty: str = Field(..., pattern="^(easy|medium|hard|expert)$")
    points_reward: int = Field(..., gt=0)
    credits_reward: int = Field(default=0, ge=0)
    badge_reward: Optional[str] = None
    start_date: datetime
    end_date: datetime
    requirement_type: str
    requirement_value: int = Field(..., gt=0)
    requirement_metadata: Optional[Dict[str, Any]] = None
    icon: Optional[str] = None
    educational_content: Optional[str] = None

    model_config = {"from_attributes": True}


class ChallengeUpdate(BaseModel):
    """Schema para actualizar challenge (admin)."""

    title: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    points_reward: Optional[int] = Field(None, gt=0)
    credits_reward: Optional[int] = Field(None, ge=0)
    badge_reward: Optional[str] = None
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None
    icon: Optional[str] = None
    educational_content: Optional[str] = None
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}


class ChallengeResponse(BaseModel):
    """Schema de respuesta de challenge."""

    id: int
    title: str
    description: str
    frequency: str
    difficulty: str
    points_reward: int
    credits_reward: int
    badge_reward: Optional[str] = None
    start_date: datetime
    end_date: datetime
    requirement_type: str
    requirement_value: int
    requirement_metadata: Optional[Dict[str, Any]] = None
    icon: Optional[str] = None
    educational_content: Optional[str] = None
    is_active: bool
    participants_count: int
    completions_count: int

    model_config = {"from_attributes": True}


class UserChallengeResponse(BaseModel):
    """Schema de respuesta de progreso de challenge."""

    id: int
    user_id: str
    challenge_id: int
    progress: int
    target: int
    is_completed: bool
    completed_at: Optional[datetime] = None
    started_at: datetime

    # Info adicional del challenge
    challenge_title: Optional[str] = None
    challenge_description: Optional[str] = None
    challenge_icon: Optional[str] = None
    points_reward: Optional[int] = None

    model_config = {"from_attributes": True}

    @property
    def progress_percentage(self) -> float:
        """Calcular porcentaje de progreso."""
        if self.target == 0:
            return 0.0
        return min((self.progress / self.target) * 100, 100.0)
