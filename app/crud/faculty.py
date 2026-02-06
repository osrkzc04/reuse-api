"""
CRUD para facultades.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.crud.base import CRUDBase
from app.models.faculty import Faculty
from app.schemas.common import MessageResponse


class CRUDFaculty(CRUDBase[Faculty, dict, dict]):
    """CRUD específico para facultades."""

    def get_active(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Faculty]:
        """
        Obtener facultades activas.

        Args:
            db: Sesión de base de datos
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de facultades activas
        """
        return (
            db.query(Faculty)
            .filter(Faculty.is_active == True)
            .order_by(Faculty.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_code(self, db: Session, *, code: str) -> Optional[Faculty]:
        """
        Obtener facultad por código.

        Args:
            db: Sesión de base de datos
            code: Código de la facultad

        Returns:
            Facultad encontrada o None
        """
        return db.query(Faculty).filter(Faculty.code == code).first()

    def search(
        self, db: Session, *, query: str, skip: int = 0, limit: int = 20
    ) -> List[Faculty]:
        """
        Buscar facultades por nombre o código.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de facultades que coinciden
        """
        search_term = f"%{query}%"
        return (
            db.query(Faculty)
            .filter(
                or_(
                    Faculty.name.ilike(search_term),
                    Faculty.code.ilike(search_term)
                ),
                Faculty.is_active == True
            )
            .order_by(Faculty.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_faculty(
        self, db: Session, *, name: str, code: str
    ) -> Faculty:
        """
        Crear nueva facultad.

        Args:
            db: Sesión de base de datos
            name: Nombre de la facultad
            code: Código de la facultad

        Returns:
            Facultad creada

        Raises:
            ValueError: Si el código ya existe
        """
        # Verificar que el código no exista
        existing = self.get_by_code(db, code=code)
        if existing:
            raise ValueError(f"Ya existe una facultad con el código '{code}'")

        new_faculty = Faculty(name=name, code=code, is_active=True)
        db.add(new_faculty)
        db.commit()
        db.refresh(new_faculty)
        return new_faculty

    def toggle_active(
        self, db: Session, *, faculty_id: int
    ) -> Optional[Faculty]:
        """
        Activar/desactivar una facultad.

        Args:
            db: Sesión de base de datos
            faculty_id: ID de la facultad

        Returns:
            Facultad actualizada o None
        """
        faculty = self.get(db, id=faculty_id)
        if faculty:
            faculty.is_active = not faculty.is_active
            db.commit()
            db.refresh(faculty)
        return faculty


# Instancia global del CRUD
faculty = CRUDFaculty(Faculty)
