"""
Modelo ORM para Intereses en Ofertas con soporte para Soft Delete.
"""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base, SoftDeleteMixin


class OfferInterest(Base, SoftDeleteMixin):
    """Modelo de Intereses en Ofertas (botón 'Me interesa') con soporte para soft delete."""

    __tablename__ = "offer_interests"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    conversation_id = Column(UUID(as_uuid=True))
    status = Column(String(20), default='active', index=True)
    notes = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    offer = relationship("Offer", back_populates="interests")
    user = relationship("User", back_populates="offer_interests")

    def __repr__(self):
        return f"<OfferInterest user={self.user_id} offer={self.offer_id}>"
