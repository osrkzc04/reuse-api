"""
Utilidades de seguridad: JWT, hashing de contraseñas, etc.
"""
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from jose import JWTError, jwt
from passlib.context import CryptContext
from app.config import settings

# Configurar contexto de hash de contraseñas
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """
    Verificar que una contraseña en texto plano coincida con su hash.

    Args:
        plain_password: Contraseña en texto plano
        hashed_password: Hash de la contraseña

    Returns:
        True si coinciden, False en caso contrario
    """
    return pwd_context.verify(plain_password, hashed_password)


def get_password_hash(password: str) -> str:
    """
    Generar hash de una contraseña.

    Args:
        password: Contraseña en texto plano

    Returns:
        Hash de la contraseña
    """
    return pwd_context.hash(password)


def create_access_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Crear un JWT access token.

    Args:
        data: Datos a codificar en el token
        expires_delta: Tiempo de expiración personalizado

    Returns:
        Token JWT codificado
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode.update({"exp": expire, "type": "access"})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def create_refresh_token(data: Dict[str, Any], expires_delta: Optional[timedelta] = None) -> str:
    """
    Crear un JWT refresh token.

    Args:
        data: Datos a codificar en el token
        expires_delta: Tiempo de expiración personalizado

    Returns:
        Token JWT de refresco
    """
    to_encode = data.copy()

    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(days=settings.REFRESH_TOKEN_EXPIRE_DAYS)

    to_encode.update({"exp": expire, "type": "refresh"})

    encoded_jwt = jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)
    return encoded_jwt


def decode_token(token: str) -> Dict[str, Any]:
    """
    Decodificar y validar un JWT.

    Args:
        token: Token JWT a decodificar

    Returns:
        Payload del token decodificado

    Raises:
        JWTError: Si el token es inválido o ha expirado
    """
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except JWTError as e:
        raise JWTError(f"Token inválido: {str(e)}")
