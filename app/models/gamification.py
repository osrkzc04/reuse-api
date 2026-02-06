"""
Modelos ORM para Gamificación (Challenges y Badges) con soporte para Soft Delete.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import ENUM, JSONB, UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base, SoftDeleteMixin


# Enums
challenge_frequency_enum = ENUM('weekly', 'monthly', 'special', 'permanent', name='challenge_frequency', create_type=False)
challenge_difficulty_enum = ENUM('easy', 'medium', 'hard', 'expert', name='challenge_difficulty', create_type=False)


class Challenge(Base, SoftDeleteMixin):
    """Modelo de Retos/Challenges con soporte para soft delete."""

    __tablename__ = "challenges"

    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    frequency = Column(challenge_frequency_enum, nullable=False)
    difficulty = Column(challenge_difficulty_enum, nullable=False)
    points_reward = Column(Integer, nullable=False)
    credits_reward = Column(Integer, default=0)
    badge_reward = Column(String(50))
    start_date = Column(DateTime(timezone=True), nullable=False)
    end_date = Column(DateTime(timezone=True), nullable=False)
    requirement_type = Column(String(50), nullable=False)
    requirement_value = Column(Integer, nullable=False)
    requirement_metadata = Column(JSONB)
    icon = Column(String(50))
    educational_content = Column(Text)
    is_active = Column(Boolean, default=True, index=True)
    participants_count = Column(Integer, default=0)
    completions_count = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Constraints
    __table_args__ = (
        CheckConstraint('points_reward > 0', name='check_points_reward_positive'),
    )

    # Relationships
    user_challenges = relationship("UserChallenge", back_populates="challenge", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Challenge {self.title} ({self.frequency})>"


class UserChallenge(Base, SoftDeleteMixin):
    """Modelo de Progreso de Retos por Usuario con soporte para soft delete."""

    __tablename__ = "user_challenges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    challenge_id = Column(Integer, ForeignKey("challenges.id", ondelete="CASCADE"), nullable=False)
    progress = Column(Integer, default=0)
    target = Column(Integer, nullable=False)
    is_completed = Column(Boolean, default=False, index=True)
    completed_at = Column(DateTime(timezone=True))
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    user = relationship("User", back_populates="challenges")
    challenge = relationship("Challenge", back_populates="user_challenges")

    def __repr__(self):
        return f"<UserChallenge user={self.user_id} challenge={self.challenge_id} progress={self.progress}/{self.target}>"

    @property
    def progress_percentage(self) -> float:
        """Calcular porcentaje de progreso."""
        if self.target == 0:
            return 0.0
        return min((self.progress / self.target) * 100, 100.0)


class BadgesCatalog(Base, SoftDeleteMixin):
    """Modelo de Catálogo de Insignias con soporte para soft delete."""

    __tablename__ = "badges_catalog"

    id = Column(String(50), primary_key=True)
    name = Column(String(100), nullable=False)
    description = Column(Text, nullable=False)
    icon = Column(String(100), nullable=False)
    category = Column(String(50), nullable=False)
    unlock_criteria = Column(Text, nullable=False)
    unlock_type = Column(String(50), nullable=False)
    unlock_value = Column(Integer, default=0)
    unlock_metadata = Column(JSONB)
    rarity = Column(String(20), default='common')
    points_value = Column(Integer, default=0)
    display_order = Column(Integer, default=0)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    user_badges = relationship("UserBadge", back_populates="badge", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<BadgesCatalog {self.name} ({self.rarity})>"


class UserBadge(Base, SoftDeleteMixin):
    """Modelo de Insignias Obtenidas por Usuario con soporte para soft delete."""

    __tablename__ = "user_badges"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    badge_id = Column(String(50), ForeignKey("badges_catalog.id", ondelete="CASCADE"), nullable=False)
    earned_at = Column(DateTime(timezone=True), server_default=func.now())
    progress = Column(Integer, default=100)
    is_displayed = Column(Boolean, default=True, index=True)
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    user = relationship("User", back_populates="badges")
    badge = relationship("BadgesCatalog", back_populates="user_badges")

    def __repr__(self):
        return f"<UserBadge user={self.user_id} badge={self.badge_id}>"
