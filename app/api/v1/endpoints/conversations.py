"""
Endpoints de conversaciones (chat).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, and_, desc
from uuid import UUID
from typing import List

from app.core.deps import get_db, get_current_active_user
from app.crud.conversation import conversation as crud_conversation
from app.schemas.conversation import ConversationResponse
from app.schemas.common import MessageResponse
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.models.offer import Offer
from app.models.offer_photo import OfferPhoto

router = APIRouter()


@router.get("", response_model=List[ConversationResponse])
def get_my_conversations(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener conversaciones del usuario actual.

    Requiere autenticacion.
    Retorna las 30 conversaciones mas recientes donde el usuario participa.
    """
    # Obtener conversaciones donde el usuario es participante
    conversations = (
        db.query(Conversation)
        .filter(
            or_(
                Conversation.user1_id == current_user.id,
                Conversation.user2_id == current_user.id
            ),
            Conversation.is_active == True
        )
        .order_by(desc(Conversation.updated_at))
        .limit(30)
        .all()
    )

    # Enriquecer respuesta con informacion adicional
    enriched_conversations = []
    for conv in conversations:
        # Determinar el otro usuario
        other_user_id = conv.user2_id if conv.user1_id == current_user.id else conv.user1_id
        other_user = db.query(User).filter(User.id == other_user_id).first()

        # Obtener info de la oferta
        offer = db.query(Offer).filter(Offer.id == conv.offer_id).first()
        offer_photo = (
            db.query(OfferPhoto)
            .filter(OfferPhoto.offer_id == conv.offer_id, OfferPhoto.is_primary == True)
            .first()
        )

        # Obtener ultimo mensaje
        last_msg = (
            db.query(Message)
            .filter(Message.conversation_id == conv.id)
            .order_by(desc(Message.created_at))
            .first()
        )

        # Contar mensajes no leidos
        unread_count = (
            db.query(Message)
            .filter(
                Message.conversation_id == conv.id,
                Message.from_user_id != current_user.id,
                Message.is_read == False
            )
            .count()
        )

        # Construir respuesta
        conv_response = ConversationResponse.model_validate(conv)
        conv_response.other_user_id = other_user_id
        conv_response.other_user_name = other_user.full_name if other_user else None
        conv_response.other_user_photo = other_user.profile_photo_url if other_user else None
        conv_response.offer_title = offer.title if offer else None
        conv_response.offer_photo = offer_photo.photo_url if offer_photo else None
        conv_response.last_message = last_msg.content if last_msg else None
        conv_response.last_message_at = last_msg.created_at if last_msg else None
        conv_response.unread_count = unread_count

        enriched_conversations.append(conv_response)

    return enriched_conversations


@router.get("/{conversation_id}", response_model=ConversationResponse)
def get_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener detalle de una conversación específica.

    El usuario debe ser participante de la conversación.
    """
    conversation = crud_conversation.get(db, id=conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada"
        )

    # Verificar que el usuario es participante
    if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta conversación"
        )

    # Determinar el otro usuario
    other_user_id = conversation.user2_id if conversation.user1_id == current_user.id else conversation.user1_id
    other_user = db.query(User).filter(User.id == other_user_id).first()

    # Obtener info de la oferta
    offer = db.query(Offer).filter(Offer.id == conversation.offer_id).first()
    offer_photo = (
        db.query(OfferPhoto)
        .filter(OfferPhoto.offer_id == conversation.offer_id, OfferPhoto.is_primary == True)
        .first()
    )

    # Construir respuesta
    response = ConversationResponse.model_validate(conversation)
    response.other_user_id = other_user_id
    response.other_user_name = other_user.full_name if other_user else None
    response.other_user_photo = other_user.profile_photo_url if other_user else None
    response.offer_title = offer.title if offer else None
    response.offer_photo = offer_photo.photo_url if offer_photo else None

    return response


@router.post("/start/{offer_id}", response_model=ConversationResponse, status_code=status.HTTP_201_CREATED)
def start_conversation(
    offer_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Iniciar una conversación sobre una oferta.

    Si ya existe una conversación activa entre el usuario y el dueño
    de la oferta, retorna la existente.
    """
    # Obtener la oferta
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    # Verificar que el usuario no sea el dueño de la oferta
    if offer.user_id == current_user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No puedes iniciar una conversación con tu propia oferta"
        )

    # Verificar si ya existe una conversación
    existing_conv = (
        db.query(Conversation)
        .filter(
            Conversation.offer_id == offer_id,
            or_(
                and_(
                    Conversation.user1_id == current_user.id,
                    Conversation.user2_id == offer.user_id
                ),
                and_(
                    Conversation.user1_id == offer.user_id,
                    Conversation.user2_id == current_user.id
                )
            ),
            Conversation.is_active == True
        )
        .first()
    )

    if existing_conv:
        response = ConversationResponse.model_validate(existing_conv)
        response.other_user_id = offer.user_id
        return response

    # Crear nueva conversación
    new_conversation = Conversation(
        offer_id=offer_id,
        user1_id=current_user.id,
        user2_id=offer.user_id
    )
    db.add(new_conversation)
    db.commit()
    db.refresh(new_conversation)

    response = ConversationResponse.model_validate(new_conversation)
    response.other_user_id = offer.user_id
    return response


@router.delete("/{conversation_id}", response_model=MessageResponse)
def delete_conversation(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Desactivar una conversación.

    El usuario debe ser participante de la conversación.
    """
    conversation = crud_conversation.get(db, id=conversation_id)

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada"
        )

    # Verificar que el usuario es participante
    if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta conversación"
        )

    # Desactivar conversación
    conversation.is_active = False
    db.commit()

    return MessageResponse(message="Conversación eliminada exitosamente")
