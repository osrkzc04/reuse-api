"""
Servicio de autenticación.
Maneja registro, login, refresh de tokens.
"""
from datetime import datetime, timedelta
from typing import Dict
from sqlalchemy.orm import Session
from fastapi import HTTPException, status

from app.core.security import create_access_token, create_refresh_token, verify_password
from app.core.exceptions import UnauthorizedException, BadRequestException
from app.crud.user import user as crud_user
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.user_preferences import UserPreferences
from app.schemas.auth import RegisterRequest, LoginRequest, TokenResponse
from app.config import settings


async def register_user(db: Session, user_in: RegisterRequest) -> User:
    """
    Registrar nuevo usuario y enviar correo de verificación.

    Args:
        db: Sesión de base de datos
        user_in: Datos de registro

    Returns:
        Usuario creado

    Raises:
        BadRequestException: Si el email ya está registrado
    """
    # Verificar si el email ya existe
    existing_user = crud_user.get_by_email(db, email=user_in.email)
    if existing_user:
        raise BadRequestException("El email ya está registrado")

    # Crear usuario
    from app.schemas.user import UserCreate
    user_create = UserCreate(**user_in.model_dump())
    user = crud_user.create(db, obj_in=user_create)

    # Dejar usuario en estado pending_verification (NO activar automáticamente)
    user.status = "pending_verification"
    user.is_email_verified = False
    db.commit()
    db.refresh(user)

    # Crear preferencias por defecto
    user_prefs = UserPreferences(user_id=user.id)
    db.add(user_prefs)
    db.commit()

    # Enviar correo de verificación
    await send_verification_email_to_user(db, user)

    return user


def login_user(db: Session, login_data: LoginRequest, device_info: str = None, ip_address: str = None) -> TokenResponse:
    """
    Autenticar usuario y generar tokens.

    Args:
        db: Sesión de base de datos
        login_data: Credenciales de login
        device_info: Información del dispositivo
        ip_address: Dirección IP

    Returns:
        Tokens de acceso y refresco

    Raises:
        UnauthorizedException: Si las credenciales son inválidas
    """
    # Autenticar usuario
    user = crud_user.authenticate(
        db, email=login_data.email, password=login_data.password
    )

    if not user:
        raise UnauthorizedException("Email o contraseña incorrectos")

    # Permitir login para usuarios pending_verification
    # El frontend manejará la redirección a la página de verificación
    if user.status == "suspended":
        raise UnauthorizedException("Tu cuenta ha sido suspendida temporalmente")
    elif user.status == "banned":
        raise UnauthorizedException("Tu cuenta ha sido bloqueada permanentemente")

    # Actualizar último login
    user.last_login = datetime.utcnow()
    db.commit()

    # Generar tokens
    access_token = create_access_token(data={"sub": str(user.id)})
    refresh_token_str = create_refresh_token(data={"sub": str(user.id)})

    # Guardar refresh token en BD
    expires_at = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)
    refresh_token = RefreshToken(
        user_id=user.id,
        token=refresh_token_str,
        expires_at=expires_at,
        device_info=device_info,
        ip_address=ip_address
    )
    db.add(refresh_token)
    db.commit()

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


def refresh_access_token(db: Session, refresh_token_str: str) -> TokenResponse:
    """
    Renovar access token usando refresh token.

    Args:
        db: Sesión de base de datos
        refresh_token_str: Refresh token

    Returns:
        Nuevo access token

    Raises:
        UnauthorizedException: Si el refresh token es inválido
    """
    from app.core.security import decode_token
    from jose import JWTError

    # Validar refresh token
    try:
        payload = decode_token(refresh_token_str)
        if payload.get("type") != "refresh":
            raise UnauthorizedException("Token inválido")
    except JWTError:
        raise UnauthorizedException("Token inválido o expirado")

    # Verificar en base de datos
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token_str,
        RefreshToken.is_revoked == False
    ).first()

    if not db_token or not db_token.is_valid():
        raise UnauthorizedException("Token inválido o revocado")

    # Generar nuevo access token
    user_id = payload.get("sub")
    access_token = create_access_token(data={"sub": user_id})

    return TokenResponse(
        access_token=access_token,
        refresh_token=refresh_token_str,  # Mismo refresh token
        expires_in=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60
    )


def logout_user(db: Session, refresh_token_str: str) -> Dict[str, str]:
    """
    Cerrar sesión revocando refresh token.

    Args:
        db: Sesión de base de datos
        refresh_token_str: Refresh token a revocar

    Returns:
        Mensaje de confirmación
    """
    db_token = db.query(RefreshToken).filter(
        RefreshToken.token == refresh_token_str
    ).first()

    if db_token:
        db_token.is_revoked = True
        db_token.revoked_at = datetime.utcnow()
        db.commit()

    return {"message": "Sesión cerrada exitosamente"}


def generate_verification_token(db: Session, user_id: str) -> str:
    """
    Generar token de verificación de email.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario

    Returns:
        Token de verificación
    """
    import secrets
    from datetime import timezone
    from app.models.email_verification_token import EmailVerificationToken

    # Generar token único
    token = secrets.token_urlsafe(32)

    # Expiración en 24 horas (timezone-aware)
    expires_at = datetime.now(timezone.utc) + timedelta(hours=24)

    # Crear token en BD
    verification_token = EmailVerificationToken(
        user_id=user_id,
        token=token,
        expires_at=expires_at
    )
    db.add(verification_token)
    db.commit()

    return token


async def send_verification_email_to_user(db: Session, user: User) -> None:
    """
    Enviar correo de verificación a un usuario.

    Args:
        db: Sesión de base de datos
        user: Usuario al que enviar el correo
    """
    from app.services.email_service import EmailService

    # Generar token
    token = generate_verification_token(db, str(user.id))

    # Enviar correo
    email_service = EmailService()
    await email_service.send_verification_email(
        to_email=user.email,
        user_name=user.full_name,
        verification_token=token
    )


def verify_email_token(db: Session, token: str) -> Dict[str, str]:
    """
    Verificar token de email y marcar usuario como verificado.

    Args:
        db: Sesión de base de datos
        token: Token de verificación

    Returns:
        Mensaje de confirmación

    Raises:
        BadRequestException: Si el token es inválido o expirado
    """
    from datetime import timezone
    from app.models.email_verification_token import EmailVerificationToken

    # Buscar token en BD
    db_token = db.query(EmailVerificationToken).filter(
        EmailVerificationToken.token == token
    ).first()

    if not db_token:
        raise BadRequestException("Token de verificación inválido")

    # Verificar si ya fue usado
    if db_token.is_used:
        # Verificar si el usuario ya está verificado
        user = db.query(User).filter(User.id == db_token.user_id).first()
        if user and user.is_email_verified:
            return {"message": "Tu correo ya está verificado. Puedes iniciar sesión."}
        raise BadRequestException("Este token ya fue usado")

    # Verificar si expiró
    now = datetime.now(timezone.utc)
    expires = db_token.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=timezone.utc)

    if expires <= now:
        raise BadRequestException("El token ha expirado. Por favor solicita uno nuevo.")

    # Marcar token como usado
    db_token.is_used = True
    db_token.used_at = datetime.now(timezone.utc)

    # Marcar usuario como verificado
    user = db.query(User).filter(User.id == db_token.user_id).first()
    if user:
        user.is_email_verified = True
        user.status = "active"

    db.commit()

    return {"message": "Correo verificado exitosamente"}


async def resend_verification_email(db: Session, user_id: str) -> Dict[str, str]:
    """
    Reenviar correo de verificación a un usuario.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario

    Returns:
        Mensaje de confirmación

    Raises:
        BadRequestException: Si el usuario no existe o ya está verificado
    """
    user = db.query(User).filter(User.id == user_id).first()

    if not user:
        raise BadRequestException("Usuario no encontrado")

    if user.is_email_verified:
        raise BadRequestException("El correo ya está verificado")

    # Enviar correo
    await send_verification_email_to_user(db, user)

    return {"message": "Correo de verificación reenviado"}
