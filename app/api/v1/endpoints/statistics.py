"""
Endpoints para Estadísticas, Dashboard y Auditoría.
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from sqlalchemy import text
from typing import List, Optional
from uuid import UUID

from app.core.deps import get_db, get_current_user, get_current_admin_user
from app.models.user import User
from app.models.audit import AuditHistory
from app.schemas.statistics import (
    AdminDashboard,
    LeaderboardEntry,
    LeaderboardResponse,
    UserExchangeStats,
    UserRanking,
    EnvironmentalImpact,
    UserCreditsBalance,
    CategoryStats,
    ExchangeMetrics,
    OffersHealth,
    RecentActivity,
    ChallengeProgress,
    ModerationQueueItem,
    CreditsAnalysis,
    FacultySummary,
    InactiveUser,
    AuditHistoryEntry,
    AuditHistoryResponse,
)

router = APIRouter()


# ================================================================
# DASHBOARD ADMIN (Solo administradores)
# ================================================================

@router.get("/dashboard", response_model=AdminDashboard)
async def get_admin_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener estadísticas del dashboard de administrador.
    Requiere rol de administrador.
    """
    result = db.execute(text("SELECT * FROM v_admin_dashboard")).fetchone()
    if not result:
        raise HTTPException(status_code=500, detail="Error al obtener estadísticas")

    return AdminDashboard(
        total_active_users=result.total_active_users or 0,
        pending_verification_users=result.pending_verification_users or 0,
        new_users_week=result.new_users_week or 0,
        new_users_month=result.new_users_month or 0,
        total_active_offers=result.total_active_offers or 0,
        flagged_offers=result.flagged_offers or 0,
        new_offers_week=result.new_offers_week or 0,
        total_completed_exchanges=result.total_completed_exchanges or 0,
        pending_exchanges=result.pending_exchanges or 0,
        disputed_exchanges=result.disputed_exchanges or 0,
        exchanges_completed_week=result.exchanges_completed_week or 0,
        pending_flags=result.pending_flags or 0,
        total_credits_issued=result.total_credits_issued or 0,
        total_sustainability_points=result.total_sustainability_points or 0
    )


# ================================================================
# LEADERBOARD (Público)
# ================================================================

@router.get("/leaderboard", response_model=LeaderboardResponse)
async def get_leaderboard(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    faculty_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Obtener leaderboard de usuarios.
    Opcionalmente filtrar por facultad.
    """
    offset = (page - 1) * per_page

    query = "SELECT * FROM v_user_leaderboard"
    count_query = "SELECT COUNT(*) FROM v_user_leaderboard"

    params = {}
    if faculty_id:
        # Necesitamos filtrar por faculty_id, pero la vista no lo tiene directamente
        # Hacemos un filtro adicional
        query = """
            SELECT l.* FROM v_user_leaderboard l
            JOIN users u ON l.id = u.id
            WHERE u.faculty_id = :faculty_id
        """
        count_query = """
            SELECT COUNT(*) FROM v_user_leaderboard l
            JOIN users u ON l.id = u.id
            WHERE u.faculty_id = :faculty_id
        """
        params["faculty_id"] = faculty_id

    query += " LIMIT :limit OFFSET :offset"
    params["limit"] = per_page
    params["offset"] = offset

    results = db.execute(text(query), params).fetchall()
    total = db.execute(text(count_query), params if faculty_id else {}).scalar()

    entries = [
        LeaderboardEntry(
            id=row.id,
            full_name=row.full_name,
            profile_photo_url=row.profile_photo_url,
            faculty_name=row.faculty_name,
            sustainability_points=row.sustainability_points,
            level=row.level,
            total_exchanges=row.total_exchanges,
            successful_exchanges=row.successful_exchanges,
            average_rating=row.average_rating,
            overall_rank=row.overall_rank,
            faculty_rank=row.faculty_rank
        )
        for row in results
    ]

    return LeaderboardResponse(
        data=entries,
        total=total or 0,
        page=page,
        per_page=per_page
    )


# ================================================================
# ESTADÍSTICAS DE USUARIO
# ================================================================

@router.get("/users/{user_id}/exchange-stats", response_model=UserExchangeStats)
async def get_user_exchange_stats(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener estadísticas de intercambios de un usuario."""
    result = db.execute(
        text("SELECT * FROM fn_user_exchange_success_rate(:user_id)"),
        {"user_id": str(user_id)}
    ).fetchone()

    if not result:
        return UserExchangeStats(
            total_exchanges=0,
            completed_exchanges=0,
            cancelled_exchanges=0,
            success_rate=0
        )

    return UserExchangeStats(
        total_exchanges=result.total_exchanges,
        completed_exchanges=result.completed_exchanges,
        cancelled_exchanges=result.cancelled_exchanges,
        success_rate=result.success_rate
    )


@router.get("/users/{user_id}/ranking", response_model=UserRanking)
async def get_user_ranking(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener ranking de un usuario."""
    result = db.execute(
        text("SELECT * FROM fn_get_user_ranking(:user_id)"),
        {"user_id": str(user_id)}
    ).fetchone()

    if not result:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    return UserRanking(
        user_id=result.user_id,
        full_name=result.full_name,
        sustainability_points=result.sustainability_points,
        rank_overall=result.rank_overall,
        rank_faculty=result.rank_faculty,
        faculty_name=result.faculty_name
    )


@router.get("/users/{user_id}/environmental-impact", response_model=EnvironmentalImpact)
async def get_user_environmental_impact(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener impacto ambiental estimado de un usuario."""
    result = db.execute(
        text("SELECT * FROM fn_calculate_environmental_impact(:user_id)"),
        {"user_id": str(user_id)}
    ).fetchone()

    return EnvironmentalImpact(
        total_items_exchanged=result.total_items_exchanged,
        estimated_kg_co2_saved=result.estimated_kg_co2_saved,
        estimated_kg_waste_avoided=result.estimated_kg_waste_avoided,
        equivalent_trees_planted=result.equivalent_trees_planted
    )


@router.get("/users/{user_id}/credits-balance", response_model=UserCreditsBalance)
async def get_user_credits_balance(
    user_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener balance de créditos de un usuario."""
    result = db.execute(
        text("SELECT * FROM fn_get_user_credits_balance(:user_id)"),
        {"user_id": str(user_id)}
    ).fetchone()

    return UserCreditsBalance(
        current_balance=result.current_balance or 0,
        total_earned=result.total_earned or 0,
        total_spent=result.total_spent or 0,
        last_transaction_at=result.last_transaction_at
    )


@router.get("/me/stats", response_model=dict)
async def get_my_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener todas las estadísticas del usuario actual."""
    user_id = str(current_user.id)

    # Obtener todas las estadísticas en paralelo
    exchange_stats = db.execute(
        text("SELECT * FROM fn_user_exchange_success_rate(:user_id)"),
        {"user_id": user_id}
    ).fetchone()

    ranking = db.execute(
        text("SELECT * FROM fn_get_user_ranking(:user_id)"),
        {"user_id": user_id}
    ).fetchone()

    impact = db.execute(
        text("SELECT * FROM fn_calculate_environmental_impact(:user_id)"),
        {"user_id": user_id}
    ).fetchone()

    balance = db.execute(
        text("SELECT * FROM fn_get_user_credits_balance(:user_id)"),
        {"user_id": user_id}
    ).fetchone()

    return {
        "exchange_stats": {
            "total_exchanges": exchange_stats.total_exchanges if exchange_stats else 0,
            "completed_exchanges": exchange_stats.completed_exchanges if exchange_stats else 0,
            "cancelled_exchanges": exchange_stats.cancelled_exchanges if exchange_stats else 0,
            "success_rate": float(exchange_stats.success_rate) if exchange_stats else 0
        },
        "ranking": {
            "rank_overall": ranking.rank_overall if ranking else None,
            "rank_faculty": ranking.rank_faculty if ranking else None,
            "faculty_name": ranking.faculty_name if ranking else None
        } if ranking else None,
        "environmental_impact": {
            "total_items_exchanged": impact.total_items_exchanged if impact else 0,
            "estimated_kg_co2_saved": float(impact.estimated_kg_co2_saved) if impact else 0,
            "estimated_kg_waste_avoided": float(impact.estimated_kg_waste_avoided) if impact else 0,
            "equivalent_trees_planted": float(impact.equivalent_trees_planted) if impact else 0
        },
        "credits_balance": {
            "current_balance": balance.current_balance if balance else 0,
            "total_earned": balance.total_earned if balance else 0,
            "total_spent": balance.total_spent if balance else 0,
            "last_transaction_at": balance.last_transaction_at.isoformat() if balance and balance.last_transaction_at else None
        }
    }


# ================================================================
# ESTADÍSTICAS DE CATEGORÍAS
# ================================================================

@router.get("/categories/stats", response_model=List[CategoryStats])
async def get_categories_stats(
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """Obtener estadísticas por categoría."""
    if category_id:
        results = db.execute(
            text("SELECT * FROM fn_get_category_stats(:category_id)"),
            {"category_id": category_id}
        ).fetchall()
    else:
        results = db.execute(text("SELECT * FROM fn_get_category_stats()")).fetchall()

    return [
        CategoryStats(
            category_id=row.category_id,
            category_name=row.category_name,
            total_offers=row.total_offers,
            active_offers=row.active_offers,
            completed_exchanges=row.completed_exchanges,
            avg_credits_value=row.avg_credits_value
        )
        for row in results
    ]


# ================================================================
# MÉTRICAS DE INTERCAMBIOS (Admin)
# ================================================================

@router.get("/exchanges/metrics", response_model=List[ExchangeMetrics])
async def get_exchange_metrics(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Obtener métricas de intercambios por mes. Requiere rol de administrador."""
    results = db.execute(text("SELECT * FROM v_exchange_metrics")).fetchall()

    return [
        ExchangeMetrics(
            month=row.month,
            total_exchanges=row.total_exchanges,
            completed=row.completed,
            cancelled=row.cancelled,
            disputed=row.disputed,
            completion_rate=row.completion_rate,
            avg_days_to_complete=row.avg_days_to_complete,
            total_credits_exchanged=row.total_credits_exchanged
        )
        for row in results
    ]


# ================================================================
# SALUD DE OFERTAS (Admin)
# ================================================================

@router.get("/offers/health", response_model=List[OffersHealth])
async def get_offers_health(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Obtener salud de ofertas por categoría. Requiere rol de administrador."""
    results = db.execute(text("SELECT * FROM v_offers_health")).fetchall()

    return [
        OffersHealth(
            category_id=row.category_id,
            category_name=row.category_name,
            total_offers=row.total_offers,
            active_offers=row.active_offers,
            completed_offers=row.completed_offers,
            cancelled_offers=row.cancelled_offers,
            flagged_offers=row.flagged_offers,
            expired_offers=row.expired_offers,
            offers_last_month=row.offers_last_month,
            avg_views=row.avg_views,
            avg_interests=row.avg_interests
        )
        for row in results
    ]


# ================================================================
# ACTIVIDAD RECIENTE (Admin)
# ================================================================

@router.get("/activity/recent", response_model=List[RecentActivity])
async def get_recent_activity(
    limit: int = Query(50, ge=1, le=100),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Obtener actividad reciente del sistema. Requiere rol de administrador."""
    results = db.execute(
        text("SELECT * FROM v_recent_activity LIMIT :limit"),
        {"limit": limit}
    ).fetchall()

    return [
        RecentActivity(
            activity_type=row.activity_type,
            entity_id=row.entity_id,
            description=row.description,
            user_id=row.user_id,
            user_name=row.user_name,
            created_at=row.created_at
        )
        for row in results
    ]


# ================================================================
# PROGRESO DE RETOS
# ================================================================

@router.get("/challenges/progress", response_model=List[ChallengeProgress])
async def get_challenges_progress(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Obtener progreso de retos activos."""
    results = db.execute(text("SELECT * FROM v_challenges_progress")).fetchall()

    return [
        ChallengeProgress(
            id=row.id,
            title=row.title,
            description=row.description,
            frequency=row.frequency,
            difficulty=row.difficulty,
            points_reward=row.points_reward,
            credits_reward=row.credits_reward,
            start_date=row.start_date,
            end_date=row.end_date,
            requirement_type=row.requirement_type,
            requirement_value=row.requirement_value,
            total_participants=row.total_participants,
            completions=row.completions,
            completion_rate=row.completion_rate,
            challenge_status=row.challenge_status
        )
        for row in results
    ]


# ================================================================
# COLA DE MODERACIÓN (Admin/Moderador)
# ================================================================

@router.get("/moderation/queue", response_model=List[ModerationQueueItem])
async def get_moderation_queue(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Obtener cola de moderación. Requiere rol de administrador o moderador."""
    results = db.execute(text("SELECT * FROM v_moderation_queue")).fetchall()

    return [
        ModerationQueueItem(
            id=row.id,
            flag_type=row.flag_type,
            description=row.description,
            status=row.status,
            created_at=row.created_at,
            reporter_id=row.reporter_id,
            reporter_name=row.reporter_name,
            reporter_email=row.reporter_email,
            offer_id=row.offer_id,
            offer_title=row.offer_title,
            offer_owner_id=row.offer_owner_id,
            offer_owner_name=row.offer_owner_name,
            exchange_id=row.exchange_id,
            exchange_status=row.exchange_status,
            hours_in_queue=row.hours_in_queue or 0
        )
        for row in results
    ]


# ================================================================
# ANÁLISIS DE CRÉDITOS (Admin)
# ================================================================

@router.get("/credits/analysis", response_model=List[CreditsAnalysis])
async def get_credits_analysis(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Obtener análisis de créditos. Requiere rol de administrador."""
    results = db.execute(text("SELECT * FROM v_credits_analysis")).fetchall()

    return [
        CreditsAnalysis(
            month=row.month,
            transaction_type=row.transaction_type,
            transaction_count=row.transaction_count,
            total_amount=row.total_amount,
            avg_amount=row.avg_amount
        )
        for row in results
    ]


# ================================================================
# RESUMEN DE FACULTADES
# ================================================================

@router.get("/faculties/summary", response_model=List[FacultySummary])
async def get_faculties_summary(
    db: Session = Depends(get_db)
):
    """Obtener resumen por facultad. Público."""
    results = db.execute(text("SELECT * FROM v_faculty_summary")).fetchall()

    return [
        FacultySummary(
            id=row.id,
            name=row.name,
            code=row.code,
            total_users=row.total_users,
            active_users=row.active_users,
            total_points=row.total_points,
            avg_points_per_user=row.avg_points_per_user,
            total_offers=row.total_offers,
            completed_exchanges=row.completed_exchanges,
            faculty_rank=row.faculty_rank
        )
        for row in results
    ]


# ================================================================
# USUARIOS INACTIVOS (Admin)
# ================================================================

@router.get("/users/inactive", response_model=List[InactiveUser])
async def get_inactive_users(
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(50, ge=1, le=500),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Obtener usuarios inactivos. Requiere rol de administrador."""
    results = db.execute(
        text("SELECT * FROM fn_detect_inactive_users(:days) LIMIT :limit"),
        {"days": days, "limit": limit}
    ).fetchall()

    return [
        InactiveUser(
            user_id=row.user_id,
            email=row.email,
            full_name=row.full_name,
            last_activity=row.last_activity,
            days_inactive=row.days_inactive
        )
        for row in results
    ]


# ================================================================
# HISTORIAL DE AUDITORÍA (Admin)
# ================================================================

@router.get("/audit", response_model=AuditHistoryResponse)
async def get_audit_history(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    table_name: Optional[str] = None,
    operation: Optional[str] = None,
    record_id: Optional[str] = None,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener historial de auditoría.
    Requiere rol de administrador.
    """
    offset = (page - 1) * per_page

    # Construir query dinámico
    where_clauses = []
    params = {"limit": per_page, "offset": offset}

    if table_name:
        where_clauses.append("table_name = :table_name")
        params["table_name"] = table_name

    if operation:
        where_clauses.append("operation = :operation")
        params["operation"] = operation

    if record_id:
        where_clauses.append("record_id = :record_id")
        params["record_id"] = record_id

    where_sql = " AND ".join(where_clauses) if where_clauses else "1=1"

    query = f"""
        SELECT * FROM audit_history
        WHERE {where_sql}
        ORDER BY created_at DESC
        LIMIT :limit OFFSET :offset
    """

    count_query = f"SELECT COUNT(*) FROM audit_history WHERE {where_sql}"

    results = db.execute(text(query), params).fetchall()
    total = db.execute(text(count_query), params).scalar()

    entries = [
        AuditHistoryEntry(
            id=row.id,
            table_name=row.table_name,
            record_id=row.record_id,
            operation=row.operation,
            old_data=row.old_data,
            new_data=row.new_data,
            changed_fields=row.changed_fields,
            changed_by=row.changed_by,
            ip_address=row.ip_address,
            created_at=row.created_at
        )
        for row in results
    ]

    return AuditHistoryResponse(
        data=entries,
        total=total or 0,
        page=page,
        per_page=per_page
    )


@router.get("/audit/tables", response_model=List[str])
async def get_audited_tables(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """Obtener lista de tablas auditadas. Requiere rol de administrador."""
    results = db.execute(
        text("SELECT DISTINCT table_name FROM audit_history ORDER BY table_name")
    ).fetchall()

    return [row.table_name for row in results]


@router.get("/audit/record/{table_name}/{record_id}", response_model=List[AuditHistoryEntry])
async def get_record_audit_history(
    table_name: str,
    record_id: str,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Obtener historial de auditoría de un registro específico.
    Requiere rol de administrador.
    """
    results = db.execute(
        text("""
            SELECT * FROM audit_history
            WHERE table_name = :table_name AND record_id = :record_id
            ORDER BY created_at DESC
        """),
        {"table_name": table_name, "record_id": record_id}
    ).fetchall()

    return [
        AuditHistoryEntry(
            id=row.id,
            table_name=row.table_name,
            record_id=row.record_id,
            operation=row.operation,
            old_data=row.old_data,
            new_data=row.new_data,
            changed_fields=row.changed_fields,
            changed_by=row.changed_by,
            ip_address=row.ip_address,
            created_at=row.created_at
        )
        for row in results
    ]
