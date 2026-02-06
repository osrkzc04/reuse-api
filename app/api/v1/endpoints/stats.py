"""
Endpoints de estadísticas y métricas.
"""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from sqlalchemy import func, and_, or_, extract
from datetime import datetime, timedelta
from typing import List

from app.core.deps import get_db, get_current_active_user
from app.schemas.stats import (
    DashboardStats,
    OfferStats,
    ExchangeStats,
    SustainabilityStats,
    CategoryPopularity,
    MonthlyActivity,
    ComparisonStats
)
from app.models.user import User
from app.models.offer import Offer
from app.models.offer_interest import OfferInterest
from app.models.exchange import Exchange, ExchangeRating
from app.models.category import Category
from app.models.gamification import UserBadge, UserChallenge
from app.models.user_reputation_metrics import UserReputationMetrics
from app.crud.reward import reward as crud_reward
from app.crud.user_reputation import user_reputation as crud_user_reputation

router = APIRouter()


@router.get("/dashboard", response_model=DashboardStats)
def get_dashboard(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener dashboard completo de estadísticas del usuario.

    Incluye métricas de ofertas, intercambios, sostenibilidad y actividad reciente.
    """
    user_id = current_user.id

    # ========== Estadísticas de Ofertas ==========
    offers_query = db.query(Offer).filter(Offer.user_id == user_id)

    total_offers = offers_query.count()
    active_offers = offers_query.filter(Offer.status == 'active').count()
    reserved_offers = offers_query.filter(Offer.status == 'reserved').count()
    completed_offers = offers_query.filter(Offer.status == 'completed').count()
    cancelled_offers = offers_query.filter(Offer.status == 'cancelled').count()
    flagged_offers = offers_query.filter(Offer.status == 'flagged').count()

    total_views = db.query(func.sum(Offer.views_count)).filter(Offer.user_id == user_id).scalar() or 0
    avg_views = (total_views / total_offers) if total_offers > 0 else 0

    total_interests = db.query(OfferInterest).join(Offer).filter(Offer.user_id == user_id).count()

    # Conversión: intereses que resultaron en intercambios
    exchanges_from_interests = (
        db.query(Exchange)
        .join(Offer, Exchange.offer_id == Offer.id)
        .filter(Offer.user_id == user_id, Exchange.status == 'completed')
        .count()
    )
    conversion_rate = (exchanges_from_interests / total_interests * 100) if total_interests > 0 else 0

    offer_stats = OfferStats(
        total_offers=total_offers,
        active_offers=active_offers,
        reserved_offers=reserved_offers,
        completed_offers=completed_offers,
        cancelled_offers=cancelled_offers,
        flagged_offers=flagged_offers,
        total_views=int(total_views),
        avg_views_per_offer=round(avg_views, 2),
        total_interests=total_interests,
        conversion_rate=round(conversion_rate, 2)
    )

    # ========== Estadísticas de Intercambios ==========
    exchanges_as_buyer = db.query(Exchange).filter(Exchange.buyer_id == user_id)
    exchanges_as_seller = db.query(Exchange).filter(Exchange.seller_id == user_id)

    total_as_buyer = exchanges_as_buyer.count()
    completed_as_buyer = exchanges_as_buyer.filter(Exchange.status == 'completed').count()
    pending_as_buyer = exchanges_as_buyer.filter(Exchange.status.in_(['pending', 'accepted'])).count()
    cancelled_as_buyer = exchanges_as_buyer.filter(Exchange.status == 'cancelled').count()

    total_as_seller = exchanges_as_seller.count()
    completed_as_seller = exchanges_as_seller.filter(Exchange.status == 'completed').count()
    pending_as_seller = exchanges_as_seller.filter(Exchange.status.in_(['pending', 'accepted'])).count()
    cancelled_as_seller = exchanges_as_seller.filter(Exchange.status == 'cancelled').count()

    total_exchanges = total_as_buyer + total_as_seller
    completed_exchanges = completed_as_buyer + completed_as_seller
    success_rate = (completed_exchanges / total_exchanges * 100) if total_exchanges > 0 else 0

    # Rating recibido
    rating_stats = (
        db.query(
            func.avg(ExchangeRating.rating).label('avg'),
            func.count(ExchangeRating.id).label('count')
        )
        .filter(ExchangeRating.rated_user_id == user_id)
        .first()
    )

    exchange_stats = ExchangeStats(
        total_as_buyer=total_as_buyer,
        completed_as_buyer=completed_as_buyer,
        pending_as_buyer=pending_as_buyer,
        cancelled_as_buyer=cancelled_as_buyer,
        total_as_seller=total_as_seller,
        completed_as_seller=completed_as_seller,
        pending_as_seller=pending_as_seller,
        cancelled_as_seller=cancelled_as_seller,
        total_exchanges=total_exchanges,
        completed_exchanges=completed_exchanges,
        success_rate=round(success_rate, 2),
        avg_rating_received=float(rating_stats.avg) if rating_stats.avg else None,
        total_ratings_received=rating_stats.count or 0
    )

    # ========== Estadísticas de Sostenibilidad ==========
    # Puntos para siguiente nivel (cada 100 XP = 1 nivel)
    xp_for_next_level = (current_user.level + 1) * 100
    xp_current_level = current_user.level * 100
    xp_progress = current_user.experience_points - xp_current_level
    points_to_next = xp_for_next_level - current_user.experience_points
    level_progress = (xp_progress / 100 * 100) if xp_progress > 0 else 0

    # Rankings
    total_users = db.query(User).filter(User.status == 'active').count()
    users_above = (
        db.query(User)
        .filter(User.status == 'active', User.sustainability_points > current_user.sustainability_points)
        .count()
    )
    rank_overall = users_above + 1
    percentile_overall = ((total_users - rank_overall) / total_users * 100) if total_users > 0 else 0

    rank_in_faculty = None
    percentile_in_faculty = None
    if current_user.faculty_id:
        total_in_faculty = db.query(User).filter(
            User.faculty_id == current_user.faculty_id,
            User.status == 'active'
        ).count()
        users_above_faculty = (
            db.query(User)
            .filter(
                User.faculty_id == current_user.faculty_id,
                User.status == 'active',
                User.sustainability_points > current_user.sustainability_points
            )
            .count()
        )
        rank_in_faculty = users_above_faculty + 1
        percentile_in_faculty = (
            ((total_in_faculty - rank_in_faculty) / total_in_faculty * 100)
            if total_in_faculty > 0 else 0
        )

    # Badges y challenges
    total_badges = db.query(UserBadge).filter(UserBadge.user_id == user_id).count()

    challenges_query = db.query(UserChallenge).filter(UserChallenge.user_id == user_id)
    total_challenges = challenges_query.count()
    completed_challenges = challenges_query.filter(UserChallenge.is_completed == True).count()
    challenge_completion_rate = (completed_challenges / total_challenges * 100) if total_challenges > 0 else 0

    # Créditos
    from app.models.credits import CreditsLedger
    current_balance = crud_reward.get_user_balance(db, user_id=user_id)
    total_earned = (
        db.query(func.sum(CreditsLedger.amount))
        .filter(CreditsLedger.user_id == user_id, CreditsLedger.amount > 0)
        .scalar() or 0
    )
    total_spent = abs(
        db.query(func.sum(CreditsLedger.amount))
        .filter(CreditsLedger.user_id == user_id, CreditsLedger.amount < 0)
        .scalar() or 0
    )

    # Impacto ambiental estimado (aproximaciones)
    # Asumimos que cada intercambio evita 2kg de CO2 y 1kg de residuos
    co2_saved = completed_exchanges * 2.0
    waste_avoided = completed_exchanges * 1.0

    sustainability_stats = SustainabilityStats(
        sustainability_points=current_user.sustainability_points,
        level=current_user.level,
        experience_points=current_user.experience_points,
        points_to_next_level=points_to_next,
        level_progress_percentage=round(level_progress, 2),
        rank_overall=rank_overall,
        rank_in_faculty=rank_in_faculty,
        percentile_overall=round(percentile_overall, 2),
        percentile_in_faculty=round(percentile_in_faculty, 2) if percentile_in_faculty else None,
        total_badges=total_badges,
        total_challenges_joined=total_challenges,
        total_challenges_completed=completed_challenges,
        challenges_completion_rate=round(challenge_completion_rate, 2),
        current_credits_balance=current_balance,
        total_credits_earned=int(total_earned),
        total_credits_spent=int(total_spent),
        estimated_co2_saved_kg=co2_saved,
        estimated_waste_avoided_kg=waste_avoided
    )

    # ========== Actividad Reciente (últimos 30 días) ==========
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)

    recent_offers = (
        db.query(Offer)
        .filter(Offer.user_id == user_id, Offer.created_at >= thirty_days_ago)
        .count()
    )
    recent_exchanges = (
        db.query(Exchange)
        .filter(
            or_(Exchange.buyer_id == user_id, Exchange.seller_id == user_id),
            Exchange.status == 'completed',
            Exchange.completed_at >= thirty_days_ago
        )
        .count()
    )
    # Mensajes enviados (si existe tabla)
    from app.models.message import Message
    recent_messages = (
        db.query(Message)
        .filter(Message.from_user_id == user_id, Message.created_at >= thirty_days_ago)
        .count()
    )

    # Puntos ganados recientemente
    recent_points = (
        db.query(func.sum(CreditsLedger.amount))
        .filter(
            CreditsLedger.user_id == user_id,
            CreditsLedger.created_at >= thirty_days_ago,
            CreditsLedger.amount > 0
        )
        .scalar() or 0
    )

    recent_activity = {
        "offers_created": recent_offers,
        "exchanges_completed": recent_exchanges,
        "messages_sent": recent_messages,
        "sustainability_points_earned": int(recent_points)
    }

    # ========== Reputación ==========
    reputation_metrics = db.query(UserReputationMetrics).filter(
        UserReputationMetrics.user_id == user_id
    ).first()

    trust_score = None
    response_rate = None
    avg_response_time = None

    if reputation_metrics:
        trust_score = crud_user_reputation.calculate_trust_score(db, user_id=user_id)
        response_rate = reputation_metrics.response_rate
        avg_response_time = reputation_metrics.avg_response_time_minutes

    # ========== Construir Dashboard ==========
    return DashboardStats(
        user_id=str(current_user.id),
        user_name=current_user.full_name,
        member_since=current_user.created_at,
        last_active=current_user.last_login,
        offers=offer_stats,
        exchanges=exchange_stats,
        sustainability=sustainability_stats,
        recent_activity=recent_activity,
        trust_score=trust_score,
        response_rate=response_rate,
        avg_response_time_minutes=avg_response_time
    )


@router.get("/categories/popular", response_model=List[CategoryPopularity])
def get_popular_categories(
    limit: int = Query(10, le=50),
    db: Session = Depends(get_db)
):
    """
    Obtener categorías más populares por cantidad de ofertas e intercambios.
    """
    category_stats = (
        db.query(
            Category.id,
            Category.name,
            func.count(Offer.id).label('total_offers'),
            func.sum(func.cast(Offer.status == 'active', db.Integer)).label('active_offers'),
            func.count(Exchange.id).label('total_exchanges'),
            func.avg(Offer.credits_value).label('avg_credits')
        )
        .join(Offer, Offer.category_id == Category.id)
        .outerjoin(Exchange, Exchange.offer_id == Offer.id)
        .filter(Category.is_active == True)
        .group_by(Category.id, Category.name)
        .order_by(func.count(Offer.id).desc())
        .limit(limit)
        .all()
    )

    results = []
    for cat_id, cat_name, total_offers, active_offers, total_exchanges, avg_credits in category_stats:
        results.append(CategoryPopularity(
            category_id=cat_id,
            category_name=cat_name,
            total_offers=total_offers,
            active_offers=active_offers or 0,
            total_exchanges=total_exchanges or 0,
            avg_credits_value=round(float(avg_credits), 2) if avg_credits else 0
        ))

    return results


@router.get("/activity/monthly", response_model=List[MonthlyActivity])
def get_monthly_activity(
    months: int = Query(6, ge=1, le=24, description="Cantidad de meses hacia atrás"),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener actividad mensual del usuario.

    Útil para gráficos de progreso temporal.
    """
    user_id = current_user.id
    results = []

    for i in range(months):
        # Calcular mes
        target_date = datetime.utcnow() - timedelta(days=30 * i)
        month_str = target_date.strftime("%Y-%m")
        month_start = target_date.replace(day=1)

        if i == 0:
            month_end = datetime.utcnow()
        else:
            month_end = (datetime.utcnow() - timedelta(days=30 * (i - 1))).replace(day=1)

        # Ofertas creadas en ese mes
        offers_created = (
            db.query(Offer)
            .filter(
                Offer.user_id == user_id,
                Offer.created_at >= month_start,
                Offer.created_at < month_end
            )
            .count()
        )

        # Intercambios completados en ese mes
        exchanges_completed = (
            db.query(Exchange)
            .filter(
                or_(Exchange.buyer_id == user_id, Exchange.seller_id == user_id),
                Exchange.status == 'completed',
                Exchange.completed_at >= month_start,
                Exchange.completed_at < month_end
            )
            .count()
        )

        # Challenges completados
        challenges_completed = (
            db.query(UserChallenge)
            .filter(
                UserChallenge.user_id == user_id,
                UserChallenge.is_completed == True,
                UserChallenge.completed_at >= month_start,
                UserChallenge.completed_at < month_end
            )
            .count()
        )

        # Puntos ganados (aproximado desde transacciones)
        from app.models.credits import CreditsLedger
        points_earned = (
            db.query(func.sum(CreditsLedger.amount))
            .filter(
                CreditsLedger.user_id == user_id,
                CreditsLedger.amount > 0,
                CreditsLedger.created_at >= month_start,
                CreditsLedger.created_at < month_end
            )
            .scalar() or 0
        )

        results.append(MonthlyActivity(
            month=month_str,
            offers_created=offers_created,
            exchanges_completed=exchanges_completed,
            sustainability_points_earned=int(points_earned),
            challenges_completed=challenges_completed
        ))

    return list(reversed(results))  # Orden cronológico


@router.get("/comparison", response_model=List[ComparisonStats])
def get_comparison_stats(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Comparar mis estadísticas con promedios de la sistema.

    Útil para mostrar "Estás en el top X%" en diferentes métricas.
    """
    user_id = current_user.id
    comparisons = []

    # 1. Sustainability Points
    my_points = current_user.sustainability_points
    avg_points = db.query(func.avg(User.sustainability_points)).filter(User.status == 'active').scalar() or 0
    faculty_avg_points = None
    if current_user.faculty_id:
        faculty_avg_points = (
            db.query(func.avg(User.sustainability_points))
            .filter(User.faculty_id == current_user.faculty_id, User.status == 'active')
            .scalar() or 0
        )

    total_users = db.query(User).filter(User.status == 'active').count()
    users_below = db.query(User).filter(
        User.status == 'active',
        User.sustainability_points < my_points
    ).count()
    percentile_points = (users_below / total_users * 100) if total_users > 0 else 0

    comparisons.append(ComparisonStats(
        metric_name="Puntos de Sostenibilidad",
        my_value=float(my_points),
        platform_average=round(float(avg_points), 2),
        faculty_average=round(float(faculty_avg_points), 2) if faculty_avg_points else None,
        percentile=round(percentile_points, 2)
    ))

    # 2. Intercambios completados
    my_exchanges = (
        db.query(Exchange)
        .filter(
            or_(Exchange.buyer_id == user_id, Exchange.seller_id == user_id),
            Exchange.status == 'completed'
        )
        .count()
    )
    avg_exchanges = (
        db.query(func.count(Exchange.id) / func.count(func.distinct(
            func.coalesce(Exchange.buyer_id, Exchange.seller_id)
        )))
        .filter(Exchange.status == 'completed')
        .scalar() or 0
    )

    comparisons.append(ComparisonStats(
        metric_name="Intercambios Completados",
        my_value=float(my_exchanges),
        platform_average=round(float(avg_exchanges), 2),
        faculty_average=None,
        percentile=0.0  # Calcular si es necesario
    ))

    # 3. Rating promedio
    my_rating_result = (
        db.query(func.avg(ExchangeRating.rating))
        .filter(ExchangeRating.rated_user_id == user_id)
        .scalar()
    )
    my_rating = float(my_rating_result) if my_rating_result else 0.0

    avg_rating = db.query(func.avg(ExchangeRating.rating)).scalar() or 0

    comparisons.append(ComparisonStats(
        metric_name="Rating Promedio",
        my_value=round(my_rating, 2),
        platform_average=round(float(avg_rating), 2),
        faculty_average=None,
        percentile=0.0
    ))

    return comparisons
