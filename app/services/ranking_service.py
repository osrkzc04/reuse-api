"""
Servicio de ranking.
Calcula y gestiona rankings de usuarios.
"""
from typing import List, Optional, Dict
from uuid import UUID
from sqlalchemy.orm import Session
from sqlalchemy import desc, func

from app.models.user import User
from app.models.faculty import Faculty
from app.models.user_reputation_metrics import UserReputationMetrics
from app.models.user_badge import UserBadge
from app.schemas.ranking import RankingEntry, RankingResponse, MyPositionResponse


def get_general_ranking(
    db: Session, skip: int = 0, limit: int = 20, current_user_id: Optional[UUID] = None
) -> RankingResponse:
    """
    Obtener ranking general de usuarios.

    Args:
        db: Sesión de base de datos
        skip: Registros a saltar
        limit: Límite de registros
        current_user_id: ID del usuario actual (opcional)

    Returns:
        Respuesta de ranking
    """
    # Obtener usuarios ordenados por puntos
    users_query = (
        db.query(
            User.id,
            User.full_name,
            User.profile_photo_url,
            User.faculty_id,
            User.sustainability_points,
            User.level,
            Faculty.name.label("faculty_name"),
            UserReputationMetrics.total_exchanges,
            func.count(UserBadge.id).label("badges_count")
        )
        .outerjoin(Faculty, User.faculty_id == Faculty.id)
        .outerjoin(UserReputationMetrics, User.id == UserReputationMetrics.user_id)
        .outerjoin(UserBadge, User.id == UserBadge.user_id)
        .filter(User.status == "active")
        .group_by(
            User.id,
            User.full_name,
            User.profile_photo_url,
            User.faculty_id,
            User.sustainability_points,
            User.level,
            Faculty.name,
            UserReputationMetrics.total_exchanges
        )
        .order_by(desc(User.sustainability_points))
    )

    total_users = users_query.count()
    users = users_query.offset(skip).limit(limit).all()

    # Construir entradas de ranking
    entries = []
    my_rank = None

    for idx, user in enumerate(users):
        rank = skip + idx + 1
        entry = RankingEntry(
            rank=rank,
            user_id=user.id,
            user_name=user.full_name,
            user_photo=user.profile_photo_url,
            faculty_id=user.faculty_id,
            faculty_name=user.faculty_name,
            sustainability_points=user.sustainability_points,
            level=user.level,
            total_exchanges=user.total_exchanges or 0,
            badges_count=user.badges_count or 0
        )
        entries.append(entry)

        if current_user_id and str(user.id) == str(current_user_id):
            my_rank = rank

    return RankingResponse(
        entries=entries,
        total_users=total_users,
        my_rank=my_rank,
        ranking_type="general"
    )


def get_faculty_ranking(
    db: Session, faculty_id: int, skip: int = 0, limit: int = 20, current_user_id: Optional[UUID] = None
) -> RankingResponse:
    """
    Obtener ranking por facultad.

    Args:
        db: Sesión de base de datos
        faculty_id: ID de la facultad
        skip: Registros a saltar
        limit: Límite de registros
        current_user_id: ID del usuario actual (opcional)

    Returns:
        Respuesta de ranking
    """
    users_query = (
        db.query(
            User.id,
            User.full_name,
            User.profile_photo_url,
            User.faculty_id,
            User.sustainability_points,
            User.level,
            Faculty.name.label("faculty_name"),
            UserReputationMetrics.total_exchanges,
            func.count(UserBadge.id).label("badges_count")
        )
        .outerjoin(Faculty, User.faculty_id == Faculty.id)
        .outerjoin(UserReputationMetrics, User.id == UserReputationMetrics.user_id)
        .outerjoin(UserBadge, User.id == UserBadge.user_id)
        .filter(User.status == "active", User.faculty_id == faculty_id)
        .group_by(
            User.id,
            User.full_name,
            User.profile_photo_url,
            User.faculty_id,
            User.sustainability_points,
            User.level,
            Faculty.name,
            UserReputationMetrics.total_exchanges
        )
        .order_by(desc(User.sustainability_points))
    )

    total_users = users_query.count()
    users = users_query.offset(skip).limit(limit).all()

    # Construir entradas de ranking
    entries = []
    my_rank = None

    for idx, user in enumerate(users):
        rank = skip + idx + 1
        entry = RankingEntry(
            rank=rank,
            user_id=user.id,
            user_name=user.full_name,
            user_photo=user.profile_photo_url,
            faculty_id=user.faculty_id,
            faculty_name=user.faculty_name,
            sustainability_points=user.sustainability_points,
            level=user.level,
            total_exchanges=user.total_exchanges or 0,
            badges_count=user.badges_count or 0
        )
        entries.append(entry)

        if current_user_id and str(user.id) == str(current_user_id):
            my_rank = rank

    return RankingResponse(
        entries=entries,
        total_users=total_users,
        my_rank=my_rank,
        ranking_type="faculty"
    )


def get_my_position(db: Session, user_id: UUID) -> MyPositionResponse:
    """
    Obtener posición del usuario en rankings.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario

    Returns:
        Posición en rankings
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return None

    # Calcular posición en ranking general
    rank_overall = (
        db.query(func.count(User.id))
        .filter(
            User.status == "active",
            User.sustainability_points > user.sustainability_points
        )
        .scalar()
    ) + 1

    total_users = db.query(func.count(User.id)).filter(User.status == "active").scalar()

    # Calcular posición en ranking de facultad
    rank_in_faculty = None
    total_users_in_faculty = None
    percentile_in_faculty = None

    if user.faculty_id:
        rank_in_faculty = (
            db.query(func.count(User.id))
            .filter(
                User.status == "active",
                User.faculty_id == user.faculty_id,
                User.sustainability_points > user.sustainability_points
            )
            .scalar()
        ) + 1

        total_users_in_faculty = (
            db.query(func.count(User.id))
            .filter(User.status == "active", User.faculty_id == user.faculty_id)
            .scalar()
        )

        percentile_in_faculty = (rank_in_faculty / total_users_in_faculty) * 100 if total_users_in_faculty > 0 else 0

    percentile_overall = (rank_overall / total_users) * 100 if total_users > 0 else 0

    return MyPositionResponse(
        rank_overall=rank_overall,
        rank_in_faculty=rank_in_faculty,
        total_users=total_users,
        total_users_in_faculty=total_users_in_faculty,
        percentile_overall=percentile_overall,
        percentile_in_faculty=percentile_in_faculty
    )
