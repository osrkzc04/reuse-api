"""
Modelo ORM para Ubicaciones del campus con soporte para Soft Delete.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, Numeric
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base, SoftDeleteMixin


class Location(Base, SoftDeleteMixin):
    """Modelo de Ubicaciones del campus PUCE con soporte para soft delete."""

    __tablename__ = "locations"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False)
    description = Column(Text)
    latitude = Column(Numeric(10, 8))
    longitude = Column(Numeric(11, 8))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    offers = relationship("Offer", back_populates="location")
    exchanges = relationship("Exchange", back_populates="location")

    def __repr__(self):
        return f"<Location {self.name}>"
