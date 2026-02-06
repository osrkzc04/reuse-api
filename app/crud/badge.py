"""
CRUD para insignias/badges.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import desc
from uuid import UUID
from datetime import datetime
from app.crud.base import CRUDBase
from app.models.gamification import BadgesCatalog, UserBadge
from app.schemas.badge import BadgeCreate, BadgeUpdate


class CRUDBadge(CRUDBase[BadgesCatalog, BadgeCreate, BadgeUpdate]):
    """CRUD específico para insignias."""

    def get_active_badges(
        self, db: Session, *, limit: int = 50
    ) -> List[BadgesCatalog]:
        """
        Obtener insignias activas ordenadas por display_order.

        Args:
            db: Sesion de base de datos
            limit: Limite de registros (default 50)

        Returns:
            Lista de insignias activas
        """
        return (
            db.query(BadgesCatalog)
            .filter(BadgesCatalog.is_active == True)
            .order_by(BadgesCatalog.display_order, BadgesCatalog.created_at)
            .limit(limit)
            .all()
        )

    def get_by_category(
        self, db: Session, *, category: str, skip: int = 0, limit: int = 20
    ) -> List[BadgesCatalog]:
        """
        Obtener insignias por categoría.

        Args:
            db: Sesión de base de datos
            category: Categoría de la insignia
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de insignias de la categoría
        """
        return (
            db.query(BadgesCatalog)
            .filter(
                BadgesCatalog.category == category,
                BadgesCatalog.is_active == True
            )
            .order_by(BadgesCatalog.display_order)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_by_rarity(
        self, db: Session, *, rarity: str, skip: int = 0, limit: int = 20
    ) -> List[BadgesCatalog]:
        """
        Obtener insignias por rareza.

        Args:
            db: Sesión de base de datos
            rarity: Rareza de la insignia
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de insignias de la rareza especificada
        """
        return (
            db.query(BadgesCatalog)
            .filter(
                BadgesCatalog.rarity == rarity,
                BadgesCatalog.is_active == True
            )
            .order_by(BadgesCatalog.display_order)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_badge(
        self, db: Session, *, user_id: UUID, badge_id: str
    ) -> Optional[UserBadge]:
        """
        Verificar si un usuario tiene una insignia específica.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            badge_id: ID de la insignia

        Returns:
            Insignia del usuario o None
        """
        return (
            db.query(UserBadge)
            .filter(
                UserBadge.user_id == user_id,
                UserBadge.badge_id == badge_id
            )
            .first()
        )

    def get_user_badges(
        self, db: Session, *, user_id: UUID, limit: int = 50
    ) -> List[UserBadge]:
        """
        Obtener todas las insignias de un usuario.

        Args:
            db: Sesion de base de datos
            user_id: ID del usuario
            limit: Limite de registros (default 50)

        Returns:
            Lista de insignias del usuario
        """
        return (
            db.query(UserBadge)
            .filter(UserBadge.user_id == user_id)
            .order_by(desc(UserBadge.earned_at))
            .limit(limit)
            .all()
        )

    def get_user_displayed_badges(
        self, db: Session, *, user_id: UUID, limit: int = 6
    ) -> List[UserBadge]:
        """
        Obtener insignias que el usuario tiene marcadas para mostrar.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            limit: Límite de insignias a mostrar

        Returns:
            Lista de insignias visibles del usuario
        """
        return (
            db.query(UserBadge)
            .filter(
                UserBadge.user_id == user_id,
                UserBadge.is_displayed == True
            )
            .order_by(desc(UserBadge.earned_at))
            .limit(limit)
            .all()
        )

    def award_badge(
        self, db: Session, *, user_id: UUID, badge_id: str, progress: int = 100
    ) -> UserBadge:
        """
        Otorgar una insignia a un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            badge_id: ID de la insignia
            progress: Progreso de la insignia (default 100%)

        Returns:
            Insignia otorgada

        Raises:
            ValueError: Si la insignia no existe o el usuario ya la tiene
        """
        # Verificar que la insignia existe
        badge = self.get(db, id=badge_id)
        if not badge:
            raise ValueError("Insignia no encontrada")

        # Verificar que el usuario no tenga ya la insignia
        existing = self.get_user_badge(db, user_id=user_id, badge_id=badge_id)
        if existing:
            raise ValueError("El usuario ya tiene esta insignia")

        # Otorgar insignia
        user_badge = UserBadge(
            user_id=user_id,
            badge_id=badge_id,
            progress=progress,
            earned_at=datetime.utcnow(),
            is_displayed=True
        )
        db.add(user_badge)
        db.commit()
        db.refresh(user_badge)
        return user_badge

    def toggle_display(
        self, db: Session, *, user_badge_id: int
    ) -> Optional[UserBadge]:
        """
        Alternar visibilidad de una insignia.

        Args:
            db: Sesión de base de datos
            user_badge_id: ID del registro UserBadge

        Returns:
            Insignia actualizada o None
        """
        user_badge = db.query(UserBadge).filter(UserBadge.id == user_badge_id).first()
        if user_badge:
            user_badge.is_displayed = not user_badge.is_displayed
            db.commit()
            db.refresh(user_badge)
        return user_badge


# Instancia global del CRUD
badge = CRUDBadge(BadgesCatalog)
