"""
Modelo ORM para Mensajes con soporte para Soft Delete.
"""
from sqlalchemy import Column, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base, SoftDeleteMixin


class Message(Base, SoftDeleteMixin):
    """Modelo de Mensajes del chat con soporte para soft delete."""

    __tablename__ = "messages"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False, index=True)
    from_user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    content = Column(Text, nullable=False)
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    conversation = relationship("Conversation", back_populates="messages")
    from_user = relationship("User", back_populates="messages_sent", foreign_keys=[from_user_id])

    def __repr__(self):
        return f"<Message {self.id} from {self.from_user_id}>"
