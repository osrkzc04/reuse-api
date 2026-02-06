"""
Modelo ORM para Métricas de Reputación de Usuario.
"""
from sqlalchemy import Column, Integer, Numeric, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class UserReputationMetrics(Base):
    """Modelo de Métricas y Reputación de Usuario."""

    __tablename__ = "user_reputation_metrics"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    total_exchanges = Column(Integer, default=0)
    successful_exchanges = Column(Integer, default=0)
    average_rating = Column(Numeric(3, 2), default=0.00)
    total_ratings_received = Column(Integer, default=0)
    total_credits_earned = Column(Integer, default=0)
    total_credits_spent = Column(Integer, default=0)

    # Gamificación adicional
    total_interests_received = Column(Integer, default=0)
    total_interests_given = Column(Integer, default=0)
    current_streak = Column(Integer, default=0)
    longest_streak = Column(Integer, default=0)
    rank_in_faculty = Column(Integer)
    rank_overall = Column(Integer)
    favorite_category = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))

    badges = Column(JSONB, default=[])
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="reputation_metrics")

    def __repr__(self):
        return f"<UserReputationMetrics for user {self.user_id}>"

    @property
    def success_rate(self) -> float:
        """Calcular tasa de éxito de intercambios."""
        if self.total_exchanges == 0:
            return 0.0
        return (self.successful_exchanges / self.total_exchanges) * 100
