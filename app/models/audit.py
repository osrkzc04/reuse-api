"""
Modelo ORM para Historial de Auditoría.
"""
from sqlalchemy import Column, BigInteger, String, Text, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB, ENUM, ARRAY
from sqlalchemy.sql import func
from app.db.base import Base


# Enum para operación de auditoría
audit_operation_enum = ENUM('INSERT', 'UPDATE', 'DELETE', name='audit_operation', create_type=False)


class AuditHistory(Base):
    """Modelo de Historial de Auditoría para triggers."""

    __tablename__ = "audit_history"

    id = Column(BigInteger, primary_key=True, index=True)
    table_name = Column(String(100), nullable=False, index=True)
    record_id = Column(Text, nullable=False)
    operation = Column(audit_operation_enum, nullable=False, index=True)
    old_data = Column(JSONB)
    new_data = Column(JSONB)
    changed_fields = Column(ARRAY(Text))
    changed_by = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="SET NULL"), nullable=True)
    ip_address = Column(String(45))
    user_agent = Column(Text)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), index=True)

    def __repr__(self):
        return f"<AuditHistory {self.operation} on {self.table_name} record {self.record_id}>"

    @property
    def changes_summary(self) -> dict:
        """Resumen de cambios para la operación UPDATE."""
        if self.operation != 'UPDATE' or not self.changed_fields:
            return {}

        summary = {}
        for field in self.changed_fields:
            old_val = self.old_data.get(field) if self.old_data else None
            new_val = self.new_data.get(field) if self.new_data else None
            summary[field] = {"old": old_val, "new": new_val}
        return summary
