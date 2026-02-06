"""
Modelo ORM para Refresh Tokens.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class RefreshToken(Base):
    """Modelo de Refresh Tokens para autenticación JWT."""

    __tablename__ = "refresh_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(500), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_revoked = Column(Boolean, default=False)
    revoked_at = Column(DateTime(timezone=True))
    device_info = Column(String(500))
    ip_address = Column(String(45))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="refresh_tokens")

    def __repr__(self):
        return f"<RefreshToken {self.id} for user {self.user_id}>"

    def is_valid(self) -> bool:
        """Verificar si el token es válido (no revocado y no expirado)."""
        from datetime import datetime
        return not self.is_revoked and self.expires_at > datetime.utcnow()
