"""
Endpoints de autenticación.
"""
from fastapi import APIRouter, Depends, HTTPException, status, Header
from sqlalchemy.orm import Session

from app.core.deps import get_db, get_current_user_id
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse, RefreshTokenRequest, VerifyEmailRequest
from app.schemas.user import UserResponse
from app.schemas.common import MessageResponse
from app.services import auth_service
from app.services.activity_log_service import log_activity, ActionTypes, EntityTypes
from typing import Optional

router = APIRouter()


@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(
    user_in: RegisterRequest,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Registrar nuevo usuario y enviar correo de verificación.

    Requiere:
    - Email válido y único
    - Contraseña de al menos 8 caracteres con mayúscula y número
    - Nombre completo
    - ID de facultad válido

    Retorna el usuario creado con estado 'pending_verification'.
    Se envía un correo de verificación automáticamente.
    """
    try:
        user = await auth_service.register_user(db, user_in)

        # Registrar actividad
        log_activity(
            db=db,
            action_type=ActionTypes.REGISTER,
            user_id=user.id,
            entity_type=EntityTypes.USER,
            entity_id=user.id,
            extra_data={"email": user.email, "faculty_id": str(user.faculty_id)},
            ip_address=x_forwarded_for,
            user_agent=user_agent
        )

        return user
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/login", response_model=TokenResponse)
def login(
    login_data: LoginRequest,
    user_agent: Optional[str] = Header(None),
    x_forwarded_for: Optional[str] = Header(None),
    db: Session = Depends(get_db)
):
    """
    Autenticar usuario y obtener tokens.

    Requiere:
    - Email
    - Contraseña

    Retorna:
    - access_token: Token de acceso (válido 30 minutos)
    - refresh_token: Token de refresco (válido 7 días)
    """
    from app.models.user import User

    try:
        result = auth_service.login_user(
            db,
            login_data,
            device_info=user_agent,
            ip_address=x_forwarded_for
        )

        # Obtener usuario para el log
        user = db.query(User).filter(User.email == login_data.email.lower()).first()

        # Registrar login exitoso
        if user:
            log_activity(
                db=db,
                action_type=ActionTypes.LOGIN,
                user_id=user.id,
                entity_type=EntityTypes.USER,
                entity_id=user.id,
                extra_data={"email": login_data.email},
                ip_address=x_forwarded_for,
                user_agent=user_agent
            )

        return result
    except Exception as e:
        # Registrar intento fallido (sin user_id porque no sabemos quién es)
        log_activity(
            db=db,
            action_type=ActionTypes.LOGIN_FAILED,
            extra_data={"email": login_data.email, "error": str(e)},
            ip_address=x_forwarded_for,
            user_agent=user_agent
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/refresh", response_model=TokenResponse)
def refresh_token(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Renovar access token usando refresh token.

    Requiere:
    - refresh_token válido y no revocado

    Retorna:
    - Nuevo access_token
    - Mismo refresh_token
    """
    try:
        return auth_service.refresh_access_token(db, refresh_data.refresh_token)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e)
        )


@router.post("/logout", response_model=MessageResponse)
def logout(
    refresh_data: RefreshTokenRequest,
    db: Session = Depends(get_db)
):
    """
    Cerrar sesión revocando refresh token.

    Requiere:
    - refresh_token a revocar
    """
    result = auth_service.logout_user(db, refresh_data.refresh_token)
    return MessageResponse(**result)


@router.post("/verify-email", response_model=MessageResponse)
def verify_email(
    verify_data: VerifyEmailRequest,
    db: Session = Depends(get_db)
):
    """
    Verificar correo electrónico usando token.

    Requiere:
    - token: Token de verificación enviado por correo

    Retorna:
    - Mensaje de confirmación
    """
    try:
        result = auth_service.verify_email_token(db, verify_data.token)
        return MessageResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )


@router.post("/resend-verification", response_model=MessageResponse)
async def resend_verification(
    db: Session = Depends(get_db),
    current_user_id: str = Depends(get_current_user_id)
):
    """
    Reenviar correo de verificación al usuario actual.

    Requiere:
    - Usuario autenticado (token JWT en header Authorization)

    Retorna:
    - Mensaje de confirmación
    """
    try:
        result = await auth_service.resend_verification_email(db, current_user_id)
        return MessageResponse(**result)
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e)
        )
