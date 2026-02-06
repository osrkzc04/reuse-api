"""
Endpoints de ranking de gamificación.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import desc, func
from typing import Optional

from app.core.deps import get_db, get_current_active_user
from app.schemas.ranking import RankingEntry, RankingResponse, MyPositionResponse
from app.models.user import User
from app.models.faculty import Faculty
from app.models.gamification import UserBadge
from app.models.exchange import Exchange

router = APIRouter()


@router.get("/general", response_model=RankingResponse)
def get_general_ranking(
    limit: int = Query(50, le=200, description="Cantidad de usuarios a mostrar"),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """
    Obtener ranking general por puntos de sostenibilidad.

    Muestra los top usuarios ordenados por sustainability_points.
    """
    # Obtener top usuarios (solo estudiantes, excluir admin/moderador)
    top_users = (
        db.query(User)
        .filter(User.status == 'active', User.role == 'estudiante')
        .order_by(desc(User.sustainability_points), desc(User.level))
        .limit(limit)
        .all()
    )

    # Construir entries con ranking
    entries = []
    for idx, user in enumerate(top_users, start=1):
        # Contar exchanges del usuario
        total_exchanges = (
            db.query(Exchange)
            .filter(
                (Exchange.buyer_id == user.id) | (Exchange.seller_id == user.id),
                Exchange.status == 'completed'
            )
            .count()
        )

        # Contar badges
        badges_count = db.query(UserBadge).filter(UserBadge.user_id == user.id).count()

        # Obtener facultad
        faculty = db.query(Faculty).filter(Faculty.id == user.faculty_id).first() if user.faculty_id else None

        entry = RankingEntry(
            rank=idx,
            user_id=user.id,
            user_name=user.full_name,
            user_photo=user.profile_photo_url,
            faculty_id=user.faculty_id,
            faculty_name=faculty.name if faculty else None,
            sustainability_points=user.sustainability_points,
            level=user.level,
            total_exchanges=total_exchanges,
            badges_count=badges_count
        )
        entries.append(entry)

    # Total de usuarios activos (solo estudiantes)
    total_users = db.query(User).filter(
        User.status == 'active',
        User.role == 'estudiante'
    ).count()

    # Buscar posición del usuario actual (solo si es estudiante)
    my_rank = None
    if current_user and current_user.role == 'estudiante':
        users_above = (
            db.query(User)
            .filter(
                User.status == 'active',
                User.role == 'estudiante',
                User.sustainability_points > current_user.sustainability_points
            )
            .count()
        )
        my_rank = users_above + 1

    return RankingResponse(
        entries=entries,
        total_users=total_users,
        my_rank=my_rank,
        ranking_type='general'
    )


@router.get("/faculty/{faculty_id}", response_model=RankingResponse)
def get_faculty_ranking(
    faculty_id: int,
    limit: int = Query(50, le=200),
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_active_user)
):
    """
    Obtener ranking por facultad.

    Muestra los top usuarios de una facultad específica.
    """
    # Verificar que la facultad existe
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Facultad no encontrada"
        )

    # Obtener top usuarios de la facultad (solo estudiantes)
    top_users = (
        db.query(User)
        .filter(
            User.faculty_id == faculty_id,
            User.status == 'active',
            User.role == 'estudiante'
        )
        .order_by(desc(User.sustainability_points), desc(User.level))
        .limit(limit)
        .all()
    )

    # Construir entries
    entries = []
    for idx, user in enumerate(top_users, start=1):
        # Contar exchanges
        total_exchanges = (
            db.query(Exchange)
            .filter(
                (Exchange.buyer_id == user.id) | (Exchange.seller_id == user.id),
                Exchange.status == 'completed'
            )
            .count()
        )

        # Contar badges
        badges_count = db.query(UserBadge).filter(UserBadge.user_id == user.id).count()

        entry = RankingEntry(
            rank=idx,
            user_id=user.id,
            user_name=user.full_name,
            user_photo=user.profile_photo_url,
            faculty_id=user.faculty_id,
            faculty_name=faculty.name,
            sustainability_points=user.sustainability_points,
            level=user.level,
            total_exchanges=total_exchanges,
            badges_count=badges_count
        )
        entries.append(entry)

    # Total de usuarios en la facultad (solo estudiantes)
    total_users = (
        db.query(User)
        .filter(
            User.faculty_id == faculty_id,
            User.status == 'active',
            User.role == 'estudiante'
        )
        .count()
    )

    # Buscar posición del usuario actual en su facultad (solo si es estudiante)
    my_rank = None
    if current_user and current_user.faculty_id == faculty_id and current_user.role == 'estudiante':
        users_above = (
            db.query(User)
            .filter(
                User.faculty_id == faculty_id,
                User.status == 'active',
                User.role == 'estudiante',
                User.sustainability_points > current_user.sustainability_points
            )
            .count()
        )
        my_rank = users_above + 1

    return RankingResponse(
        entries=entries,
        total_users=total_users,
        my_rank=my_rank,
        ranking_type='faculty'
    )


@router.get("/my/position", response_model=MyPositionResponse)
def get_my_ranking_position(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener mi posición actual en los rankings.

    Retorna posición en ranking general y en ranking de facultad (si aplica).
    Incluye percentiles para contexto.
    Solo aplica para estudiantes.
    """
    # Admin/moderador no participan en ranking
    if current_user.role in ['administrador', 'moderador']:
        return MyPositionResponse(
            rank_overall=None,
            rank_in_faculty=None,
            total_users=0,
            total_users_in_faculty=None,
            percentile_overall=0,
            percentile_in_faculty=None
        )

    # Total de usuarios activos (solo estudiantes)
    total_users = db.query(User).filter(
        User.status == 'active',
        User.role == 'estudiante'
    ).count()

    # Ranking general (solo estudiantes)
    users_above_overall = (
        db.query(User)
        .filter(
            User.status == 'active',
            User.role == 'estudiante',
            User.sustainability_points > current_user.sustainability_points
        )
        .count()
    )
    rank_overall = users_above_overall + 1
    percentile_overall = ((total_users - rank_overall) / total_users * 100) if total_users > 0 else 0

    # Ranking en facultad (solo estudiantes)
    rank_in_faculty = None
    total_users_in_faculty = None
    percentile_in_faculty = None

    if current_user.faculty_id:
        total_users_in_faculty = (
            db.query(User)
            .filter(
                User.faculty_id == current_user.faculty_id,
                User.status == 'active',
                User.role == 'estudiante'
            )
            .count()
        )

        users_above_faculty = (
            db.query(User)
            .filter(
                User.faculty_id == current_user.faculty_id,
                User.status == 'active',
                User.role == 'estudiante',
                User.sustainability_points > current_user.sustainability_points
            )
            .count()
        )
        rank_in_faculty = users_above_faculty + 1
        percentile_in_faculty = (
            ((total_users_in_faculty - rank_in_faculty) / total_users_in_faculty * 100)
            if total_users_in_faculty > 0
            else 0
        )

    return MyPositionResponse(
        rank_overall=rank_overall,
        rank_in_faculty=rank_in_faculty,
        total_users=total_users,
        total_users_in_faculty=total_users_in_faculty,
        percentile_overall=round(percentile_overall, 2),
        percentile_in_faculty=round(percentile_in_faculty, 2) if percentile_in_faculty is not None else None
    )


@router.get("/faculties", response_model=list[dict])
def get_faculties_ranking(
    db: Session = Depends(get_db)
):
    """
    Obtener ranking de facultades por promedio de puntos.

    Útil para mostrar qué facultad es más activa en sostenibilidad.
    """
    from sqlalchemy import func

    # Calcular promedio de puntos por facultad (solo estudiantes)
    faculty_rankings = (
        db.query(
            Faculty.id,
            Faculty.name,
            func.count(User.id).label('total_users'),
            func.avg(User.sustainability_points).label('avg_points'),
            func.sum(User.sustainability_points).label('total_points')
        )
        .join(User, User.faculty_id == Faculty.id)
        .filter(
            User.status == 'active',
            User.role == 'estudiante',
            Faculty.is_active == True
        )
        .group_by(Faculty.id, Faculty.name)
        .order_by(desc('avg_points'))
        .all()
    )

    results = []
    for idx, (fac_id, fac_name, total_users, avg_points, total_points) in enumerate(faculty_rankings, start=1):
        results.append({
            "rank": idx,
            "faculty_id": fac_id,
            "faculty_name": fac_name,
            "total_users": total_users,
            "average_points": round(float(avg_points), 2) if avg_points else 0,
            "total_points": int(total_points) if total_points else 0
        })

    return results
