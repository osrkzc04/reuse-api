"""
Schemas para autenticación.
"""
from pydantic import BaseModel, EmailStr, Field, field_validator
from typing import Optional
from uuid import UUID


class LoginRequest(BaseModel):
    """Schema para solicitud de login."""

    email: EmailStr
    password: str = Field(..., min_length=1)

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    """Schema de respuesta de tokens JWT."""

    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # segundos

    model_config = {"from_attributes": True}


class RefreshTokenRequest(BaseModel):
    """Schema para solicitud de renovación de token."""

    refresh_token: str

    model_config = {"from_attributes": True}


class TokenPayload(BaseModel):
    """Schema del payload del JWT."""

    sub: str  # user_id
    exp: int  # expiration timestamp
    type: str  # 'access' o 'refresh'

    model_config = {"from_attributes": True}


class RegisterRequest(BaseModel):
    """Schema para registro de nuevo usuario."""

    email: EmailStr
    password: str = Field(..., min_length=8, max_length=100)
    full_name: str = Field(..., min_length=2, max_length=200)
    faculty_id: int
    whatsapp: Optional[str] = Field(None, max_length=20)

    @field_validator('email')
    @classmethod
    def validate_puce_email(cls, v: str) -> str:
        """Validar que el correo sea del dominio PUCE."""
        if not v.lower().endswith('@puce.edu.ec'):
            raise ValueError('Solo se permiten correos institucionales @puce.edu.ec')
        return v.lower()

    @field_validator('password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validar fortaleza de contraseña."""
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.islower() for c in v):
            raise ValueError('La contraseña debe contener al menos una minúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

    @field_validator('whatsapp')
    @classmethod
    def validate_whatsapp(cls, v: Optional[str]) -> Optional[str]:
        """Validar formato de WhatsApp."""
        if v is not None and len(v) > 0:
            # Limpiar caracteres no numéricos excepto +
            cleaned = ''.join(c for c in v if c.isdigit() or c == '+')
            if len(cleaned) < 10:
                raise ValueError('Número de WhatsApp inválido')
            return cleaned
        return v

    model_config = {"from_attributes": True}


class PasswordChangeRequest(BaseModel):
    """Schema para cambio de contraseña."""

    current_password: str
    new_password: str = Field(..., min_length=8)

    @field_validator('new_password')
    @classmethod
    def password_strength(cls, v: str) -> str:
        """Validar fortaleza de contraseña."""
        if not any(c.isupper() for c in v):
            raise ValueError('La contraseña debe contener al menos una mayúscula')
        if not any(c.isdigit() for c in v):
            raise ValueError('La contraseña debe contener al menos un número')
        return v

    model_config = {"from_attributes": True}


class VerifyEmailRequest(BaseModel):
    """Schema para verificación de email."""

    token: str = Field(..., min_length=1)

    model_config = {"from_attributes": True}
