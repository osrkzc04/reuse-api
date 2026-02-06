"""
Endpoints de ofertas.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query, Header
from sqlalchemy.orm import Session
from uuid import UUID
from typing import Optional, List

from app.core.deps import get_db, get_current_active_user
from app.crud.offer import offer as crud_offer
from app.schemas.offer import OfferCreate, OfferUpdate, OfferResponse, OfferDetailResponse
from app.schemas.common import MessageResponse
from app.models.user import User
from app.services.activity_log_service import log_activity, ActionTypes, EntityTypes

router = APIRouter()


@router.get("", response_model=List[OfferResponse])
def get_offers(
    category_id: Optional[int] = None,
    db: Session = Depends(get_db)
):
    """
    Obtener lista de ofertas (feed principal).

    Parametros:
    - category_id: Filtrar por categoria (opcional)

    No requiere autenticacion.
    Retorna las 100 ofertas mas recientes.
    """
    if category_id:
        offers = crud_offer.get_by_category(db, category_id=category_id, limit=100)
    else:
        offers = crud_offer.get_active_offers(db, limit=100)

    return offers


@router.get("/my-offers", response_model=List[OfferResponse])
def get_my_offers(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener mis ofertas.

    Requiere autenticacion.
    Retorna las 50 ofertas mas recientes del usuario actual.
    """
    offers = crud_offer.get_by_user(db, user_id=current_user.id, limit=50)
    return offers


@router.get("/{offer_id}", response_model=OfferDetailResponse)
def get_offer(
    offer_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Obtener detalle de una oferta específica.

    Incrementa el contador de vistas.
    No requiere autenticación.
    """
    offer = crud_offer.get(db, id=offer_id)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    # Incrementar vistas
    crud_offer.increment_views(db, offer_id=offer_id)

    # Construir respuesta detallada
    from app.models.user import User
    from app.models.category import Category
    from app.models.location import Location
    from app.models.user_reputation_metrics import UserReputationMetrics

    user = db.query(User).filter(User.id == offer.user_id).first()
    category = db.query(Category).filter(Category.id == offer.category_id).first()
    location = db.query(Location).filter(Location.id == offer.location_id).first() if offer.location_id else None
    metrics = db.query(UserReputationMetrics).filter(
        UserReputationMetrics.user_id == offer.user_id
    ).first()

    response = OfferDetailResponse.model_validate(offer)
    response.user_name = user.full_name if user else None
    response.user_photo = user.profile_photo_url if user else None
    response.user_rating = float(metrics.average_rating) if metrics else None
    response.category_name = category.name if category else None
    response.location_name = location.name if location else None

    return response


@router.post("", response_model=OfferResponse, status_code=status.HTTP_201_CREATED)
def create_offer(
    offer_in: OfferCreate,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Crear nueva oferta.

    Requiere autenticación.
    Solo usuarios con rol 'estudiante' pueden crear ofertas.

    Campos requeridos:
    - title: Título de la oferta (5-200 caracteres)
    - description: Descripción detallada (mín 20 caracteres)
    - category_id: ID de la categoría
    - condition: Estado del objeto (nuevo, como_nuevo, buen_estado, usado, para_reparar)

    Campos opcionales:
    - location_id: ID de la ubicación preferida para intercambio
    - credits_value: Valor en créditos (default: 0)
    """
    # Bloquear admin y moderador
    if current_user.role in ['administrador', 'moderador']:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Los administradores y moderadores no pueden crear publicaciones"
        )

    offer = crud_offer.create(db, obj_in=offer_in, user_id=current_user.id)

    # Registrar actividad
    log_activity(
        db=db,
        action_type=ActionTypes.CREATE_OFFER,
        user_id=current_user.id,
        entity_type=EntityTypes.OFFER,
        entity_id=offer.id,
        extra_data={"title": offer.title, "category_id": offer.category_id},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    return offer


@router.put("/{offer_id}", response_model=OfferResponse)
def update_offer(
    offer_id: UUID,
    offer_update: OfferUpdate,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Actualizar oferta existente.

    Requiere autenticación.
    Solo el dueño de la oferta puede actualizarla.
    """
    offer = crud_offer.get(db, id=offer_id)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    if str(offer.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para editar esta oferta"
        )

    updated_offer = crud_offer.update(db, db_obj=offer, obj_in=offer_update)

    # Registrar actividad
    log_activity(
        db=db,
        action_type=ActionTypes.UPDATE_OFFER,
        user_id=current_user.id,
        entity_type=EntityTypes.OFFER,
        entity_id=offer_id,
        extra_data={"title": updated_offer.title},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    return updated_offer


@router.delete("/{offer_id}", response_model=MessageResponse)
def delete_offer(
    offer_id: UUID,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Eliminar oferta (soft delete).

    Requiere autenticación.
    Solo el dueño puede eliminar su oferta.

    La oferta no se elimina físicamente, se marca como eliminada
    (deleted_at) y su status cambia a 'cancelled'.
    """
    offer = crud_offer.get(db, id=offer_id)

    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    if str(offer.user_id) != str(current_user.id):
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para eliminar esta oferta"
        )

    # Registrar actividad antes del delete
    log_activity(
        db=db,
        action_type=ActionTypes.DELETE_OFFER,
        user_id=current_user.id,
        entity_type=EntityTypes.OFFER,
        entity_id=offer_id,
        extra_data={"title": offer.title},
        ip_address=x_forwarded_for,
        user_agent=user_agent
    )

    # Soft delete: marca deleted_at y cambia status a cancelled
    crud_offer.soft_delete(db, id=offer_id)

    return MessageResponse(message="Oferta eliminada exitosamente")
