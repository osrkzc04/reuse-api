"""
Endpoints de mensajes (chat).
"""
from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from sqlalchemy import or_, desc
from uuid import UUID
from datetime import datetime
from typing import List

from app.core.deps import get_db, get_current_active_user
from app.crud.message import message as crud_message
from app.schemas.message import MessageCreate, MessageResponse
from app.schemas.common import MessageResponse as APIMessageResponse
from app.models.user import User
from app.models.conversation import Conversation
from app.models.message import Message
from app.services.notification_service import notify_new_message

router = APIRouter()


@router.get("/conversation/{conversation_id}", response_model=List[MessageResponse])
def get_conversation_messages(
    conversation_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener mensajes de una conversacion.

    Requiere autenticacion.
    Retorna los 100 mensajes mas recientes de la conversacion.
    """
    # Verificar que la conversacion existe
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversacion no encontrada"
        )

    # Verificar que el usuario es participante
    if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta conversacion"
        )

    # Obtener mensajes
    messages = (
        db.query(Message)
        .filter(Message.conversation_id == conversation_id)
        .order_by(desc(Message.created_at))
        .limit(100)
        .all()
    )

    # Enriquecer respuesta con informacion del usuario
    enriched_messages = []
    for msg in messages:
        sender = db.query(User).filter(User.id == msg.from_user_id).first()

        msg_response = MessageResponse.model_validate(msg)
        msg_response.from_user_name = sender.full_name if sender else None
        msg_response.from_user_photo = sender.profile_photo_url if sender else None

        enriched_messages.append(msg_response)

    # Marcar como leidos los mensajes recibidos por el usuario actual
    db.query(Message).filter(
        Message.conversation_id == conversation_id,
        Message.from_user_id != current_user.id,
        Message.is_read == False
    ).update({"is_read": True, "read_at": datetime.utcnow()})
    db.commit()

    return enriched_messages


@router.post("/conversation/{conversation_id}", response_model=MessageResponse, status_code=status.HTTP_201_CREATED)
def send_message(
    conversation_id: UUID,
    message_in: MessageCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Enviar un mensaje en una conversación.

    El usuario debe ser participante de la conversación.
    """
    # Verificar que la conversación existe y está activa
    conversation = db.query(Conversation).filter(
        Conversation.id == conversation_id,
        Conversation.is_active == True
    ).first()

    if not conversation:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Conversación no encontrada o inactiva"
        )

    # Verificar que el usuario es participante
    if conversation.user1_id != current_user.id and conversation.user2_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes acceso a esta conversación"
        )

    # Determinar el receptor
    receiver_id = conversation.user2_id if conversation.user1_id == current_user.id else conversation.user1_id

    # Crear mensaje
    new_message = Message(
        conversation_id=conversation_id,
        from_user_id=current_user.id,
        content=message_in.content
    )
    db.add(new_message)

    # Actualizar timestamp de la conversación
    conversation.updated_at = datetime.utcnow()
    db.commit()
    db.refresh(new_message)

    # Notificar al receptor del mensaje
    notify_new_message(
        db=db,
        recipient_id=receiver_id,
        sender_name=current_user.full_name,
        conversation_id=conversation_id
    )

    # Construir respuesta
    response = MessageResponse.model_validate(new_message)
    response.from_user_name = current_user.full_name
    response.from_user_photo = current_user.profile_photo_url

    return response


@router.patch("/{message_id}/read", response_model=APIMessageResponse)
def mark_message_as_read(
    message_id: UUID,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Marcar un mensaje como leído.

    El usuario debe ser el receptor del mensaje.
    """
    message = db.query(Message).filter(Message.id == message_id).first()

    if not message:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Mensaje no encontrado"
        )

    # Verificar que el usuario es el receptor (no es el remitente)
    # y que es parte de la conversación
    conversation = db.query(Conversation).filter(Conversation.id == message.conversation_id).first()
    is_participant = conversation and (conversation.user1_id == current_user.id or conversation.user2_id == current_user.id)
    is_receiver = message.from_user_id != current_user.id

    if not is_participant or not is_receiver:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tienes permiso para marcar este mensaje como leído"
        )

    # Marcar como leído
    if not message.is_read:
        message.is_read = True
        message.read_at = datetime.utcnow()
        db.commit()

    return APIMessageResponse(message="Mensaje marcado como leído")


@router.get("/unread/count")
def get_unread_count(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Obtener cantidad total de mensajes no leídos del usuario.

    Útil para badges/notificaciones en la UI.
    """
    # Contar mensajes donde el usuario es participante de la conversación
    # y NO es el remitente del mensaje (es decir, es el receptor)
    unread_count = (
        db.query(Message)
        .join(Conversation, Message.conversation_id == Conversation.id)
        .filter(
            or_(
                Conversation.user1_id == current_user.id,
                Conversation.user2_id == current_user.id
            ),
            Message.from_user_id != current_user.id,
            Message.is_read == False
        )
        .count()
    )

    return {"unread_count": unread_count}
