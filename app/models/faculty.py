"""
Modelo ORM para Facultades con soporte para Soft Delete.
"""
from sqlalchemy import Column, Integer, String, Boolean, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base, SoftDeleteMixin


class Faculty(Base, SoftDeleteMixin):
    """Modelo de Facultades PUCE con soporte para soft delete."""

    __tablename__ = "faculties"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(200), nullable=False, unique=True)
    code = Column(String(20), nullable=False, unique=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    users = relationship("User", back_populates="faculty")

    def __repr__(self):
        return f"<Faculty {self.name} ({self.code})>"
