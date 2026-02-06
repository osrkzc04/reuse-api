"""
CRUD base genérico con operaciones comunes y soporte para Soft Delete.
"""
from datetime import datetime
from typing import Generic, TypeVar, Type, Optional, List, Any, Dict
from sqlalchemy.orm import Session
from pydantic import BaseModel
from app.db.base import Base

ModelType = TypeVar("ModelType", bound=Base)
CreateSchemaType = TypeVar("CreateSchemaType", bound=BaseModel)
UpdateSchemaType = TypeVar("UpdateSchemaType", bound=BaseModel)


class CRUDBase(Generic[ModelType, CreateSchemaType, UpdateSchemaType]):
    """
    Clase base para operaciones CRUD con soporte para Soft Delete.

    Todas las consultas filtran automáticamente los registros eliminados
    (deleted_at IS NULL) a menos que se especifique lo contrario.
    """

    def __init__(self, model: Type[ModelType]):
        """
        Inicializar CRUD con el modelo ORM.

        Args:
            model: Modelo ORM de SQLAlchemy
        """
        self.model = model

    def _base_query(self, db: Session, include_deleted: bool = False):
        """
        Crear query base con filtro de soft delete.

        Args:
            db: Sesión de base de datos
            include_deleted: Si es True, incluye registros eliminados

        Returns:
            Query filtrado
        """
        query = db.query(self.model)
        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.filter(self.model.deleted_at.is_(None))
        return query

    def get(
        self,
        db: Session,
        id: Any,
        include_deleted: bool = False
    ) -> Optional[ModelType]:
        """
        Obtener un registro por ID.

        Args:
            db: Sesión de base de datos
            id: ID del registro
            include_deleted: Si es True, incluye registros eliminados

        Returns:
            Registro encontrado o None
        """
        return self._base_query(db, include_deleted).filter(
            self.model.id == id
        ).first()

    def get_multi(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    ) -> List[ModelType]:
        """
        Obtener múltiples registros con paginación.

        Args:
            db: Sesión de base de datos
            skip: Cantidad de registros a saltar
            limit: Límite de registros a retornar
            include_deleted: Si es True, incluye registros eliminados

        Returns:
            Lista de registros
        """
        return self._base_query(db, include_deleted).offset(skip).limit(limit).all()

    def get_count(
        self,
        db: Session,
        include_deleted: bool = False
    ) -> int:
        """
        Obtener el total de registros.

        Args:
            db: Sesión de base de datos
            include_deleted: Si es True, incluye registros eliminados

        Returns:
            Cantidad total de registros
        """
        return self._base_query(db, include_deleted).count()

    def create(self, db: Session, *, obj_in: CreateSchemaType) -> ModelType:
        """
        Crear un nuevo registro.

        Args:
            db: Sesión de base de datos
            obj_in: Schema con datos de entrada

        Returns:
            Registro creado
        """
        obj_in_data = obj_in.model_dump()
        db_obj = self.model(**obj_in_data)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def update(
        self,
        db: Session,
        *,
        db_obj: ModelType,
        obj_in: UpdateSchemaType | Dict[str, Any]
    ) -> ModelType:
        """
        Actualizar un registro existente.

        Args:
            db: Sesión de base de datos
            db_obj: Objeto de base de datos a actualizar
            obj_in: Schema o dict con datos de actualización

        Returns:
            Registro actualizado
        """
        if isinstance(obj_in, dict):
            update_data = obj_in
        else:
            update_data = obj_in.model_dump(exclude_unset=True)

        for field in update_data:
            if hasattr(db_obj, field):
                setattr(db_obj, field, update_data[field])

        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def remove(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """
        Eliminar un registro (HARD DELETE).

        ADVERTENCIA: Este método elimina permanentemente el registro.
        Use soft_delete() para borrado suave.

        Args:
            db: Sesión de base de datos
            id: ID del registro a eliminar

        Returns:
            Registro eliminado
        """
        obj = self._base_query(db).filter(self.model.id == id).first()
        if obj:
            db.delete(obj)
            db.commit()
        return obj

    def soft_delete(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """
        Eliminar un registro de forma suave (Soft Delete).

        Marca el registro como eliminado estableciendo deleted_at.
        El registro permanece en la base de datos pero no aparece
        en las consultas normales.

        Args:
            db: Sesión de base de datos
            id: ID del registro a eliminar

        Returns:
            Registro eliminado (soft) o None si no existe
        """
        obj = self._base_query(db).filter(self.model.id == id).first()
        if obj and hasattr(obj, 'deleted_at'):
            obj.deleted_at = datetime.utcnow()
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj

    def restore(self, db: Session, *, id: Any) -> Optional[ModelType]:
        """
        Restaurar un registro eliminado (deshacer soft delete).

        Args:
            db: Sesión de base de datos
            id: ID del registro a restaurar

        Returns:
            Registro restaurado o None si no existe
        """
        obj = self._base_query(db, include_deleted=True).filter(
            self.model.id == id
        ).first()
        if obj and hasattr(obj, 'deleted_at') and obj.deleted_at is not None:
            obj.deleted_at = None
            db.add(obj)
            db.commit()
            db.refresh(obj)
        return obj

    def get_deleted(
        self,
        db: Session,
        *,
        skip: int = 0,
        limit: int = 100
    ) -> List[ModelType]:
        """
        Obtener registros eliminados (soft deleted).

        Args:
            db: Sesión de base de datos
            skip: Cantidad de registros a saltar
            limit: Límite de registros a retornar

        Returns:
            Lista de registros eliminados
        """
        if not hasattr(self.model, 'deleted_at'):
            return []
        return db.query(self.model).filter(
            self.model.deleted_at.isnot(None)
        ).offset(skip).limit(limit).all()
