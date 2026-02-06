"""
Schemas para el servicio de Email.
"""
from pydantic import BaseModel, EmailStr, Field
from typing import Optional, List
from enum import Enum


class EmailType(str, Enum):
    """Tipos de correo disponibles."""
    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"
    EXCHANGE_NOTIFICATION = "exchange_notification"
    NEWSLETTER = "newsletter"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


class EmailBase(BaseModel):
    """Schema base para emails."""
    subject: str = Field(..., min_length=1, max_length=200, description="Asunto del correo")


class SendEmailRequest(EmailBase):
    """Request para enviar un correo personalizado."""
    to_email: EmailStr = Field(..., description="Email de destino")
    html_content: str = Field(..., min_length=1, description="Contenido HTML del correo")
    text_content: Optional[str] = Field(None, description="Contenido de texto plano (fallback)")
    cc: Optional[List[EmailStr]] = Field(None, description="Emails en copia")
    bcc: Optional[List[EmailStr]] = Field(None, description="Emails en copia oculta")

    model_config = {
        "json_schema_extra": {
            "example": {
                "to_email": "usuario@puce.edu.ec",
                "subject": "Asunto del correo",
                "html_content": "<h1>Hola</h1><p>Este es un correo de prueba</p>",
                "text_content": "Hola, este es un correo de prueba"
            }
        }
    }


class SendNewsletterRequest(EmailBase):
    """Request para enviar un newsletter."""
    to_emails: List[EmailStr] = Field(..., min_items=1, max_items=100, description="Lista de emails (máximo 100)")
    title: str = Field(..., min_length=1, max_length=200, description="Título del newsletter")
    content: str = Field(..., min_length=1, description="Contenido HTML del newsletter")
    cta_text: Optional[str] = Field(None, max_length=50, description="Texto del botón de acción")
    cta_url: Optional[str] = Field(None, description="URL del botón de acción")

    model_config = {
        "json_schema_extra": {
            "example": {
                "to_emails": ["usuario1@puce.edu.ec", "usuario2@puce.edu.ec"],
                "subject": "Newsletter Reuse - Enero 2025",
                "title": "Novedades de Enero",
                "content": "<p>Estas son las novedades del mes...</p>",
                "cta_text": "Ver más",
                "cta_url": "https://reuse.puce.edu.ec/noticias"
            }
        }
    }


class SendNotificationRequest(BaseModel):
    """Request para enviar una notificación por email."""
    to_email: EmailStr = Field(..., description="Email de destino")
    user_name: str = Field(..., min_length=1, max_length=100, description="Nombre del usuario")
    title: str = Field(..., min_length=1, max_length=200, description="Título de la notificación")
    message: str = Field(..., min_length=1, description="Mensaje de la notificación")
    action_text: Optional[str] = Field(None, max_length=50, description="Texto del botón de acción")
    action_url: Optional[str] = Field(None, description="URL del botón de acción")

    model_config = {
        "json_schema_extra": {
            "example": {
                "to_email": "usuario@puce.edu.ec",
                "user_name": "Juan Pérez",
                "title": "Nuevo mensaje",
                "message": "Tienes un nuevo mensaje en Reuse",
                "action_text": "Ver mensaje",
                "action_url": "https://reuse.puce.edu.ec/mensajes"
            }
        }
    }


class EmailResponse(BaseModel):
    """Response para envío de email."""
    success: bool = Field(..., description="Si el correo se envió correctamente")
    message: str = Field(..., description="Mensaje descriptivo")
    email_type: EmailType = Field(..., description="Tipo de correo enviado")

    model_config = {
        "json_schema_extra": {
            "example": {
                "success": True,
                "message": "Correo enviado exitosamente",
                "email_type": "custom"
            }
        }
    }


class NewsletterResponse(BaseModel):
    """Response para envío de newsletter."""
    total: int = Field(..., description="Total de emails procesados")
    sent: int = Field(..., description="Emails enviados exitosamente")
    failed: int = Field(..., description="Emails fallidos")
    results: dict = Field(..., description="Detalle por email")

    model_config = {
        "json_schema_extra": {
            "example": {
                "total": 2,
                "sent": 2,
                "failed": 0,
                "results": {
                    "usuario1@puce.edu.ec": True,
                    "usuario2@puce.edu.ec": True
                }
            }
        }
    }


class EmailConfigStatus(BaseModel):
    """Estado de la configuración de email."""
    enabled: bool = Field(..., description="Si el servicio está habilitado")
    configured: bool = Field(..., description="Si SMTP está configurado")
    smtp_host: str = Field(..., description="Host SMTP")
    smtp_port: int = Field(..., description="Puerto SMTP")
    from_email: str = Field(..., description="Email remitente")

    model_config = {
        "json_schema_extra": {
            "example": {
                "enabled": True,
                "configured": True,
                "smtp_host": "smtp.gmail.com",
                "smtp_port": 587,
                "from_email": "noreply@reuse.puce.edu.ec"
            }
        }
    }
