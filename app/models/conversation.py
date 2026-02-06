"""
Modelo ORM para Conversaciones con soporte para Soft Delete.
"""
from sqlalchemy import Column, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base, SoftDeleteMixin


class Conversation(Base, SoftDeleteMixin):
    """Modelo de Conversaciones entre usuarios con soporte para soft delete."""

    __tablename__ = "conversations"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    offer_id = Column(UUID(as_uuid=True), ForeignKey("offers.id", ondelete="CASCADE"), nullable=False, index=True)
    user1_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    user2_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    offer = relationship("Offer", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<Conversation {self.id} between {self.user1_id} and {self.user2_id}>"

    def get_other_user_id(self, current_user_id: str) -> str:
        """Obtener el ID del otro usuario en la conversación."""
        return str(self.user2_id) if str(self.user1_id) == str(current_user_id) else str(self.user1_id)
