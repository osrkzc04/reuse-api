"""
Modelo ORM para Categorías de objetos con soporte para Soft Delete.
"""
from sqlalchemy import Column, Integer, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base, SoftDeleteMixin


class Category(Base, SoftDeleteMixin):
    """Modelo de Categorías de objetos con soporte para soft delete."""

    __tablename__ = "categories"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), nullable=False)
    description = Column(Text)
    parent_id = Column(Integer, ForeignKey("categories.id", ondelete="SET NULL"))
    icon = Column(String(50))
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Self-referential relationship
    parent = relationship("Category", remote_side=[id], backref="subcategories")

    # Relationships
    offers = relationship("Offer", back_populates="category")

    def __repr__(self):
        return f"<Category {self.name}>"
