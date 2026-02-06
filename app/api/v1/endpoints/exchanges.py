"""
Endpoints de intercambios y valoraciones.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from uuid import UUID
from datetime import datetime
from typing import Optional, List

from app.core.deps import get_db, get_current_active_user
from app.crud.exchange import exchange as crud_exchange
from app.schemas.exchange import (
    ExchangeCreate,
    ExchangeUpdate,
    ExchangeConfirm,
    ExchangeResponse,
    ExchangeDetailResponse,
    ExchangeRatingCreate,
    ExchangeRatingResponse
)
from app.schemas.common import MessageResponse
from app.models.user import User
from app.models.exchange import Exchange, ExchangeEvent, ExchangeRating
from app.models.offer import Offer
from app.models.offer_photo import OfferPhoto
from app.models.location import Location
from app.services.notification_service import (
    notify_exchange_created,
    notify_exchange_accepted,
    notify_exchange_cancelled,
    notify_exchange_completed
)
from app.services.activity_log_service import log_activity, ActionTypes, EntityTypes

router = APIRouter()


@router.get("", response_model=List[ExchangeDetailResponse])
def get_my_exchanges(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener intercambios del usuario actual.

    Requiere autenticacion.
    Retorna los 50 intercambios mas recientes del usuario.
    """
    # Obtener intercambios donde el usuario es participante
    exchanges = (
        db.query(Exchange)
        .filter(
            or_(
                Exchange.buyer_id == current_user.id,
                Exchange.seller_id == current_user.id
            )
        )
        .order_by(desc(Exchange.created_at))
        .limit(50)
        .all()
    )

    # Enriquecer respuesta
    enriched_exchanges = []
    for exchange in exchanges:
        # Obtener datos relacionados
        offer = db.query(Offer).filter(Offer.id == exchange.offer_id).first()
        offer_photo = (
            db.query(OfferPhoto)
            .filter(OfferPhoto.offer_id == exchange.offer_id, OfferPhoto.is_primary == True)
            .first()
        )
        buyer = db.query(User).filter(User.id == exchange.buyer_id).first()
        seller = db.query(User).filter(User.id == exchange.seller_id).first()
        location = db.query(Location).filter(Location.id == exchange.location_id).first() if exchange.location_id else None

        # Construir respuesta
        ex_response = ExchangeDetailResponse.model_validate(exchange)
        ex_response.offer_title = offer.title if offer else None
        ex_response.offer_photo = offer_photo.photo_url if offer_photo else None
        ex_response.buyer_name = buyer.full_name if buyer else None
        ex_response.buyer_photo = buyer.profile_photo_url if buyer else None
        ex_response.seller_name = seller.full_name if seller else None
        ex_response.seller_photo = seller.profile_photo_url if seller else None
        ex_response.location_name = location.name if location else None

        enriched_exchanges.append(ex_response)

    return enriched_exchanges


@router.get("/{exchange_id}", response_model=ExchangeDetailResponse)
def get_exchange(
    exchange_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener detalle de un intercambio específico.

    El usuario debe ser participante del intercambio (buyer o seller).
    """
    exchange = crud_exchange.get(db, id=exchange_id)

    if not exchange:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intercambio no encontrado"
        )

    # Verificar que el usuario es participante
    if exchange.buyer_id != current_user.id and exchange.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este intercambio"
        )

    # Obtener datos relacionados
    offer = db.query(Offer).filter(Offer.id == exchange.offer_id).first()
    offer_photo = (
        db.query(OfferPhoto)
        .filter(OfferPhoto.offer_id == exchange.offer_id, OfferPhoto.is_primary == True)
        .first()
    )
    buyer = db.query(User).filter(User.id == exchange.buyer_id).first()
    seller = db.query(User).filter(User.id == exchange.seller_id).first()
    location = db.query(Location).filter(Location.id == exchange.location_id).first() if exchange.location_id else None

    # Construir respuesta
    response = ExchangeDetailResponse.model_validate(exchange)
    response.offer_title = offer.title if offer else None
    response.offer_photo = offer_photo.photo_url if offer_photo else None
    response.buyer_name = buyer.full_name if buyer else None
    response.buyer_photo = buyer.profile_photo_url if buyer else None
    response.seller_name = seller.full_name if seller else None
    response.seller_photo = seller.profile_photo_url if seller else None
    response.location_name = location.name if location else None

    return response


@router.post("", response_model=ExchangeResponse, status_code=status.HTTP_201_CREATED)
def create_exchange(
    exchange_in: ExchangeCreate,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Crear una propuesta de intercambio.

    El usuario actual será el buyer. El seller es el dueño de la oferta.
    """
    # Obtener la oferta
    offer = db.query(Offer).filter(Offer.id == exchange_in.offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    # Verificar que la oferta está activa
    if offer.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="La oferta no está disponible para intercambio"
        )

    # Verificar que el usuario no sea el dueño de la oferta
    if offer.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes crear un intercambio con tu propia oferta"
        )

    # Generar UUID para el intercambio
    import uuid as uuid_module
    exchange_id = uuid_module.uuid4()

    # Crear intercambio con ID explícito
    new_exchange = Exchange(
        id=exchange_id,
        offer_id=exchange_in.offer_id,
        buyer_id=current_user.id,
        seller_id=offer.user_id,
        location_id=exchange_in.location_id,
        scheduled_at=exchange_in.scheduled_at,
        credits_amount=offer.credits_value,
        status='pending'
    )
    db.add(new_exchange)

    # Crear evento con el ID conocido
    event = ExchangeEvent(
        exchange_id=exchange_id,
        event_type='created',
        by_user_id=current_user.id,
        notes=getattr(exchange_in, 'notes', None)
    )
    db.add(event)

    # Actualizar estado de la oferta
    offer.status = 'reserved'

    db.commit()
    db.refresh(new_exchange)

    # Notificar al vendedor
    notify_exchange_created(
        db=db,
        seller_id=offer.user_id,
        buyer_name=current_user.full_name,
        offer_title=offer.title,
        exchange_id=new_exchange.id
    )

    # Registrar actividad
    log_activity(
        db=db,
        action_type=ActionTypes.CREATE_EXCHANGE,
        user_id=current_user.id,
        entity_type=EntityTypes.EXCHANGE,
        entity_id=new_exchange.id,
        extra_data={"offer_id": str(exchange_in.offer_id), "offer_title": offer.title, "seller_id": str(offer.user_id)},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    return ExchangeResponse.model_validate(new_exchange)


@router.post("/{exchange_id}/accept", response_model=MessageResponse)
def accept_exchange(
    exchange_id: UUID,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Aceptar una propuesta de intercambio (seller).
    """
    exchange = crud_exchange.get(db, id=exchange_id)

    if not exchange:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intercambio no encontrado"
        )

    # Verificar que el usuario es el seller
    if exchange.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el vendedor puede aceptar el intercambio"
        )

    # Verificar estado
    if exchange.status != 'pending':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede aceptar un intercambio en estado '{exchange.status}'"
        )

    # Actualizar estado
    exchange.status = 'accepted'

    # Crear evento
    event = ExchangeEvent(
        exchange_id=exchange_id,
        event_type='accepted',
        by_user_id=current_user.id
    )
    db.add(event)

    db.commit()

    # Notificar al comprador
    offer = db.query(Offer).filter(Offer.id == exchange.offer_id).first()
    notify_exchange_accepted(
        db=db,
        buyer_id=exchange.buyer_id,
        offer_title=offer.title if offer else "Oferta",
        exchange_id=exchange.id
    )

    # Registrar actividad
    log_activity(
        db=db,
        action_type=ActionTypes.ACCEPT_EXCHANGE,
        user_id=current_user.id,
        entity_type=EntityTypes.EXCHANGE,
        entity_id=exchange_id,
        extra_data={"buyer_id": str(exchange.buyer_id), "offer_title": offer.title if offer else None},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    return MessageResponse(message="Intercambio aceptado exitosamente")


@router.post("/{exchange_id}/confirm", response_model=MessageResponse)
def confirm_exchange(
    exchange_id: UUID,
    confirm_data: Optional[ExchangeConfirm] = None,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Confirmar que se realizó el intercambio (buyer o seller).

    Cuando ambas partes confirman, el intercambio se marca como completado.
    """
    exchange = crud_exchange.get(db, id=exchange_id)

    if not exchange:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intercambio no encontrado"
        )

    # Verificar que el usuario es participante
    if exchange.buyer_id != current_user.id and exchange.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este intercambio"
        )

    # Verificar estado
    if exchange.status not in ['accepted', 'in_progress']:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"No se puede confirmar un intercambio en estado '{exchange.status}'"
        )

    # Registrar confirmación
    is_buyer = exchange.buyer_id == current_user.id
    event_type = 'check_in_buyer' if is_buyer else 'check_in_seller'

    if is_buyer:
        if exchange.buyer_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya has confirmado este intercambio"
            )
        exchange.buyer_confirmed = True
        exchange.buyer_confirmed_at = datetime.utcnow()
    else:
        if exchange.seller_confirmed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Ya has confirmado este intercambio"
            )
        exchange.seller_confirmed = True
        exchange.seller_confirmed_at = datetime.utcnow()

    # Si está en pending, cambiarlo a in_progress
    if exchange.status == 'accepted':
        exchange.status = 'in_progress'

    # Crear evento
    event = ExchangeEvent(
        exchange_id=exchange_id,
        event_type=event_type,
        by_user_id=current_user.id,
        notes=confirm_data.notes if confirm_data else None
    )
    db.add(event)

    # Si ambos confirmaron, completar el intercambio
    if exchange.buyer_confirmed and exchange.seller_confirmed:
        exchange.status = 'completed'
        exchange.completed_at = datetime.utcnow()

        # Crear evento de completado
        complete_event = ExchangeEvent(
            exchange_id=exchange_id,
            event_type='completed',
            by_user_id=current_user.id
        )
        db.add(complete_event)

        # Actualizar oferta
        offer = db.query(Offer).filter(Offer.id == exchange.offer_id).first()
        if offer:
            offer.status = 'completed'

        # Procesar créditos
        from app.crud.reward import reward as crud_reward

        # Descontar créditos al buyer
        crud_reward.add_credits_transaction(
            db,
            user_id=exchange.buyer_id,
            transaction_type='exchange_payment',
            amount=-exchange.credits_amount,
            reference_id=exchange_id,
            description=f"Pago por intercambio: {offer.title if offer else 'N/A'}"
        )

        # Abonar créditos al seller
        crud_reward.add_credits_transaction(
            db,
            user_id=exchange.seller_id,
            transaction_type='exchange_received',
            amount=exchange.credits_amount,
            reference_id=exchange_id,
            description=f"Recibo por intercambio: {offer.title if offer else 'N/A'}"
        )

        # Otorgar puntos de sostenibilidad a ambos
        buyer = db.query(User).filter(User.id == exchange.buyer_id).first()
        seller = db.query(User).filter(User.id == exchange.seller_id).first()

        if buyer:
            buyer.sustainability_points += 10
            buyer.experience_points += 15
        if seller:
            seller.sustainability_points += 10
            seller.experience_points += 15

        # Notificar a ambas partes
        notify_exchange_completed(
            db=db,
            user_id=exchange.buyer_id,
            offer_title=offer.title if offer else "Oferta",
            exchange_id=exchange.id,
            points_earned=10
        )
        notify_exchange_completed(
            db=db,
            user_id=exchange.seller_id,
            offer_title=offer.title if offer else "Oferta",
            exchange_id=exchange.id,
            points_earned=10
        )

    db.commit()

    # Registrar actividad
    action_type = ActionTypes.COMPLETE_EXCHANGE if exchange.status == 'completed' else ActionTypes.CONFIRM_EXCHANGE
    log_activity(
        db=db,
        action_type=action_type,
        user_id=current_user.id,
        entity_type=EntityTypes.EXCHANGE,
        entity_id=exchange_id,
        extra_data={"status": exchange.status, "role": "buyer" if is_buyer else "seller"},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    message = "Intercambio completado exitosamente" if exchange.status == 'completed' else "Confirmación registrada"
    return MessageResponse(message=message)


@router.post("/{exchange_id}/cancel", response_model=MessageResponse)
def cancel_exchange(
    exchange_id: UUID,
    cancellation_data: ExchangeUpdate,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Cancelar un intercambio.

    Requiere proporcionar razón de cancelación.
    """
    exchange = crud_exchange.get(db, id=exchange_id)

    if not exchange:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intercambio no encontrado"
        )

    # Verificar que el usuario es participante
    if exchange.buyer_id != current_user.id and exchange.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este intercambio"
        )

    # Verificar que no esté completado
    if exchange.status == 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se puede cancelar un intercambio completado"
        )

    # Actualizar estado
    exchange.status = 'cancelled'
    exchange.cancellation_reason = cancellation_data.cancellation_reason

    # Crear evento
    event = ExchangeEvent(
        exchange_id=exchange_id,
        event_type='cancelled',
        by_user_id=current_user.id,
        notes=cancellation_data.cancellation_reason
    )
    db.add(event)

    # Reactivar oferta
    offer = db.query(Offer).filter(Offer.id == exchange.offer_id).first()
    if offer:
        offer.status = 'active'

    db.commit()

    # Notificar a la otra parte
    other_user_id = exchange.seller_id if exchange.buyer_id == current_user.id else exchange.buyer_id
    notify_exchange_cancelled(
        db=db,
        user_id=other_user_id,
        offer_title=offer.title if offer else "Oferta",
        cancelled_by=current_user.full_name,
        exchange_id=exchange.id
    )

    # Registrar actividad
    log_activity(
        db=db,
        action_type=ActionTypes.CANCEL_EXCHANGE,
        user_id=current_user.id,
        entity_type=EntityTypes.EXCHANGE,
        entity_id=exchange_id,
        extra_data={"reason": cancellation_data.cancellation_reason, "offer_title": offer.title if offer else None},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    return MessageResponse(message="Intercambio cancelado exitosamente")


@router.post("/{exchange_id}/rate", response_model=ExchangeRatingResponse, status_code=status.HTTP_201_CREATED)
def rate_exchange(
    exchange_id: UUID,
    rating_in: ExchangeRatingCreate,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Valorar a la otra parte después de un intercambio.

    Solo disponible para intercambios completados.
    """
    exchange = crud_exchange.get(db, id=exchange_id)

    if not exchange:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intercambio no encontrado"
        )

    # Verificar que el usuario es participante
    if exchange.buyer_id != current_user.id and exchange.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este intercambio"
        )

    # Verificar que el intercambio está completado
    if exchange.status != 'completed':
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Solo se pueden valorar intercambios completados"
        )

    # Determinar quién es el rated_user
    rated_user_id = exchange.seller_id if exchange.buyer_id == current_user.id else exchange.buyer_id

    # Verificar que no haya valorado ya
    existing_rating = (
        db.query(ExchangeRating)
        .filter(
            ExchangeRating.exchange_id == exchange_id,
            ExchangeRating.rater_user_id == current_user.id
        )
        .first()
    )

    if existing_rating:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Ya has valorado este intercambio"
        )

    # Crear valoración
    new_rating = ExchangeRating(
        exchange_id=exchange_id,
        rater_user_id=current_user.id,
        rated_user_id=rated_user_id,
        rating=rating_in.rating,
        comment=rating_in.comment
    )
    db.add(new_rating)

    # Actualizar métricas de reputación del usuario valorado
    from app.models.user_reputation_metrics import UserReputationMetrics

    metrics = (
        db.query(UserReputationMetrics)
        .filter(UserReputationMetrics.user_id == rated_user_id)
        .first()
    )

    if metrics:
        # Recalcular promedio
        total_ratings = metrics.total_ratings + 1
        new_average = (
            (metrics.average_rating * metrics.total_ratings) + rating_in.rating
        ) / total_ratings

        metrics.average_rating = new_average
        metrics.total_ratings = total_ratings
    else:
        # Crear métricas si no existen
        metrics = UserReputationMetrics(
            user_id=rated_user_id,
            average_rating=float(rating_in.rating),
            total_ratings=1
        )
        db.add(metrics)

    db.commit()
    db.refresh(new_rating)

    # Registrar actividad
    log_activity(
        db=db,
        action_type=ActionTypes.RATE_EXCHANGE,
        user_id=current_user.id,
        entity_type=EntityTypes.EXCHANGE,
        entity_id=exchange_id,
        extra_data={"rating": rating_in.rating, "rated_user_id": str(rated_user_id)},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    return ExchangeRatingResponse.model_validate(new_rating)


@router.get("/{exchange_id}/ratings", response_model=list[ExchangeRatingResponse])
def get_exchange_ratings(
    exchange_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener valoraciones de un intercambio.

    El usuario debe ser participante del intercambio.
    """
    exchange = crud_exchange.get(db, id=exchange_id)

    if not exchange:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Intercambio no encontrado"
        )

    # Verificar que el usuario es participante
    if exchange.buyer_id != current_user.id and exchange.seller_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a este intercambio"
        )

    # Obtener valoraciones
    ratings = (
        db.query(ExchangeRating)
        .filter(ExchangeRating.exchange_id == exchange_id)
        .all()
    )

    return [ExchangeRatingResponse.model_validate(r) for r in ratings]
