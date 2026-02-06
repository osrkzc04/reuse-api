"""
CRUD para conversaciones con soporte para Soft Delete.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from uuid import UUID
from app.crud.base import CRUDBase
from app.models.conversation import Conversation
from pydantic import BaseModel


class ConversationCreate(BaseModel):
    """Schema para crear conversación."""
    pass


class ConversationUpdate(BaseModel):
    """Schema para actualizar conversación."""
    is_active: Optional[bool] = None


class CRUDConversation(CRUDBase[Conversation, ConversationCreate, ConversationUpdate]):
    """CRUD específico para conversaciones con soporte para soft delete."""

    def get_by_users_and_offer(
        self, db: Session, *, user1_id: UUID, user2_id: UUID, offer_id: UUID,
        include_deleted: bool = False
    ) -> Optional[Conversation]:
        """
        Obtener conversación entre dos usuarios para una oferta.
        Por defecto excluye conversaciones eliminadas (soft delete).

        Args:
            db: Sesión de base de datos
            user1_id: ID del primer usuario
            user2_id: ID del segundo usuario
            offer_id: ID de la oferta
            include_deleted: Incluir conversaciones eliminadas

        Returns:
            Conversación encontrada o None
        """
        query = db.query(Conversation).filter(
            Conversation.offer_id == offer_id,
            or_(
                and_(
                    Conversation.user1_id == user1_id,
                    Conversation.user2_id == user2_id
                ),
                and_(
                    Conversation.user1_id == user2_id,
                    Conversation.user2_id == user1_id
                )
            )
        )

        if not include_deleted:
            query = query.filter(Conversation.deleted_at.is_(None))

        return query.first()

    def get_by_user(
        self, db: Session, *, user_id: UUID, limit: int = 30,
        include_deleted: bool = False
    ) -> List[Conversation]:
        """
        Obtener conversaciones de un usuario.
        Por defecto excluye conversaciones eliminadas (soft delete).

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            limit: Límite de registros (default 30)
            include_deleted: Incluir conversaciones eliminadas

        Returns:
            Lista de conversaciones del usuario
        """
        query = db.query(Conversation).filter(
            or_(
                Conversation.user1_id == user_id,
                Conversation.user2_id == user_id
            ),
            Conversation.is_active == True
        )

        if not include_deleted:
            query = query.filter(Conversation.deleted_at.is_(None))

        return (
            query
            .order_by(desc(Conversation.updated_at))
            .limit(limit)
            .all()
        )

    def create_conversation(
        self, db: Session, *, offer_id: UUID, user1_id: UUID, user2_id: UUID
    ) -> Conversation:
        """
        Crear nueva conversación.

        Args:
            db: Sesión de base de datos
            offer_id: ID de la oferta
            user1_id: ID del primer usuario
            user2_id: ID del segundo usuario

        Returns:
            Conversación creada
        """
        # Verificar si ya existe (incluyendo eliminadas para reactivar)
        existing = self.get_by_users_and_offer(
            db, user1_id=user1_id, user2_id=user2_id, offer_id=offer_id,
            include_deleted=True
        )
        if existing:
            # Si existía pero estaba eliminada, restaurar
            if existing.deleted_at is not None:
                existing.deleted_at = None
                existing.is_active = True
                db.add(existing)
                db.commit()
                db.refresh(existing)
            return existing

        db_obj = Conversation(
            offer_id=offer_id,
            user1_id=user1_id,
            user2_id=user2_id
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def soft_delete(self, db: Session, *, id: UUID) -> Optional[Conversation]:
        """
        Eliminar conversación de forma suave (soft delete).

        Args:
            db: Sesión de base de datos
            id: ID de la conversación

        Returns:
            Conversación eliminada (soft) o None si no existe
        """
        conv = self.get(db, id=id)
        if conv:
            conv.deleted_at = datetime.utcnow()
            conv.is_active = False
            db.add(conv)
            db.commit()
            db.refresh(conv)
        return conv

    def get_by_user_count(
        self, db: Session, *, user_id: UUID, include_deleted: bool = False
    ) -> int:
        """
        Obtener cantidad de conversaciones de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            include_deleted: Incluir conversaciones eliminadas

        Returns:
            Cantidad de conversaciones
        """
        query = db.query(Conversation).filter(
            or_(
                Conversation.user1_id == user_id,
                Conversation.user2_id == user_id
            ),
            Conversation.is_active == True
        )

        if not include_deleted:
            query = query.filter(Conversation.deleted_at.is_(None))

        return query.count()


# Instancia global del CRUD
conversation = CRUDConversation(Conversation)
