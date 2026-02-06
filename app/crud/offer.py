"""
CRUD para ofertas con soporte para Soft Delete.
"""
from datetime import datetime
from typing import List, Optional
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import desc
from uuid import UUID
from app.crud.base import CRUDBase
from app.models.offer import Offer
from app.schemas.offer import OfferCreate, OfferUpdate


class CRUDOffer(CRUDBase[Offer, OfferCreate, OfferUpdate]):
    """CRUD específico para ofertas con soporte para soft delete."""

    def create(self, db: Session, *, obj_in: OfferCreate, user_id: UUID) -> Offer:
        """
        Crear oferta asignando el usuario.

        Args:
            db: Sesión de base de datos
            obj_in: Datos de la oferta
            user_id: ID del usuario creador

        Returns:
            Oferta creada
        """
        obj_in_data = obj_in.model_dump()
        db_obj = Offer(**obj_in_data, user_id=user_id)
        db.add(db_obj)
        db.commit()
        db.refresh(db_obj)
        return db_obj

    def get_active_offers(
        self, db: Session, *, limit: int = 100
    ) -> List[Offer]:
        """
        Obtener ofertas activas ordenadas por fecha.
        Excluye registros con soft delete (deleted_at IS NOT NULL).

        Args:
            db: Sesion de base de datos
            limit: Limite de registros (default 100)

        Returns:
            Lista de ofertas activas
        """
        return (
            db.query(Offer)
            .options(joinedload(Offer.photos))
            .filter(
                Offer.status == "active",
                Offer.deleted_at.is_(None)
            )
            .order_by(desc(Offer.created_at))
            .limit(limit)
            .all()
        )

    def get_active_offers_count(self, db: Session) -> int:
        """
        Obtener cantidad de ofertas activas.
        Excluye registros con soft delete.

        Args:
            db: Sesión de base de datos

        Returns:
            Cantidad de ofertas activas
        """
        return db.query(Offer).filter(
            Offer.status == "active",
            Offer.deleted_at.is_(None)
        ).count()

    def get_by_user(
        self, db: Session, *, user_id: UUID, limit: int = 50,
        include_deleted: bool = False
    ) -> List[Offer]:
        """
        Obtener ofertas de un usuario especifico.
        Por defecto excluye registros con soft delete.

        Args:
            db: Sesion de base de datos
            user_id: ID del usuario
            limit: Limite de registros (default 50)
            include_deleted: Incluir ofertas eliminadas (soft delete)

        Returns:
            Lista de ofertas del usuario
        """
        query = (
            db.query(Offer)
            .options(joinedload(Offer.photos))
            .filter(Offer.user_id == user_id)
        )

        if not include_deleted:
            query = query.filter(Offer.deleted_at.is_(None))

        return (
            query
            .order_by(desc(Offer.created_at))
            .limit(limit)
            .all()
        )

    def get_by_category(
        self, db: Session, *, category_id: int, limit: int = 100
    ) -> List[Offer]:
        """
        Obtener ofertas por categoria.
        Excluye registros con soft delete.

        Args:
            db: Sesion de base de datos
            category_id: ID de la categoria
            limit: Limite de registros (default 100)

        Returns:
            Lista de ofertas de la categoria
        """
        return (
            db.query(Offer)
            .options(joinedload(Offer.photos))
            .filter(
                Offer.category_id == category_id,
                Offer.status == "active",
                Offer.deleted_at.is_(None)
            )
            .order_by(desc(Offer.created_at))
            .limit(limit)
            .all()
        )

    def increment_views(self, db: Session, *, offer_id: UUID) -> Offer:
        """
        Incrementar contador de vistas de una oferta.

        Args:
            db: Sesión de base de datos
            offer_id: ID de la oferta

        Returns:
            Oferta actualizada
        """
        offer = self.get(db, id=offer_id)
        if offer:
            offer.views_count += 1
            db.commit()
            db.refresh(offer)
        return offer

    def soft_delete(self, db: Session, *, id: UUID) -> Optional[Offer]:
        """
        Eliminar oferta de forma suave (soft delete).
        Marca la oferta como eliminada y cambia el status a cancelled.

        Args:
            db: Sesión de base de datos
            id: ID de la oferta

        Returns:
            Oferta eliminada (soft) o None si no existe
        """
        offer = self.get(db, id=id)
        if offer:
            offer.deleted_at = datetime.utcnow()
            offer.status = "cancelled"
            db.add(offer)
            db.commit()
            db.refresh(offer)
        return offer

    def restore(self, db: Session, *, id: UUID) -> Optional[Offer]:
        """
        Restaurar una oferta eliminada (deshacer soft delete).

        Args:
            db: Sesión de base de datos
            id: ID de la oferta

        Returns:
            Oferta restaurada o None si no existe
        """
        offer = self.get(db, id=id, include_deleted=True)
        if offer and offer.deleted_at is not None:
            offer.deleted_at = None
            offer.status = "active"
            db.add(offer)
            db.commit()
            db.refresh(offer)
        return offer

    def get_deleted(
        self, db: Session, *, user_id: Optional[UUID] = None, skip: int = 0, limit: int = 20
    ) -> List[Offer]:
        """
        Obtener ofertas eliminadas (soft deleted).

        Args:
            db: Sesión de base de datos
            user_id: Filtrar por usuario (opcional)
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de ofertas eliminadas
        """
        query = db.query(Offer).filter(Offer.deleted_at.isnot(None))

        if user_id:
            query = query.filter(Offer.user_id == user_id)

        return (
            query
            .order_by(desc(Offer.deleted_at))
            .offset(skip)
            .limit(limit)
            .all()
        )


# Instancia global del CRUD
offer = CRUDOffer(Offer)
