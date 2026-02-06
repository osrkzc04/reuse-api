"""
Servicio de gamificación.
Maneja puntos, niveles, badges y challenges.
Incluye funciones que utilizan stored procedures para operaciones críticas.
"""
from typing import Optional, Dict, Any
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.models.user import User
from app.models.user_reputation_metrics import UserReputationMetrics
from app.models.user_challenge import UserChallenge
from app.models.challenge import Challenge
from app.models.user_badge import UserBadge
from app.models.badges_catalog import BadgesCatalog
from app.services import notification_service


def award_points(db: Session, user_id: UUID, points: int, reason: str = "activity") -> User:
    """
    Otorgar puntos de sostenibilidad a un usuario.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        points: Cantidad de puntos a otorgar
        reason: Razón del otorgamiento

    Returns:
        Usuario actualizado
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    # Incrementar puntos
    user.sustainability_points += points
    user.experience_points += points

    # Verificar nivel
    new_level = calculate_level(user.experience_points)
    if new_level > user.level:
        user.level = new_level
        # Notificar subida de nivel
        notification_service.notify_level_up(db, user_id, new_level)

    db.commit()
    db.refresh(user)

    # Verificar si se desbloquearon badges
    check_and_award_badges(db, user)

    # Actualizar progreso de challenges
    update_challenge_progress(db, user_id)

    return user


def calculate_level(experience_points: int) -> int:
    """
    Calcular nivel basado en puntos de experiencia.
    Cada nivel requiere 100 puntos más que el anterior.

    Args:
        experience_points: Puntos de experiencia

    Returns:
        Nivel calculado
    """
    # Fórmula: nivel = sqrt(puntos / 50)
    import math
    return max(1, int(math.sqrt(experience_points / 50)) + 1)


def check_and_award_badges(db: Session, user: User):
    """
    Verificar y otorgar badges automáticamente.

    Args:
        db: Sesión de base de datos
        user: Usuario
    """
    # Obtener badges del catálogo
    badges = db.query(BadgesCatalog).filter(BadgesCatalog.is_active == True).all()

    # Obtener métricas del usuario
    metrics = db.query(UserReputationMetrics).filter(
        UserReputationMetrics.user_id == user.id
    ).first()

    if not metrics:
        return

    for badge in badges:
        # Verificar si el usuario ya tiene el badge
        existing = db.query(UserBadge).filter(
            UserBadge.user_id == user.id,
            UserBadge.badge_id == badge.id
        ).first()

        if existing:
            continue

        # Verificar criterios de desbloqueo
        should_award = False

        if badge.unlock_type == "exchange_count":
            should_award = metrics.total_exchanges >= badge.unlock_value

        elif badge.unlock_type == "points_total":
            should_award = user.sustainability_points >= badge.unlock_value

        elif badge.unlock_type == "category_specific":
            # Verificar intercambios de categoría específica
            # TODO: Implementar lógica específica por categoría
            pass

        elif badge.unlock_type == "streak_days":
            should_award = metrics.current_streak >= badge.unlock_value

        if should_award:
            # Otorgar badge
            user_badge = UserBadge(
                user_id=user.id,
                badge_id=badge.id
            )
            db.add(user_badge)
            db.commit()

            # Notificar
            notification_service.notify_badge_earned(
                db, user.id, badge.name, badge.id
            )


def update_challenge_progress(db: Session, user_id: UUID):
    """
    Actualizar progreso de challenges activos del usuario.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
    """
    from datetime import datetime

    # Obtener challenges activos del usuario
    user_challenges = db.query(UserChallenge).join(Challenge).filter(
        UserChallenge.user_id == user_id,
        UserChallenge.is_completed == False,
        Challenge.is_active == True,
        Challenge.end_date >= datetime.utcnow()
    ).all()

    metrics = db.query(UserReputationMetrics).filter(
        UserReputationMetrics.user_id == user_id
    ).first()

    if not metrics:
        return

    for uc in user_challenges:
        challenge = uc.challenge

        # Actualizar progreso según tipo de requisito
        if challenge.requirement_type == "exchange_count":
            uc.progress = metrics.total_exchanges

        elif challenge.requirement_type == "category_specific":
            # TODO: Implementar lógica específica
            pass

        # Verificar si se completó
        if uc.progress >= uc.target and not uc.is_completed:
            uc.is_completed = True
            uc.completed_at = datetime.utcnow()

            # Otorgar recompensas
            award_points(db, user_id, challenge.points_reward, "challenge_completed")

            if challenge.credits_reward > 0:
                # TODO: Otorgar créditos
                pass

            if challenge.badge_reward:
                # TODO: Otorgar badge específico
                pass

            # Notificar
            notification_service.notify_challenge_completed(
                db, user_id, challenge.title, challenge.points_reward
            )

        db.add(uc)

    db.commit()


def enroll_in_challenge(db: Session, user_id: UUID, challenge_id: int) -> Optional[UserChallenge]:
    """
    Inscribir usuario en un challenge.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        challenge_id: ID del challenge

    Returns:
        UserChallenge creado o existente
    """
    # Verificar si ya está inscrito
    existing = db.query(UserChallenge).filter(
        UserChallenge.user_id == user_id,
        UserChallenge.challenge_id == challenge_id
    ).first()

    if existing:
        return existing

    # Obtener challenge
    challenge = db.query(Challenge).filter(Challenge.id == challenge_id).first()
    if not challenge:
        return None

    # Crear inscripción
    user_challenge = UserChallenge(
        user_id=user_id,
        challenge_id=challenge_id,
        target=challenge.requirement_value,
        progress=0
    )

    db.add(user_challenge)

    # Incrementar contador de participantes
    challenge.participants_count += 1

    db.commit()
    db.refresh(user_challenge)

    return user_challenge


# ================================================================
# FUNCIONES CON STORED PROCEDURES
# Garantizan atomicidad y validacion de reglas de negocio
# ================================================================

def sp_complete_challenge(db: Session, user_id: UUID, challenge_id: int) -> Dict[str, Any]:
    """
    Completar un reto usando stored procedure.
    Garantiza atomicidad: validación de progreso, otorgamiento de puntos,
    créditos (si aplica), badges (si aplica), actualización de contadores
    y notificación.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario
        challenge_id: ID del reto

    Returns:
        Dict con resultado del SP:
        - success: bool
        - challenge_title: str
        - points_awarded: int
        - credits_awarded: int
        - badge_awarded: str o None
        - new_credits_balance: int o None

    Raises:
        Exception: Si el SP falla (no inscrito, ya completado, progreso insuficiente)
    """
    result = db.execute(
        text("SELECT sp_complete_challenge(:user_id, :challenge_id)"),
        {
            "user_id": str(user_id),
            "challenge_id": challenge_id
        }
    ).scalar()
    db.commit()
    return result
