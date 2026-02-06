"""
Schemas para Recompensas y Créditos.
"""
from pydantic import BaseModel, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class RewardBase(BaseModel):
    """Schema base de recompensa."""

    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = None
    credits_cost: int = Field(..., gt=0)
    stock_quantity: int = Field(default=0, ge=0)
    image_url: Optional[str] = Field(None, max_length=500)

    model_config = {"from_attributes": True}


class RewardCreate(RewardBase):
    """Schema para crear recompensa."""
    pass


class RewardUpdate(BaseModel):
    """Schema para actualizar recompensa."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    description: Optional[str] = None
    credits_cost: Optional[int] = Field(None, gt=0)
    stock_quantity: Optional[int] = Field(None, ge=0)
    image_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None

    model_config = {"from_attributes": True}


class RewardResponse(RewardBase):
    """Schema de respuesta de recompensa."""

    id: int
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = {"from_attributes": True}


class RewardClaimCreate(BaseModel):
    """Schema para reclamar una recompensa."""

    reward_id: int = Field(..., gt=0)


class RewardClaimResponse(BaseModel):
    """Schema de respuesta de reclamación."""

    id: int
    reward_id: int
    user_id: UUID
    credits_spent: int
    status: str
    approved_at: Optional[datetime] = None
    delivered_at: Optional[datetime] = None
    notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    # Datos anidados de la recompensa
    reward: Optional[RewardResponse] = None

    model_config = {"from_attributes": True}


class RewardClaimUpdate(BaseModel):
    """Schema para actualizar estado de reclamación (admin)."""

    status: str = Field(..., pattern="^(pending|approved|delivered|rejected)$")
    notes: Optional[str] = None

    model_config = {"from_attributes": True}


class CreditsLedgerResponse(BaseModel):
    """Schema de respuesta de transacción de créditos."""

    id: int
    user_id: UUID
    transaction_type: str
    amount: int
    balance_after: int
    reference_id: Optional[UUID] = None
    description: Optional[str] = None
    created_at: datetime

    model_config = {"from_attributes": True}


class CreditsBalance(BaseModel):
    """Schema de balance de créditos del usuario."""

    current_balance: int
    total_earned: int
    total_spent: int
    recent_transactions: list[CreditsLedgerResponse]

    model_config = {"from_attributes": True}
