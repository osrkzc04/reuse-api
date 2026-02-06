"""
Endpoints de intereses en ofertas.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.core.deps import get_db, get_current_active_user
from app.schemas.offer_interest import OfferInterestCreate, OfferInterestResponse, OfferInterestDetailResponse
from app.schemas.common import MessageResponse
from app.models.user import User
from app.models.offer import Offer
from app.models.offer_interest import OfferInterest
from app.models.offer_photo import OfferPhoto
from app.services.notification_service import notify_new_interest

router = APIRouter()


@router.post("/offers/{offer_id}/interest", response_model=OfferInterestResponse, status_code=status.HTTP_201_CREATED)
def show_interest(
    offer_id: UUID,
    interest_in: OfferInterestCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Mostrar interés en una oferta.

    Esto notifica al dueño de la oferta que alguien está interesado.
    El usuario no puede mostrar interés en su propia oferta.
    """
    # Verificar que la oferta existe
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    # Verificar que la oferta está activa
    if offer.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La oferta no está disponible"
        )

    # Verificar que no sea el dueño de la oferta
    if offer.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes mostrar interés en tu propia oferta"
        )

    # Verificar que no haya mostrado interés previamente
    existing_interest = (
        db.query(OfferInterest)
        .filter(
            OfferInterest.offer_id == offer_id,
            OfferInterest.user_id == current_user.id
        )
        .first()
    )

    if existing_interest:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya has mostrado interés en esta oferta"
        )

    # Crear interés
    new_interest = OfferInterest(
        offer_id=offer_id,
        user_id=current_user.id,
        notes=interest_in.notes,
        status='pending'
    )
    db.add(new_interest)
    db.commit()
    db.refresh(new_interest)

    # Notificar al dueño de la oferta
    notify_new_interest(
        db=db,
        offer_owner_id=offer.user_id,
        interested_user_name=current_user.full_name,
        offer_title=offer.title,
        offer_id=offer.id
    )

    return OfferInterestResponse.model_validate(new_interest)


@router.get("/offers/{offer_id}/interests", response_model=List[OfferInterestDetailResponse])
def get_offer_interests(
    offer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener lista de usuarios interesados en una oferta.

    Solo el dueno de la oferta puede ver esta informacion.
    Retorna los 50 intereses mas recientes.
    """
    # Verificar que la oferta existe
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    # Verificar que es el dueno de la oferta
    if offer.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el dueno de la oferta puede ver los interesados"
        )

    # Obtener intereses
    interests = (
        db.query(OfferInterest)
        .filter(OfferInterest.offer_id == offer_id)
        .order_by(OfferInterest.created_at.desc())
        .limit(50)
        .all()
    )

    # Enriquecer respuesta con informacion del usuario
    enriched_interests = []
    for interest in interests:
        user = db.query(User).filter(User.id == interest.user_id).first()

        interest_response = OfferInterestDetailResponse.model_validate(interest)
        interest_response.offer_title = offer.title
        interest_response.user_name = user.full_name if user else None
        interest_response.user_photo = user.profile_photo_url if user else None

        enriched_interests.append(interest_response)

    return enriched_interests


@router.get("/my-interests", response_model=List[OfferInterestDetailResponse])
def get_my_interests(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener lista de ofertas en las que el usuario ha mostrado interes.

    Requiere autenticacion.
    Retorna los 50 intereses mas recientes.
    """
    interests = (
        db.query(OfferInterest)
        .filter(OfferInterest.user_id == current_user.id)
        .order_by(OfferInterest.created_at.desc())
        .limit(50)
        .all()
    )

    # Enriquecer respuesta con informacion de la oferta
    enriched_interests = []
    for interest in interests:
        offer = db.query(Offer).filter(Offer.id == interest.offer_id).first()
        offer_photo = (
            db.query(OfferPhoto)
            .filter(OfferPhoto.offer_id == interest.offer_id, OfferPhoto.is_primary == True)
            .first()
        )

        interest_response = OfferInterestDetailResponse.model_validate(interest)
        interest_response.offer_title = offer.title if offer else None
        interest_response.offer_photo = offer_photo.photo_url if offer_photo else None
        interest_response.user_name = current_user.full_name
        interest_response.user_photo = current_user.profile_photo_url

        enriched_interests.append(interest_response)

    return enriched_interests


@router.delete("/interests/{interest_id}", response_model=MessageResponse)
def remove_interest(
    interest_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Eliminar un interés mostrado.

    Solo el usuario que mostró el interés puede eliminarlo.
    """
    interest = db.query(OfferInterest).filter(OfferInterest.id == interest_id).first()

    if not interest:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Interés no encontrado"
        )

    # Verificar que es el dueño del interés
    if interest.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No puedes eliminar este interés"
        )

    db.delete(interest)
    db.commit()

    return MessageResponse(message="Interés eliminado exitosamente")
