"""
Endpoints de recompensas y creditos.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from typing import List

from app.core.deps import get_db, get_current_active_user, get_current_admin_user
from app.crud.reward import reward as crud_reward
from app.schemas.reward import (
    RewardResponse,
    RewardClaimCreate,
    RewardClaimResponse,
    RewardClaimUpdate,
    CreditsLedgerResponse,
    CreditsBalance
)
from app.schemas.common import MessageResponse, PaginatedResponse
from app.models.user import User

router = APIRouter()


@router.get("", response_model=List[RewardResponse])
def get_rewards(
    db: Session = Depends(get_db)
):
    """
    Obtener catalogo de recompensas.

    No requiere autenticacion.
    Retorna las 30 recompensas activas con stock disponible.
    """
    rewards = crud_reward.get_active_rewards(db, limit=30)
    return [RewardResponse.model_validate(r) for r in rewards]


@router.get("/{reward_id}", response_model=RewardResponse)
def get_reward(
    reward_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener detalle de una recompensa específica.
    """
    reward = crud_reward.get(db, id=reward_id)

    if not reward:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Recompensa no encontrada"
        )

    return RewardResponse.model_validate(reward)


@router.post("/claim", response_model=RewardClaimResponse, status_code=status.HTTP_201_CREATED)
def claim_reward(
    claim_in: RewardClaimCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Reclamar una recompensa.

    Descontará los créditos necesarios del usuario y creará una reclamación pendiente.
    """
    try:
        claim = crud_reward.claim_reward(
            db, user_id=current_user.id, reward_id=claim_in.reward_id
        )

        # Obtener info de la recompensa
        reward = crud_reward.get(db, id=claim_in.reward_id)

        response = RewardClaimResponse.model_validate(claim)
        response.reward = RewardResponse.model_validate(reward) if reward else None

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my/claims", response_model=List[RewardClaimResponse])
def get_my_claims(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener mis reclamaciones de recompensas.

    Requiere autenticacion.
    Retorna las 30 reclamaciones mas recientes.
    """
    claims = crud_reward.get_user_claims(db, user_id=current_user.id, limit=30)

    # Enriquecer respuesta con info de la recompensa
    enriched_claims = []
    for claim in claims:
        reward = crud_reward.get(db, id=claim.reward_id)

        response = RewardClaimResponse.model_validate(claim)
        response.reward = RewardResponse.model_validate(reward) if reward else None

        enriched_claims.append(response)

    return enriched_claims


@router.get("/credits/balance", response_model=CreditsBalance)
def get_my_credits_balance(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener mi balance de créditos actual.

    Incluye balance actual, total ganado, total gastado y transacciones recientes.
    """
    from app.models.credits import CreditsLedger
    from sqlalchemy import func

    # Balance actual
    current_balance = crud_reward.get_user_balance(db, user_id=current_user.id)

    # Total ganado (transacciones positivas)
    total_earned = (
        db.query(func.sum(CreditsLedger.amount))
        .filter(
            CreditsLedger.user_id == current_user.id,
            CreditsLedger.amount > 0
        )
        .scalar() or 0
    )

    # Total gastado (transacciones negativas)
    total_spent = abs(
        db.query(func.sum(CreditsLedger.amount))
        .filter(
            CreditsLedger.user_id == current_user.id,
            CreditsLedger.amount < 0
        )
        .scalar() or 0
    )

    # Transacciones recientes
    recent_transactions = crud_reward.get_user_transactions(
        db, user_id=current_user.id, limit=10
    )

    return CreditsBalance(
        current_balance=current_balance,
        total_earned=int(total_earned),
        total_spent=int(total_spent),
        recent_transactions=[
            CreditsLedgerResponse.model_validate(t) for t in recent_transactions
        ]
    )


@router.get("/credits/transactions", response_model=List[CreditsLedgerResponse])
def get_my_transactions(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener historial de transacciones de creditos.

    Requiere autenticacion.
    Retorna las 50 transacciones mas recientes.
    """
    transactions = crud_reward.get_user_transactions(db, user_id=current_user.id, limit=50)
    return [CreditsLedgerResponse.model_validate(t) for t in transactions]


# ============================================================================
# ADMIN ENDPOINTS
# ============================================================================

@router.get("/admin/claims", response_model=PaginatedResponse[RewardClaimResponse])
def get_pending_claims_admin(
    skip: int = Query(0, ge=0),
    limit: int = Query(20, le=100),
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Obtener reclamaciones pendientes (admin).
    """
    claims = crud_reward.get_pending_claims(db, skip=skip, limit=limit)

    from app.models.credits import RewardClaim
    total = db.query(RewardClaim).filter(RewardClaim.status == 'pending').count()

    # Enriquecer respuesta
    enriched_claims = []
    for claim in claims:
        reward = crud_reward.get(db, id=claim.reward_id)
        user = db.query(User).filter(User.id == claim.user_id).first()

        response = RewardClaimResponse.model_validate(claim)
        response.reward = RewardResponse.model_validate(reward) if reward else None

        enriched_claims.append(response)

    return PaginatedResponse(
        items=enriched_claims,
        total=total,
        skip=skip,
        limit=limit
    )


@router.patch("/admin/claims/{claim_id}", response_model=RewardClaimResponse)
def update_claim_status_admin(
    claim_id: int,
    update_data: RewardClaimUpdate,
    db: Session = Depends(get_db),
    admin_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar estado de una reclamación (admin).

    Estados: pending, approved, delivered, rejected
    """
    updated_claim = crud_reward.update_claim_status(
        db,
        claim_id=claim_id,
        status=update_data.status,
        notes=update_data.notes
    )

    if not updated_claim:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reclamación no encontrada"
        )

    # Obtener info de la recompensa
    reward = crud_reward.get(db, id=updated_claim.reward_id)

    response = RewardClaimResponse.model_validate(updated_claim)
    response.reward = RewardResponse.model_validate(reward) if reward else None

    return response
