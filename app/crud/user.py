"""
CRUD para usuarios con soporte para Soft Delete.
"""
from datetime import datetime
from typing import Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc
from uuid import UUID
from app.crud.base import CRUDBase
from app.models.user import User
from app.schemas.user import UserCreate, UserUpdate
from app.core.security import get_password_hash


class CRUDUser(CRUDBase[User, UserCreate, UserUpdate]):
    """CRUD específico para usuarios con soporte para soft delete."""

    def get_by_email(
        self, db: Session, *, email: str, include_deleted: bool = False
    ) -> Optional[User]:
        """
        Obtener usuario por email.
        Por defecto excluye usuarios eliminados (soft delete).

        Args:
            db: Sesión de base de datos
            email: Email del usuario
            include_deleted: Incluir usuarios eliminados

        Returns:
            Usuario encontrado o None
        """
        query = db.query(User).filter(User.email == email)

        if not include_deleted:
            query = query.filter(User.deleted_at.is_(None))

        return query.first()

    def create(self, db: Session, *, obj_in: UserCreate) -> User:
        """
        Crear usuario con hash de contraseña.

        Args:
            db: Sesión de base de datos
            obj_in: Datos del usuario

        Returns:
            Usuario creado
        """
        db_obj = User(
            email=obj_in.email,
            password_hash=get_password_hash(obj_in.password),
            full_name=obj_in.full_name,
            faculty_id=obj_in.faculty_id,
            whatsapp=obj_in.whatsapp,
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def authenticate(self, db: Session, *, email: str, password: str) -> Optional[User]:
        """
        Autenticar usuario.
        Solo autentica usuarios no eliminados (soft delete).

        Args:
            db: Sesión de base de datos
            email: Email del usuario
            password: Contraseña en texto plano

        Returns:
            Usuario autenticado o None
        """
        from app.core.security import verify_password

        user = self.get_by_email(db, email=email)
        if not user:
            return None
        if not verify_password(password, user.password_hash):
            return None
        return user

    def update_password(self, db: Session, *, user: User, new_password: str) -> User:
        """
        Actualizar contraseña de usuario.

        Args:
            db: Sesión de base de datos
            user: Usuario a actualizar
            new_password: Nueva contraseña

        Returns:
            Usuario actualizado
        """
        user.password_hash = get_password_hash(new_password)
        db.add(user)
        db.commit()
        db.refresh(user)
        return user

    def get_active_users_count(self, db: Session) -> int:
        """
        Obtener cantidad de usuarios activos.
        Excluye registros con soft delete.

        Args:
            db: Sesión de base de datos

        Returns:
            Cantidad de usuarios activos
        """
        return db.query(User).filter(
            User.status == "active",
            User.deleted_at.is_(None)
        ).count()

    def soft_delete(self, db: Session, *, id: UUID) -> Optional[User]:
        """
        Eliminar usuario de forma suave (soft delete).
        Marca el usuario como eliminado y cambia su status a 'banned'.

        Args:
            db: Sesión de base de datos
            id: ID del usuario

        Returns:
            Usuario eliminado (soft) o None si no existe
        """
        user = self.get(db, id=id)
        if user:
            user.deleted_at = datetime.utcnow()
            user.status = "banned"
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def restore(self, db: Session, *, id: UUID) -> Optional[User]:
        """
        Restaurar un usuario eliminado (deshacer soft delete).

        Args:
            db: Sesión de base de datos
            id: ID del usuario

        Returns:
            Usuario restaurado o None si no existe
        """
        user = self.get(db, id=id, include_deleted=True)
        if user and user.deleted_at is not None:
            user.deleted_at = None
            user.status = "active"
            db.add(user)
            db.commit()
            db.refresh(user)
        return user

    def get_ranking(
        self, db: Session, *, skip: int = 0, limit: int = 20, faculty_id: Optional[int] = None
    ) -> List[User]:
        """
        Obtener ranking de usuarios por puntos de sostenibilidad.
        Excluye registros con soft delete.

        Args:
            db: Sesión de base de datos
            skip: Registros a saltar
            limit: Límite de registros
            faculty_id: Filtrar por facultad (opcional)

        Returns:
            Lista de usuarios ordenados por puntos
        """
        query = db.query(User).filter(
            User.status == "active",
            User.deleted_at.is_(None)
        )

        if faculty_id:
            query = query.filter(User.faculty_id == faculty_id)

        return (
            query
            .order_by(desc(User.sustainability_points))
            .offset(skip)
            .limit(limit)
            .all()
        )


# Instancia global del CRUD
user = CRUDUser(User)
