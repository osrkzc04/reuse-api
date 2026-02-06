"""
Modelo ORM para Usuarios.
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base, SoftDeleteMixin


# Enums
user_role_enum = ENUM('estudiante', 'moderador', 'administrador', name='user_role', create_type=False)
user_status_enum = ENUM('active', 'suspended', 'banned', 'pending_verification', name='user_status', create_type=False)


class User(Base, SoftDeleteMixin):
    """Modelo de Usuarios del sistema con soporte para soft delete."""

    __tablename__ = "users"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email = Column(String(255), nullable=False, unique=True, index=True)
    password_hash = Column(String(255), nullable=False)
    full_name = Column(String(200), nullable=False)
    faculty_id = Column(Integer, ForeignKey("faculties.id", ondelete="SET NULL"))
    role = Column(user_role_enum, default='estudiante')
    status = Column(user_status_enum, default='pending_verification', index=True)
    whatsapp = Column(String(20))
    whatsapp_visible = Column(Boolean, default=False)
    profile_photo_url = Column(String(500))
    bio = Column(Text)

    # Gamificación
    sustainability_points = Column(Integer, default=0, index=True)
    level = Column(Integer, default=1)
    experience_points = Column(Integer, default=0)

    is_email_verified = Column(Boolean, default=False)
    last_login = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Constraints
    __table_args__ = (
        CheckConstraint('sustainability_points >= 0', name='check_points_positive'),
        CheckConstraint('level >= 1', name='check_level_positive'),
    )

    # Relationships
    faculty = relationship("Faculty", back_populates="users")
    offers = relationship("Offer", back_populates="user", foreign_keys="Offer.user_id")
    offer_interests = relationship("OfferInterest", back_populates="user")
    refresh_tokens = relationship("RefreshToken", back_populates="user", cascade="all, delete-orphan")
    email_verification_tokens = relationship("EmailVerificationToken", back_populates="user", cascade="all, delete-orphan")
    preferences = relationship("UserPreferences", back_populates="user", uselist=False, cascade="all, delete-orphan")
    reputation_metrics = relationship("UserReputationMetrics", back_populates="user", uselist=False, cascade="all, delete-orphan")
    notifications = relationship("Notification", back_populates="user", cascade="all, delete-orphan")
    badges = relationship("UserBadge", back_populates="user", cascade="all, delete-orphan")
    challenges = relationship("UserChallenge", back_populates="user", cascade="all, delete-orphan")
    credits_transactions = relationship("CreditsLedger", back_populates="user", cascade="all, delete-orphan")
    reward_claims = relationship("RewardClaim", back_populates="user", cascade="all, delete-orphan")

    # Exchanges
    exchanges_as_buyer = relationship("Exchange", back_populates="buyer", foreign_keys="Exchange.buyer_id")
    exchanges_as_seller = relationship("Exchange", back_populates="seller", foreign_keys="Exchange.seller_id")

    # Messages
    messages_sent = relationship("Message", back_populates="from_user", foreign_keys="Message.from_user_id")

    def __repr__(self):
        return f"<User {self.email}>"

    def is_active(self) -> bool:
        """Verificar si el usuario está activo."""
        return self.status == "active"

    def is_admin(self) -> bool:
        """Verificar si el usuario es administrador."""
        return self.role in ["administrador", "moderador"]
