"""
Base declarativa de SQLAlchemy con soporte para Soft Delete.
Todos los modelos heredan de esta clase base.
"""
from datetime import datetime
from sqlalchemy import Column, DateTime
from sqlalchemy.ext.declarative import declarative_base


class SoftDeleteMixin:
    """
    Mixin que agrega soporte para soft delete a los modelos.

    Agrega el campo deleted_at y métodos para manejar el borrado suave.
    Los modelos que hereden de este mixin tendrán:
    - Campo deleted_at para marcar eliminación
    - Método soft_delete() para eliminar suavemente
    - Método restore() para restaurar
    - Propiedad is_deleted para verificar estado
    """

    # Campo para soft delete - se agrega automáticamente a todos los modelos que hereden
    deleted_at = Column(DateTime(timezone=True), nullable=True, default=None, index=True)

    def soft_delete(self) -> None:
        """Marca el registro como eliminado (soft delete)."""
        self.deleted_at = datetime.utcnow()

    def restore(self) -> None:
        """Restaura un registro eliminado."""
        self.deleted_at = None

    @property
    def is_deleted(self) -> bool:
        """Verifica si el registro está eliminado."""
        return self.deleted_at is not None


# Base declarativa de SQLAlchemy
Base = declarative_base()
