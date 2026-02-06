"""
Endpoints de retos/challenges de gamificacion.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.deps import get_db, get_current_active_user
from app.crud.challenge import challenge as crud_challenge
from app.schemas.challenge import ChallengeResponse, UserChallengeResponse
from app.schemas.common import MessageResponse
from app.models.user import User
from app.models.gamification import Challenge
from app.services.activity_log_service import log_activity, ActionTypes, EntityTypes

router = APIRouter()


@router.get("", response_model=List[ChallengeResponse])
def get_challenges(
    db: Session = Depends(get_db)
):
    """
    Obtener lista de retos activos disponibles.

    No requiere autenticacion.
    Retorna los 30 retos activos.
    """
    challenges = crud_challenge.get_active_challenges(db, limit=30)
    return [ChallengeResponse.model_validate(c) for c in challenges]


@router.get("/{challenge_id}", response_model=ChallengeResponse)
def get_challenge(
    challenge_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener detalle de un reto específico.
    """
    challenge = crud_challenge.get(db, id=challenge_id)

    if not challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Reto no encontrado"
        )

    return ChallengeResponse.model_validate(challenge)


@router.post("/{challenge_id}/join", response_model=UserChallengeResponse, status_code=status.HTTP_201_CREATED)
def join_challenge(
    challenge_id: int,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Inscribirse a un reto.

    Si ya estás inscrito, retorna tu progreso actual.
    Solo usuarios con rol 'estudiante' pueden participar.
    """
    # Bloquear admin y moderador
    if current_user.role in ['administrador', 'moderador']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los administradores y moderadores no pueden participar en retos"
        )

    try:
        user_challenge = crud_challenge.join_challenge(
            db, user_id=current_user.id, challenge_id=challenge_id
        )

        # Obtener info del challenge
        challenge = crud_challenge.get(db, id=challenge_id)

        response = UserChallengeResponse.model_validate(user_challenge)
        response.challenge_title = challenge.title if challenge else None
        response.challenge_description = challenge.description if challenge else None
        response.challenge_icon = challenge.icon if challenge else None
        response.points_reward = challenge.points_reward if challenge else None

        # Registrar actividad
        log_activity(
            db=db,
            action_type=ActionTypes.JOIN_CHALLENGE,
            user_id=current_user.id,
            entity_type=EntityTypes.CHALLENGE,
            entity_id=None,  # challenge_id es int, no UUID
            extra_data={"challenge_id": challenge_id, "challenge_title": challenge.title if challenge else None},
            ip_address=x_forwarded_for,
            user_agent=user_agent
        )

        return response

    except ValueError as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.get("/my/challenges", response_model=List[UserChallengeResponse])
def get_my_challenges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener mis retos inscritos.

    Requiere autenticacion.
    Retorna los 30 retos mas recientes del usuario.
    Admin/moderador reciben lista vacía.
    """
    # Admin/moderador no participan en retos
    if current_user.role in ['administrador', 'moderador']:
        return []

    from app.models.gamification import UserChallenge

    user_challenges = (
        db.query(UserChallenge)
        .filter(UserChallenge.user_id == current_user.id)
        .order_by(UserChallenge.started_at.desc())
        .limit(30)
        .all()
    )

    # Enriquecer respuesta
    enriched_challenges = []
    for uc in user_challenges:
        challenge = crud_challenge.get(db, id=uc.challenge_id)

        response = UserChallengeResponse.model_validate(uc)
        response.challenge_title = challenge.title if challenge else None
        response.challenge_description = challenge.description if challenge else None
        response.challenge_icon = challenge.icon if challenge else None
        response.points_reward = challenge.points_reward if challenge else None

        enriched_challenges.append(response)

    return enriched_challenges


@router.get("/my/progress/{challenge_id}", response_model=UserChallengeResponse)
def get_my_challenge_progress(
    challenge_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener mi progreso en un reto específico.
    """
    user_challenge = crud_challenge.get_user_challenge(
        db, user_id=current_user.id, challenge_id=challenge_id
    )

    if not user_challenge:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No estás inscrito en este reto"
        )

    # Obtener info del challenge
    challenge = crud_challenge.get(db, id=challenge_id)

    response = UserChallengeResponse.model_validate(user_challenge)
    response.challenge_title = challenge.title if challenge else None
    response.challenge_description = challenge.description if challenge else None
    response.challenge_icon = challenge.icon if challenge else None
    response.points_reward = challenge.points_reward if challenge else None

    return response
