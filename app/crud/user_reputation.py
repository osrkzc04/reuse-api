"""
CRUD para métricas de reputación de usuario.
"""
from typing import Optional
from sqlalchemy.orm import Session
from uuid import UUID
from sqlalchemy import func

from app.crud.base import CRUDBase
from app.models.user_reputation_metrics import UserReputationMetrics
from app.models.exchange import ExchangeRating


class CRUDUserReputation(CRUDBase[UserReputationMetrics, dict, dict]):
    """CRUD específico para métricas de reputación."""

    def get_by_user_id(
        self, db: Session, *, user_id: UUID
    ) -> Optional[UserReputationMetrics]:
        """
        Obtener métricas de un usuario.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Métricas del usuario o None
        """
        return (
            db.query(UserReputationMetrics)
            .filter(UserReputationMetrics.user_id == user_id)
            .first()
        )

    def create_or_update(
        self, db: Session, *, user_id: UUID
    ) -> UserReputationMetrics:
        """
        Crear o actualizar métricas calculándolas desde cero.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Métricas actualizadas
        """
        # Calcular métricas desde las valoraciones
        ratings_stats = (
            db.query(
                func.avg(ExchangeRating.rating).label('avg_rating'),
                func.count(ExchangeRating.id).label('total_ratings')
            )
            .filter(ExchangeRating.rated_user_id == user_id)
            .first()
        )

        avg_rating = float(ratings_stats.avg_rating) if ratings_stats.avg_rating else 0.0
        total_ratings = ratings_stats.total_ratings or 0

        # Obtener o crear métricas
        metrics = self.get_by_user_id(db, user_id=user_id)

        if not metrics:
            metrics = UserReputationMetrics(
                user_id=user_id,
                average_rating=avg_rating,
                total_ratings=total_ratings,
                response_rate=100.0,  # Default
                avg_response_time_minutes=0
            )
            db.add(metrics)
        else:
            metrics.average_rating = avg_rating
            metrics.total_ratings = total_ratings

        db.commit()
        db.refresh(metrics)
        return metrics

    def add_rating(
        self, db: Session, *, user_id: UUID, rating: int
    ) -> UserReputationMetrics:
        """
        Agregar una nueva valoración y actualizar el promedio.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario valorado
            rating: Valoración (1-5)

        Returns:
            Métricas actualizadas
        """
        metrics = self.get_by_user_id(db, user_id=user_id)

        if not metrics:
            # Crear métricas si no existen
            metrics = UserReputationMetrics(
                user_id=user_id,
                average_rating=float(rating),
                total_ratings=1,
                response_rate=100.0,
                avg_response_time_minutes=0
            )
            db.add(metrics)
        else:
            # Recalcular promedio
            total_ratings = metrics.total_ratings + 1
            new_average = (
                (metrics.average_rating * metrics.total_ratings) + rating
            ) / total_ratings

            metrics.average_rating = new_average
            metrics.total_ratings = total_ratings

        db.commit()
        db.refresh(metrics)
        return metrics

    def update_response_metrics(
        self,
        db: Session,
        *,
        user_id: UUID,
        response_time_minutes: int
    ) -> UserReputationMetrics:
        """
        Actualizar métricas de tiempo de respuesta.

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario
            response_time_minutes: Tiempo de respuesta en minutos

        Returns:
            Métricas actualizadas
        """
        metrics = self.get_by_user_id(db, user_id=user_id)

        if not metrics:
            metrics = UserReputationMetrics(
                user_id=user_id,
                average_rating=0.0,
                total_ratings=0,
                response_rate=100.0,
                avg_response_time_minutes=response_time_minutes
            )
            db.add(metrics)
        else:
            # Calcular nuevo promedio de tiempo de respuesta
            # (promedio simple, se puede mejorar con ventanas temporales)
            if metrics.avg_response_time_minutes == 0:
                metrics.avg_response_time_minutes = response_time_minutes
            else:
                metrics.avg_response_time_minutes = (
                    metrics.avg_response_time_minutes + response_time_minutes
                ) // 2

        db.commit()
        db.refresh(metrics)
        return metrics

    def calculate_trust_score(
        self, db: Session, *, user_id: UUID
    ) -> float:
        """
        Calcular puntaje de confianza basado en múltiples factores.

        Factores:
        - Rating promedio (0-5) -> 40%
        - Cantidad de intercambios completados -> 30%
        - Tasa de respuesta -> 20%
        - Tiempo de respuesta -> 10%

        Args:
            db: Sesión de base de datos
            user_id: ID del usuario

        Returns:
            Puntaje de confianza (0-100)
        """
        from app.models.exchange import Exchange
        from app.models.user import User

        metrics = self.get_by_user_id(db, user_id=user_id)
        if not metrics:
            return 0.0

        # Factor 1: Rating promedio (0-5) normalizado a 0-100
        rating_score = (metrics.average_rating / 5.0) * 100 * 0.4

        # Factor 2: Intercambios completados (más intercambios = más confianza)
        completed_exchanges = (
            db.query(Exchange)
            .filter(
                (Exchange.buyer_id == user_id) | (Exchange.seller_id == user_id),
                Exchange.status == 'completed'
            )
            .count()
        )
        # Escala logarítmica: 10 intercambios = 100%
        exchange_score = min(100, (completed_exchanges / 10) * 100) * 0.3

        # Factor 3: Tasa de respuesta
        response_score = metrics.response_rate * 0.2

        # Factor 4: Tiempo de respuesta (inverso, menos tiempo = mejor)
        # 10 minutos o menos = 100%, más de 120 minutos = 0%
        if metrics.avg_response_time_minutes <= 10:
            time_score = 100
        elif metrics.avg_response_time_minutes >= 120:
            time_score = 0
        else:
            time_score = 100 - ((metrics.avg_response_time_minutes - 10) / 110 * 100)
        time_score *= 0.1

        total_score = rating_score + exchange_score + response_score + time_score

        return round(total_score, 2)


# Instancia global del CRUD
user_reputation = CRUDUserReputation(UserReputationMetrics)
