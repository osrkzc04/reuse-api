"""
Modelo ORM para Email Verification Tokens.
"""
from sqlalchemy import Column, String, Boolean, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import uuid
from app.db.base import Base


class EmailVerificationToken(Base):
    """Modelo de tokens para verificación de email."""

    __tablename__ = "email_verification_tokens"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    token = Column(String(500), nullable=False, unique=True, index=True)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    is_used = Column(Boolean, default=False)
    used_at = Column(DateTime(timezone=True))
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", back_populates="email_verification_tokens")

    def __repr__(self):
        return f"<EmailVerificationToken {self.id} for user {self.user_id}>"

    def is_valid(self) -> bool:
        """Verificar si el token es válido (no usado y no expirado)."""
        from datetime import datetime, timezone

        # Si ya fue usado, no es válido
        if self.is_used:
            return False

        # Comparar con timezone-aware datetime
        now = datetime.now(timezone.utc)

        # Si expires_at es naive, hacerlo aware (asumir UTC)
        expires = self.expires_at
        if expires.tzinfo is None:
            expires = expires.replace(tzinfo=timezone.utc)

        return expires > now
