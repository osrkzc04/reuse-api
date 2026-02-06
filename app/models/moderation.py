"""
Modelos ORM para Auditoría.
"""
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, BigInteger
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
from app.db.base import Base


class ActivityLog(Base):
    """Modelo de Log de Actividad (Auditoría)."""

    __tablename__ = "activity_log"

    id = Column(BigInteger, primary_key=True, index=True)
    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"))
    action_type = Column(String(50), nullable=False)
    entity_type = Column(String(50))
    entity_id = Column(UUID(as_uuid=True))
    extra_data = Column(JSONB)  # Renombrado de 'metadata' (palabra reservada en SQLAlchemy)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<ActivityLog {self.action_type} by user {self.user_id}>"
