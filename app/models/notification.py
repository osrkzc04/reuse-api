"""
Modelo ORM para Notificaciones con soporte para Soft Delete.
"""
from sqlalchemy import Column, String, Text, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base, SoftDeleteMixin


class Notification(Base, SoftDeleteMixin):
    """Modelo de Notificaciones con soporte para soft delete."""

    __tablename__ = "notifications"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text)
    reference_id = Column(UUID(as_uuid=True))
    reference_type = Column(String(50))
    is_read = Column(Boolean, default=False, index=True)
    read_at = Column(DateTime(timezone=True))
    action_url = Column(String(500))
    extra_data = Column(JSONB)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # deleted_at viene del SoftDeleteMixin

    # Relationships
    user = relationship("User", back_populates="notifications")

    def __repr__(self):
        return f"<Notification {self.type} for user {self.user_id}>"

    def mark_as_read(self):
        """Marcar notificación como leída."""
        from datetime import datetime
        self.is_read = True
        self.read_at = datetime.utcnow()
