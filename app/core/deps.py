"""
Dependencias comunes de FastAPI.
"""
from typing import Generator, Optional
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session
from jose import JWTError

from app.db.session import SessionLocal
from app.core.security import decode_token
from app.core.exceptions import UnauthorizedException

security = HTTPBearer()


def get_db() -> Generator:
    """
    Dependencia que proporciona una sesión de base de datos.

    Yields:
        Session: Sesión de SQLAlchemy
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


async def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(security)
) -> str:
    """
    Obtener el ID del usuario actual desde el JWT.

    Args:
        credentials: Credenciales HTTP Bearer

    Returns:
        ID del usuario

    Raises:
        HTTPException: Si el token es inválido
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="No se pudieron validar las credenciales",
        headers={"WWW-Authenticate": "Bearer"},
    )

    try:
        token = credentials.credentials
        payload = decode_token(token)

        user_id: Optional[str] = payload.get("sub")
        token_type: Optional[str] = payload.get("type")

        if user_id is None or token_type != "access":
            raise credentials_exception

        return user_id

    except JWTError:
        raise credentials_exception


async def get_current_user(
    db: Session = Depends(get_db),
    user_id: str = Depends(get_current_user_id)
):
    """
    Obtener el usuario actual completo desde la base de datos.

    Args:
        db: Sesión de base de datos
        user_id: ID del usuario desde el token

    Returns:
        Usuario actual

    Raises:
        HTTPException: Si el usuario no existe
    """
    # Importar aquí para evitar importación circular
    from app.models.user import User

    user = db.query(User).filter(User.id == user_id).first()

    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Usuario no encontrado"
        )

    return user


async def get_current_user_allow_unverified(
    current_user = Depends(get_current_user)
):
    """
    Obtener usuario actual permitiendo usuarios no verificados.

    Permite usuarios con status 'active' o 'pending_verification'.
    Útil para endpoints como /me donde el frontend necesita
    saber el estado de verificación del usuario.

    Args:
        current_user: Usuario actual

    Returns:
        Usuario (verificado o no)

    Raises:
        HTTPException: Si el usuario está suspendido o baneado
    """
    if current_user.status in ["suspended", "banned"]:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario suspendido o baneado"
        )

    return current_user


async def get_current_active_user(
    current_user = Depends(get_current_user)
):
    """
    Verificar que el usuario actual esté activo.

    Args:
        current_user: Usuario actual

    Returns:
        Usuario activo

    Raises:
        HTTPException: Si el usuario no está activo
    """
    if current_user.status != "active":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Usuario inactivo"
        )

    return current_user


async def get_current_admin_user(
    current_user = Depends(get_current_active_user)
):
    """
    Verificar que el usuario actual sea administrador o moderador.

    Args:
        current_user: Usuario actual

    Returns:
        Usuario administrador o moderador

    Raises:
        HTTPException: Si el usuario no es administrador ni moderador
    """
    if current_user.role not in ["administrador", "moderador"]:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="No tiene permisos de administrador"
        )

    return current_user


async def get_current_superadmin_user(
    current_user = Depends(get_current_active_user)
):
    """
    Verificar que el usuario actual sea SOLO administrador (sin moderadores).
    Usado para operaciones sensibles como envío de emails masivos.

    Args:
        current_user: Usuario actual

    Returns:
        Usuario administrador

    Raises:
        HTTPException: Si el usuario no es administrador
    """
    if current_user.role != "administrador":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo administradores pueden realizar esta accion"
        )

    return current_user
