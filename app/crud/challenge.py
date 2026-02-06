"""
CRUD para retos/challenges.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import and_, desc
from uuid import UUID
from datetime import datetime
from app.crud.base import CRUDBase
from app.models.gamification import Challenge, UserChallenge
from app.schemas.challenge import ChallengeCreate, ChallengeUpdate


class CRUDChallenge(CRUDBase[Challenge, ChallengeCreate, ChallengeUpdate]):
    """CRUD específico para retos."""

    def get_active_challenges(
        self, db: Session, *, limit: int = 30
    ) -> List[Challenge]:
        """
        Obtener retos activos vigentes.

        Args:
            db: Sesion de base de datos
            limit: Limite de registros (default 30)

        Returns:
            Lista de retos activos
        """
        now = datetime.utcnow()
        return (
            db.query(Challenge)
            .filter(
                Challenge.is_active == True,
                Challenge.start_date <= now,
                Challenge.end_date >= now
            )
            .order_by(desc(Challenge.created_at))
            .limit(limit)
            .all()
        )

    def get_by_frequency(
        self, db: Session, *, frequency: str, skip: int = 0, limit: int = 20
    ) -> List[Challenge]:
        """
        Obtener retos por frecuencia.

        Args:
            db: Sesión de base de datos
            frequency: Frecuencia del reto (weekly, monthly, etc.)
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de retos de la frecuencia especificada
        """
        now = datetime.utcnow()
        return (
            db.query(Challenge)
            .filter(
                Challenge.frequency == frequency,
                Challenge.is_active == True,
                Challenge.start_date <= now,
                Challenge.end_date >= now
            )
            .order_by(desc(Challenge.created_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_user_challenge(
        self, db: Session, *, user_id: UUID, challenge_id: int
    ) -> Optional[UserChallenge]:
        """
        Obtener progreso de un usuario en un reto específico.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            challenge_id: ID del reto

        Returns:
            Progreso del usuario en el reto o None
        """
        return (
            db.query(UserChallenge)
            .filter(
                UserChallenge.user_id == user_id,
                UserChallenge.challenge_id == challenge_id
            )
            .first()
        )

    def get_user_challenges(
        self, db: Session, *, user_id: UUID, skip: int = 0, limit: int = 20
    ) -> List[UserChallenge]:
        """
        Obtener todos los retos de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de retos del usuario
        """
        return (
            db.query(UserChallenge)
            .filter(UserChallenge.user_id == user_id)
            .order_by(desc(UserChallenge.started_at))
            .offset(skip)
            .limit(limit)
            .all()
        )

    def join_challenge(
        self, db: Session, *, user_id: UUID, challenge_id: int
    ) -> UserChallenge:
        """
        Inscribir usuario en un reto.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            challenge_id: ID del reto

        Returns:
            Registro de inscripción al reto
        """
        # Verificar si ya está inscrito
        existing = self.get_user_challenge(db, user_id=user_id, challenge_id=challenge_id)
        if existing:
            return existing

        # Obtener el reto para conocer el target
        challenge = self.get(db, id=challenge_id)
        if not challenge:
            raise ValueError("Reto no encontrado")

        # Crear inscripción
        user_challenge = UserChallenge(
            user_id=user_id,
            challenge_id=challenge_id,
            target=challenge.requirement_value,
            progress=0,
            is_completed=False
        )
        db.add(user_challenge)

        # Incrementar participantes del reto
        challenge.participants_count += 1
        db.commit()
        db.refresh(user_challenge)
        return user_challenge

    def update_progress(
        self, db: Session, *, user_id: UUID, challenge_id: int, progress_increment: int = 1
    ) -> Optional[UserChallenge]:
        """
        Actualizar progreso de un usuario en un reto.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            challenge_id: ID del reto
            progress_increment: Cantidad a incrementar

        Returns:
            Progreso actualizado o None
        """
        user_challenge = self.get_user_challenge(db, user_id=user_id, challenge_id=challenge_id)
        if not user_challenge or user_challenge.is_completed:
            return user_challenge

        # Actualizar progreso
        user_challenge.progress += progress_increment

        # Verificar si completó el reto
        if user_challenge.progress >= user_challenge.target:
            user_challenge.is_completed = True
            user_challenge.completed_at = datetime.utcnow()

            # Incrementar contador de completados en el reto
            challenge = self.get(db, id=challenge_id)
            if challenge:
                challenge.completions_count += 1

        db.commit()
        db.refresh(user_challenge)
        return user_challenge


# Instancia global del CRUD
challenge = CRUDChallenge(Challenge)
