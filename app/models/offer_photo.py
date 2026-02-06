"""
Modelo ORM para Fotos de Ofertas con soporte para Soft Delete.
"""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base, SoftDeleteMixin


class OfferPhoto(Base, SoftDeleteMixin):
    """Modelo de Fotos de Ofertas con soporte para soft delete."""

    __tablename__ = "offer_photos"

    id = Column(Integer, primary_key=True, index=True)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True)
    photo_url = Column(String(500), nullable=False)
    object_key = Column(String(500))
    is_primary = Column(Boolean, default=False)
    display_order = Column(Integer, default=0)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    offer = relationship("Offer", back_populates="photos")

    def __repr__(self):
        return f"<OfferPhoto {self.id} for offer {self.offer_id}>"
