"""
CRUD para mensajes con soporte para Soft Delete.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from uuid import UUID
from app.crud.base import CRUDBase
from app.models.message import Message
from app.schemas.message import MessageCreate
from pydantic import BaseModel


class MessageUpdate(BaseModel):
    """Schema para actualizar mensaje."""
    pass


class CRUDMessage(CRUDBase[Message, MessageCreate, MessageUpdate]):
    """CRUD específico para mensajes con soporte para soft delete."""

    def create_message(
        self, db: Session, *, obj_in: MessageCreate, conversation_id: UUID, from_user_id: UUID
    ) -> Message:
        """
        Crear mensaje en una conversación.

        Args:
            db: Sesión de base de datos
            obj_in: Datos del mensaje
            conversation_id: ID de la conversación
            from_user_id: ID del usuario remitente

        Returns:
            Mensaje creado
        """
        db_obj = Message(
            conversation_id=conversation_id,
            from_user_id=from_user_id,
            content=obj_in.content
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_conversation(
        self, db: Session, *, conversation_id: UUID, limit: int = 100,
        include_deleted: bool = False
    ) -> List[Message]:
        """
        Obtener mensajes de una conversación.
        Por defecto excluye mensajes eliminados (soft delete).

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación
            limit: Límite de registros (default 100)
            include_deleted: Incluir mensajes eliminados

        Returns:
            Lista de mensajes
        """
        query = db.query(Message).filter(Message.conversation_id == conversation_id)

        if not include_deleted:
            query = query.filter(Message.deleted_at.is_(None))

        return (
            query
            .order_by(desc(Message.created_at))
            .limit(limit)
            .all()
        )

    def mark_as_read(
        self, db: Session, *, conversation_id: UUID, user_id: UUID
    ) -> int:
        """
        Marcar mensajes de una conversación como leídos.
        Solo marca mensajes no eliminados (soft delete).

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación
            user_id: ID del usuario que lee (se marcan los mensajes de OTROS usuarios)

        Returns:
            Cantidad de mensajes marcados
        """
        updated = (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.from_user_id != user_id,
                Message.is_read == False,
                Message.deleted_at.is_(None)
            )
            .update({"is_read": True, "read_at": datetime.utcnow()})
        )
        db.commit()
        return updated

    def soft_delete(self, db: Session, *, id: UUID) -> Optional[Message]:
        """
        Eliminar mensaje de forma suave (soft delete).

        Args:
            db: Sesión de base de datos
            id: ID del mensaje

        Returns:
            Mensaje eliminado (soft) o None si no existe
        """
        msg = self.get(db, id=id)
        if msg:
            msg.deleted_at = datetime.utcnow()
            db.add(msg)
            db.commit()
            db.refresh(msg)
        return msg

    def get_unread_count(
        self, db: Session, *, conversation_id: UUID, user_id: UUID
    ) -> int:
        """
        Obtener cantidad de mensajes no leídos en una conversación.
        Excluye mensajes eliminados (soft delete).

        Args:
            db: Sesión de base de datos
            conversation_id: ID de la conversación
            user_id: ID del usuario (se cuentan mensajes de OTROS usuarios)

        Returns:
            Cantidad de mensajes no leídos
        """
        return (
            db.query(Message)
            .filter(
                Message.conversation_id == conversation_id,
                Message.from_user_id != user_id,
                Message.is_read == False,
                Message.deleted_at.is_(None)
            )
            .count()
        )


# Instancia global del CRUD
message = CRUDMessage(Message)
