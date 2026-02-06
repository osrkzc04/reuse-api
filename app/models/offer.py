"""
Modelo ORM para Ofertas.
"""
from sqlalchemy import Column, String, Integer, Boolean, DateTime, ForeignKey, CheckConstraint, Text
from sqlalchemy.dialects.postgresql import UUID, ENUM
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base, SoftDeleteMixin


# Enums
offer_status_enum = ENUM('active', 'reserved', 'completed', 'cancelled', 'flagged', name='offer_status', create_type=False)
offer_condition_enum = ENUM('nuevo', 'como_nuevo', 'buen_estado', 'usado', 'para_reparar', name='offer_condition', create_type=False)


class Offer(Base, SoftDeleteMixin):
    """Modelo de Ofertas (objetos publicados) con soporte para soft delete."""

    __tablename__ = "offers"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    category_id = Column(Integer, ForeignKey("categories.id", ondelete="RESTRICT"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    description = Column(Text, nullable=False)
    condition = Column(offer_condition_enum, nullable=False)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"))
    status = Column(offer_status_enum, default='active', index=True)
    credits_value = Column(Integer, default=0)
    views_count = Column(Integer, default=0)

    # Campos adicionales
    is_featured = Column(Boolean, default=False)
    featured_until = Column(DateTime(timezone=True))
    interests_count = Column(Integer, default=0)
    expires_at = Column(DateTime(timezone=True))

    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Constraints
    __table_args__ = (
        CheckConstraint('credits_value >= 0', name='check_credits_value_positive'),
    )

    # Relationships
    user = relationship("User", back_populates="offers", foreign_keys=[user_id])
    category = relationship("Category", back_populates="offers")
    location = relationship("Location", back_populates="offers")
    photos = relationship("OfferPhoto", back_populates="offer", cascade="all, delete-orphan")
    interests = relationship("OfferInterest", back_populates="offer", cascade="all, delete-orphan")
    conversations = relationship("Conversation", back_populates="offer", cascade="all, delete-orphan")
    exchanges = relationship("Exchange", back_populates="offer")

    def __repr__(self):
        return f"<Offer {self.title} by user {self.user_id}>"

    def is_active(self) -> bool:
        """Verificar si la oferta está activa."""
        return self.status == "active"
