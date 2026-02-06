"""
Endpoints para gestión de fotos de ofertas.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List

from app.core.deps import get_db, get_current_active_user
from app.schemas.common import MessageResponse
from app.models.user import User
from app.models.offer import Offer
from app.models.offer_photo import OfferPhoto
from app.services.storage_service import storage_service
from pydantic import BaseModel, Field


# Schemas locales
class OfferPhotoCreate(BaseModel):
    """Schema para crear foto de oferta."""
    photo_url: str = Field(..., max_length=500)
    is_primary: bool = False

    model_config = {"from_attributes": True}


class OfferPhotoResponse(BaseModel):
    """Schema de respuesta de foto."""
    id: int
    offer_id: UUID
    photo_url: str
    is_primary: bool
    display_order: int

    model_config = {"from_attributes": True}


router = APIRouter()


@router.get("/offers/{offer_id}/photos", response_model=List[OfferPhotoResponse])
def get_offer_photos(
    offer_id: UUID,
    db: Session = Depends(get_db)
):
    """
    Obtener todas las fotos de una oferta.

    Endpoint público - no requiere autenticación.
    Las fotos se ordenan por display_order.
    """
    # Verificar que la oferta existe
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    photos = (
        db.query(OfferPhoto)
        .filter(OfferPhoto.offer_id == offer_id)
        .order_by(OfferPhoto.is_primary.desc(), OfferPhoto.display_order)
        .all()
    )

    return [OfferPhotoResponse.model_validate(photo) for photo in photos]


@router.post("/offers/{offer_id}/photos", response_model=OfferPhotoResponse, status_code=status.HTTP_201_CREATED)
def add_offer_photo(
    offer_id: UUID,
    photo_in: OfferPhotoCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Agregar una foto a una oferta.

    Solo el dueño de la oferta puede agregar fotos.
    Máximo 5 fotos por oferta.
    """
    # Verificar que la oferta existe y pertenece al usuario
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    if offer.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el dueño de la oferta puede agregar fotos"
        )

    # Verificar límite de fotos
    current_photos_count = (
        db.query(OfferPhoto)
        .filter(OfferPhoto.offer_id == offer_id)
        .count()
    )

    if current_photos_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Máximo 5 fotos por oferta"
        )

    # Si se marca como principal, quitar la marca de las demás
    if photo_in.is_primary:
        db.query(OfferPhoto).filter(
            OfferPhoto.offer_id == offer_id,
            OfferPhoto.is_primary == True
        ).update({"is_primary": False})

    # Calcular display_order
    max_order = (
        db.query(func.max(OfferPhoto.display_order))
        .filter(OfferPhoto.offer_id == offer_id)
        .scalar() or 0
    )

    # Crear foto
    new_photo = OfferPhoto(
        offer_id=offer_id,
        photo_url=photo_in.photo_url,
        is_primary=photo_in.is_primary,
        display_order=max_order + 1
    )
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)

    return OfferPhotoResponse.model_validate(new_photo)


@router.delete("/offers/{offer_id}/photos/{photo_id}", response_model=MessageResponse)
async def delete_offer_photo(
    offer_id: UUID,
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Eliminar una foto de una oferta.

    Solo el dueño de la oferta puede eliminar fotos.
    También elimina el archivo del storage (local o R2).
    """
    # Verificar que la oferta existe y pertenece al usuario
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    if offer.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el dueño de la oferta puede eliminar fotos"
        )

    # Verificar que la foto existe y pertenece a la oferta
    photo = (
        db.query(OfferPhoto)
        .filter(OfferPhoto.id == photo_id, OfferPhoto.offer_id == offer_id)
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foto no encontrada"
        )

    # Guardar object_key antes de eliminar de BD
    object_key = photo.object_key

    # Si era la foto principal, marcar la primera restante como principal
    was_primary = photo.is_primary
    db.delete(photo)
    db.commit()

    if was_primary:
        first_remaining = (
            db.query(OfferPhoto)
            .filter(OfferPhoto.offer_id == offer_id)
            .order_by(OfferPhoto.display_order)
            .first()
        )
        if first_remaining:
            first_remaining.is_primary = True
            db.commit()

    # Eliminar archivo del storage
    if object_key:
        await storage_service.delete_file(object_key)

    return MessageResponse(message="Foto eliminada exitosamente")


@router.patch("/offers/{offer_id}/photos/{photo_id}/primary", response_model=OfferPhotoResponse)
def set_primary_photo(
    offer_id: UUID,
    photo_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Marcar una foto como principal.

    Solo el dueño de la oferta puede modificar la foto principal.
    """
    # Verificar que la oferta existe y pertenece al usuario
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    if offer.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el dueño de la oferta puede modificar fotos"
        )

    # Verificar que la foto existe
    photo = (
        db.query(OfferPhoto)
        .filter(OfferPhoto.id == photo_id, OfferPhoto.offer_id == offer_id)
        .first()
    )

    if not photo:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Foto no encontrada"
        )

    # Quitar marca principal de todas las fotos
    db.query(OfferPhoto).filter(
        OfferPhoto.offer_id == offer_id
    ).update({"is_primary": False})

    # Marcar esta foto como principal
    photo.is_primary = True
    db.commit()
    db.refresh(photo)

    return OfferPhotoResponse.model_validate(photo)


@router.patch("/offers/{offer_id}/photos/reorder", response_model=MessageResponse)
def reorder_photos(
    offer_id: UUID,
    photo_order: List[int],
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Reordenar fotos de una oferta.

    Recibe una lista de IDs de fotos en el orden deseado.
    """
    # Verificar que la oferta exists y pertenece al usuario
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    if offer.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el dueño de la oferta puede reordenar fotos"
        )

    # Actualizar display_order de cada foto
    for index, photo_id in enumerate(photo_order):
        db.query(OfferPhoto).filter(
            OfferPhoto.id == photo_id,
            OfferPhoto.offer_id == offer_id
        ).update({"display_order": index + 1})

    db.commit()

    return MessageResponse(message="Fotos reordenadas exitosamente")


# Importar func para el max_order
from sqlalchemy import func
