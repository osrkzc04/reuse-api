"""
Modelos ORM para Sistema de Créditos con soporte para Soft Delete.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base, SoftDeleteMixin


# Enums
transaction_type_enum = ENUM('initial_grant', 'exchange_payment', 'exchange_received', 'reward_claim', 'admin_adjustment', 'refund', name='transaction_type', create_type=False)
claim_status_enum = ENUM('pending', 'approved', 'delivered', 'rejected', name='claim_status', create_type=False)


class CreditsLedger(Base, SoftDeleteMixin):
    """Modelo de Libro Mayor de Créditos con soporte para soft delete."""

    __tablename__ = "credits_ledger"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    transaction_type = Column(transaction_type_enum, nullable=False)
    amount = Column(Integer, nullable=False)
    balance_after = Column(Integer, nullable=False)
    reference_id = Column(UUID(as_uuid=True))
    description = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    # deleted_at viene del SoftDeleteMixin

    # Constraints
    __table_args__ = (
        CheckConstraint('balance_after >= 0', name='check_balance_positive'),
    )

    # Relationships
    user = relationship("User", back_populates="credits_transactions")

    def __repr__(self):
        return f"<CreditsLedger user={self.user_id} amount={self.amount} type={self.transaction_type}>"


class RewardsCatalog(Base, SoftDeleteMixin):
    """Modelo de Catálogo de Recompensas con soporte para soft delete."""

    __tablename__ = "rewards_catalog"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    credits_cost = Column(Integer, nullable=False)
    stock_quantity = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    image_url = Column(String(500))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Constraints
    __table_args__ = (
        CheckConstraint('credits_cost > 0', name='check_credits_cost_positive'),
        CheckConstraint('stock_quantity >= 0', name='check_stock_non_negative'),
    )

    # Relationships
    claims = relationship("RewardClaim", back_populates="reward")

    def __repr__(self):
        return f"<RewardsCatalog {self.name} - {self.credits_cost} créditos>"


class RewardClaim(Base, SoftDeleteMixin):
    """Modelo de Reclamaciones de Recompensas con soporte para soft delete."""

    __tablename__ = "reward_claims"

    id = Column(Integer, primary_key=True, index=True)
    reward_id = Column(Integer, ForeignKey("rewards_catalog.id", ondelete="RESTRICT"), nullable=False)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    credits_spent = Column(Integer, nullable=False)
    status = Column(claim_status_enum, default='pending')
    approved_at = Column(DateTime(timezone=True))
    delivered_at = Column(DateTime(timezone=True))
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    reward = relationship("RewardsCatalog", back_populates="claims")
    user = relationship("User", back_populates="reward_claims")

    def __repr__(self):
        return f"<RewardClaim user={self.user_id} reward={self.reward_id} status={self.status}>"
