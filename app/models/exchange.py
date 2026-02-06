"""
Modelos ORM para Intercambios con soporte para Soft Delete.
"""
from sqlalchemy import Column, Integer, Text, Boolean, DateTime, ForeignKey, CheckConstraint
from sqlalchemy.dialects.postgresql import UUID, ENUM, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base, SoftDeleteMixin


# Enums
exchange_status_enum = ENUM('pending', 'accepted', 'in_progress', 'completed', 'cancelled', 'disputed', name='exchange_status', create_type=False)
exchange_event_type_enum = ENUM('created', 'accepted', 'rejected', 'check_in_buyer', 'check_in_seller', 'completed', 'cancelled', 'disputed', name='exchange_event_type', create_type=False)


class Exchange(Base, SoftDeleteMixin):
    """Modelo de Intercambios/Trueques con soporte para soft delete."""

    __tablename__ = "exchanges"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="RESTRICT"), nullable=False, index=True)
    buyer_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    seller_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="RESTRICT"), nullable=False, index=True)
    location_id = Column(Integer, ForeignKey("locations.id", ondelete="SET NULL"))
    status = Column(exchange_status_enum, default='pending', index=True)
    credits_amount = Column(Integer, nullable=False)

    # Confirmación dual
    buyer_confirmed = Column(Boolean, default=False)
    seller_confirmed = Column(Boolean, default=False)
    buyer_confirmed_at = Column(DateTime(timezone=True))
    seller_confirmed_at = Column(DateTime(timezone=True))

    scheduled_at = Column(DateTime(timezone=True))
    completed_at = Column(DateTime(timezone=True))
    cancellation_reason = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Constraints
    __table_args__ = (
        CheckConstraint('credits_amount >= 0', name='check_credits_amount_positive'),
    )

    # Relationships
    offer = relationship("Offer", back_populates="exchanges")
    buyer = relationship("User", back_populates="exchanges_as_buyer", foreign_keys=[buyer_id])
    seller = relationship("User", back_populates="exchanges_as_seller", foreign_keys=[seller_id])
    location = relationship("Location", back_populates="exchanges")
    events = relationship("ExchangeEvent", back_populates="exchange", cascade="all, delete-orphan")
    ratings = relationship("ExchangeRating", back_populates="exchange", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Exchange {self.id} status={self.status}>"

    def is_confirmed(self) -> bool:
        """Verificar si ambas partes confirmaron el intercambio."""
        return self.buyer_confirmed and self.seller_confirmed


class ExchangeEvent(Base, SoftDeleteMixin):
    """Modelo de Eventos de Intercambio (auditoría) con soporte para soft delete."""

    __tablename__ = "exchange_events"

    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(UUID(as_uuid=True), ForeignKey("exchanges.id", ondelete="CASCADE"), nullable=False, index=True)
    event_type = Column(exchange_event_type_enum, nullable=False)
    by_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    notes = Column(Text)
    event_metadata = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    exchange = relationship("Exchange", back_populates="events")

    def __repr__(self):
        return f"<ExchangeEvent {self.event_type} for exchange {self.exchange_id}>"


class ExchangeRating(Base, SoftDeleteMixin):
    """Modelo de Valoraciones de Intercambio con soporte para soft delete."""

    __tablename__ = "exchange_ratings"

    id = Column(Integer, primary_key=True, index=True)
    exchange_id = Column(UUID(as_uuid=True), ForeignKey("exchanges.id", ondelete="CASCADE"), nullable=False)
    rater_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rated_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    rating = Column(Integer, nullable=False)
    comment = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Constraints
    __table_args__ = (
        CheckConstraint('rating >= 1 AND rating <= 5', name='check_rating_range'),
    )

    # Relationships
    exchange = relationship("Exchange", back_populates="ratings")

    def __repr__(self):
        return f"<ExchangeRating {self.rating}/5 for exchange {self.exchange_id}>"
