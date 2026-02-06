"""
CRUD para intercambios con soporte para Soft Delete.
Incluye métodos que utilizan stored procedures para operaciones críticas.
"""
from datetime import datetime
from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import desc, or_, text
from uuid import UUID
from app.crud.base import CRUDBase
from app.models.exchange import Exchange
from app.schemas.exchange import ExchangeCreate, ExchangeUpdate


class CRUDExchange(CRUDBase[Exchange, ExchangeCreate, ExchangeUpdate]):
    """CRUD específico para intercambios con soporte para soft delete."""

    def create_exchange(
        self, db: Session, *, obj_in: ExchangeCreate, buyer_id: UUID, seller_id: UUID, credits_amount: int
    ) -> Exchange:
        """
        Crear intercambio.

        Args:
            db: Sesión de base de datos
            obj_in: Datos del intercambio
            buyer_id: ID del comprador
            seller_id: ID del vendedor
            credits_amount: Cantidad de créditos

        Returns:
            Intercambio creado
        """
        db_obj = Exchange(
            offer_id=obj_in.offer_id,
            buyer_id=buyer_id,
            seller_id=seller_id,
            credits_amount=credits_amount,
            location_id=obj_in.location_id,
            scheduled_at=obj_in.scheduled_at
        )
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_by_user(
        self, db: Session, *, user_id: UUID, limit: int = 50,
        include_deleted: bool = False
    ) -> List[Exchange]:
        """
        Obtener intercambios de un usuario (como comprador o vendedor).
        Por defecto excluye registros con soft delete.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            limit: Límite de registros (default 50)
            include_deleted: Incluir intercambios eliminados

        Returns:
            Lista de intercambios
        """
        query = db.query(Exchange).filter(
            or_(
                Exchange.buyer_id == user_id,
                Exchange.seller_id == user_id
            )
        )

        if not include_deleted:
            query = query.filter(Exchange.deleted_at.is_(None))

        return (
            query
            .order_by(desc(Exchange.created_at))
            .limit(limit)
            .all()
        )

    def get_by_user_count(
        self, db: Session, *, user_id: UUID, include_deleted: bool = False
    ) -> int:
        """
        Obtener cantidad de intercambios de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            include_deleted: Incluir intercambios eliminados

        Returns:
            Cantidad de intercambios
        """
        query = db.query(Exchange).filter(
            or_(
                Exchange.buyer_id == user_id,
                Exchange.seller_id == user_id
            )
        )

        if not include_deleted:
            query = query.filter(Exchange.deleted_at.is_(None))

        return query.count()

    def confirm_by_user(
        self, db: Session, *, exchange: Exchange, user_id: UUID
    ) -> Exchange:
        """
        Confirmar intercambio por parte de un usuario.

        Args:
            db: Sesión de base de datos
            exchange: Intercambio a confirmar
            user_id: ID del usuario que confirma

        Returns:
            Intercambio actualizado
        """
        if str(exchange.buyer_id) == str(user_id):
            exchange.buyer_confirmed = True
            exchange.buyer_confirmed_at = datetime.utcnow()
        elif str(exchange.seller_id) == str(user_id):
            exchange.seller_confirmed = True
            exchange.seller_confirmed_at = datetime.utcnow()

        # Si ambos confirmaron, marcar como completado
        if exchange.buyer_confirmed and exchange.seller_confirmed:
            exchange.status = "completed"
            exchange.completed_at = datetime.utcnow()

        db.add(exchange)
        db.commit()
        db.refresh(exchange)
        return exchange

    def get_completed_count(self, db: Session) -> int:
        """
        Obtener cantidad de intercambios completados.
        Excluye registros con soft delete.

        Args:
            db: Sesión de base de datos

        Returns:
            Cantidad de intercambios completados
        """
        return db.query(Exchange).filter(
            Exchange.status == "completed",
            Exchange.deleted_at.is_(None)
        ).count()

    def soft_delete(self, db: Session, *, id: UUID) -> Optional[Exchange]:
        """
        Eliminar intercambio de forma suave (soft delete).

        Args:
            db: Sesión de base de datos
            id: ID del intercambio

        Returns:
            Intercambio eliminado (soft) o None si no existe
        """
        exchange = self.get(db, id=id)
        if exchange:
            exchange.deleted_at = datetime.utcnow()
            db.add(exchange)
            db.commit()
            db.refresh(exchange)
        return exchange

    def get_by_status(
        self, db: Session, *, status: str, limit: int = 50
    ) -> List[Exchange]:
        """
        Obtener intercambios por estado.
        Excluye registros con soft delete.

        Args:
            db: Sesión de base de datos
            status: Estado del intercambio
            limit: Límite de registros (default 50)

        Returns:
            Lista de intercambios
        """
        return (
            db.query(Exchange)
            .filter(
                Exchange.status == status,
                Exchange.deleted_at.is_(None)
            )
            .order_by(desc(Exchange.created_at))
            .limit(limit)
            .all()
        )

    # ================================================================
    # METODOS CON STORED PROCEDURES
    # Garantizan atomicidad y validacion de reglas de negocio
    # ================================================================

    def sp_create_exchange(
        self,
        db: Session,
        *,
        buyer_id: UUID,
        offer_id: UUID,
        proposed_location_id: Optional[int] = None,
        proposed_datetime: Optional[datetime] = None,
        message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Crear intercambio usando stored procedure.
        Garantiza atomicidad: reserva de oferta, creación de exchange,
        conversación y notificación.

        Args:
            db: Sesión de base de datos
            buyer_id: ID del comprador
            offer_id: ID de la oferta
            proposed_location_id: ID de ubicación propuesta
            proposed_datetime: Fecha/hora propuesta
            message: Mensaje inicial

        Returns:
            Dict con resultado del SP (success, exchange_id, conversation_id, etc.)

        Raises:
            Exception: Si el SP falla (oferta no disponible, etc.)
        """
        result = db.execute(
            text("SELECT sp_create_exchange(:buyer_id, :offer_id, :location_id, :datetime, :message)"),
            {
                "buyer_id": str(buyer_id),
                "offer_id": str(offer_id),
                "location_id": proposed_location_id,
                "datetime": proposed_datetime,
                "message": message
            }
        ).scalar()
        db.commit()
        return result

    def sp_complete_exchange(
        self,
        db: Session,
        *,
        exchange_id: UUID,
        user_id: UUID,
        is_buyer: bool
    ) -> Dict[str, Any]:
        """
        Completar intercambio usando stored procedure.
        Garantiza atomicidad: confirmación dual, transferencia de créditos,
        puntos y notificaciones.

        Args:
            db: Sesión de base de datos
            exchange_id: ID del intercambio
            user_id: ID del usuario que confirma
            is_buyer: True si es el comprador, False si es vendedor

        Returns:
            Dict con resultado del SP (success, status, credits_transferred, etc.)

        Raises:
            Exception: Si el SP falla (saldo insuficiente, estado inválido, etc.)
        """
        result = db.execute(
            text("SELECT sp_complete_exchange(:exchange_id, :user_id, :is_buyer)"),
            {
                "exchange_id": str(exchange_id),
                "user_id": str(user_id),
                "is_buyer": is_buyer
            }
        ).scalar()
        db.commit()
        return result

    def sp_cancel_exchange(
        self,
        db: Session,
        *,
        exchange_id: UUID,
        user_id: UUID,
        reason: str
    ) -> Dict[str, Any]:
        """
        Cancelar intercambio usando stored procedure.
        Garantiza atomicidad: actualización de estado, liberación de oferta
        y notificación.

        Args:
            db: Sesión de base de datos
            exchange_id: ID del intercambio
            user_id: ID del usuario que cancela
            reason: Razón de cancelación

        Returns:
            Dict con resultado del SP (success, status, offer_released)

        Raises:
            Exception: Si el SP falla (sin permisos, ya completado, etc.)
        """
        result = db.execute(
            text("SELECT sp_cancel_exchange(:exchange_id, :user_id, :reason)"),
            {
                "exchange_id": str(exchange_id),
                "user_id": str(user_id),
                "reason": reason
            }
        ).scalar()
        db.commit()
        return result


# Instancia global del CRUD
exchange = CRUDExchange(Exchange)
