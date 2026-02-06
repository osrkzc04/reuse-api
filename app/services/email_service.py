"""
Servicio de Email para Reuse.
Maneja el envío de correos electrónicos de forma reutilizable.

Uso interno (recomendado):
    from app.services.email_service import email_service

    await email_service.send_verification_email(
        to_email="user@example.com",
        user_name="Juan",
        verification_token="abc123"
    )

Tipos de correos soportados:
    - Verificación de cuenta
    - Recuperación de contraseña
    - Notificaciones de intercambio
    - Newsletter/Anuncios
    - Correo personalizado con HTML
"""
import logging
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.utils import formatdate, make_msgid
from typing import Optional, List, Dict, Any
from pathlib import Path
from enum import Enum

import aiosmtplib
from jinja2 import Environment, FileSystemLoader, select_autoescape

from app.config import settings

# Configurar logger
logger = logging.getLogger(__name__)


class EmailType(str, Enum):
    """Tipos de correo disponibles."""
    VERIFICATION = "verification"
    PASSWORD_RESET = "password_reset"
    EXCHANGE_NOTIFICATION = "exchange_notification"
    EXCHANGE_COMPLETED = "exchange_completed"
    NEWSLETTER = "newsletter"
    NOTIFICATION = "notification"
    CUSTOM = "custom"


class EmailService:
    """
    Servicio para envío de correos electrónicos.
    Implementado como Singleton para reutilización.
    """

    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self.smtp_host = settings.SMTP_HOST
        self.smtp_port = settings.SMTP_PORT
        self.smtp_user = settings.SMTP_USER
        self.smtp_password = settings.SMTP_PASSWORD
        self.from_email = settings.SMTP_FROM_EMAIL or settings.SMTP_USER
        self.from_name = settings.SMTP_FROM_NAME
        self.use_tls = settings.SMTP_USE_TLS
        self.enabled = settings.SMTP_ENABLED

        # Configurar Jinja2 para plantillas
        templates_path = Path(__file__).parent.parent / "templates" / "emails"
        templates_path.mkdir(parents=True, exist_ok=True)

        self.jinja_env = Environment(
            loader=FileSystemLoader(str(templates_path)),
            autoescape=select_autoescape(['html', 'xml']),
            enable_async=True
        )

        logger.info(f"EmailService inicializado. SMTP: {self.smtp_host}:{self.smtp_port}, Enabled: {self.enabled}")

    def is_configured(self) -> bool:
        """Verifica si el servicio está correctamente configurado."""
        return bool(
            self.enabled and
            self.smtp_host and
            self.smtp_user and
            self.smtp_password
        )

    async def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Envía un correo electrónico.

        Args:
            to_email: Dirección de destino
            subject: Asunto del correo
            html_content: Contenido HTML del correo
            text_content: Contenido de texto plano (fallback)
            cc: Lista de direcciones en copia
            bcc: Lista de direcciones en copia oculta

        Returns:
            bool: True si se envió correctamente, False en caso contrario
        """
        if not self.is_configured():
            logger.warning(f"Email no enviado a {to_email}: SMTP no configurado o deshabilitado")
            return False

        try:
            # Crear mensaje multipart
            message = MIMEMultipart("alternative")
            message["From"] = f"{self.from_name} <{self.from_email}>"
            message["To"] = to_email
            message["Subject"] = subject
            message["Date"] = formatdate(localtime=True)
            message["Message-ID"] = make_msgid()

            if cc:
                message["Cc"] = ", ".join(cc)

            # Agregar contenido de texto plano (fallback)
            if not text_content:
                # fallback simple (puedes mejorar: strip de tags)
                text_content = "Este correo contiene contenido HTML. Si no lo ves, abre desde un cliente compatible."

            if text_content:
                part_text = MIMEText(text_content, "plain", "utf-8")
                message.attach(part_text)

            # Agregar contenido HTML
            part_html = MIMEText(html_content, "html", "utf-8")
            message.attach(part_html)

            # Determinar todos los destinatarios
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)

            # Enviar correo
            # Puerto 465 usa SSL directo (use_tls), puerto 587 usa STARTTLS (start_tls)
            if self.smtp_port == 465:
                await aiosmtplib.send(
                    message,
                    sender=self.smtp_user,
                    recipients=recipients,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_user,
                    password=self.smtp_password,
                    use_tls=True
                )
            else:
                await aiosmtplib.send(
                    message,
                    sender=self.smtp_user,
                    recipients=recipients,
                    hostname=self.smtp_host,
                    port=self.smtp_port,
                    username=self.smtp_user,
                    password=self.smtp_password,
                    start_tls=True
                )

            logger.info(f"Email enviado exitosamente a {to_email}: {subject}")
            return True

        except aiosmtplib.SMTPException as e:
            logger.error(f"Error SMTP enviando email a {to_email}: {str(e)}")
            return False
        except Exception as e:
            logger.error(f"Error inesperado enviando email a {to_email}: {str(e)}")
            return False

    async def _render_template(
        self,
        template_name: str,
        context: Dict[str, Any]
    ) -> str:
        """
        Renderiza una plantilla HTML con el contexto dado.

        Args:
            template_name: Nombre del archivo de plantilla
            context: Variables para la plantilla

        Returns:
            str: HTML renderizado
        """
        try:
            template = self.jinja_env.get_template(template_name)
            return await template.render_async(**context)
        except Exception as e:
            logger.error(f"Error renderizando plantilla {template_name}: {str(e)}")
            # Fallback a plantilla básica
            return self._get_fallback_template(context)

    def _get_fallback_template(self, context: Dict[str, Any]) -> str:
        """Genera una plantilla HTML básica de fallback."""
        title = context.get("title", "Notificación")
        message = context.get("message", "")

        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>{title}</title>
        </head>
        <body style="font-family: Arial, sans-serif; padding: 20px;">
            <h1 style="color: #2E7D32;">{title}</h1>
            <div>{message}</div>
            <hr>
            <p style="color: #666; font-size: 12px;">
                Este correo fue enviado por Reuse - Sistema de Intercambio Sostenible PUCE
            </p>
        </body>
        </html>
        """

    # ==========================================
    # MÉTODOS ESPECÍFICOS PARA CADA TIPO DE EMAIL
    # ==========================================

    async def send_verification_email(
        self,
        to_email: str,
        user_name: str,
        verification_token: str,
        verification_url: Optional[str] = None
    ) -> bool:
        """
        Envía correo de verificación de cuenta.

        Args:
            to_email: Email del usuario
            user_name: Nombre del usuario
            verification_token: Token de verificación
            verification_url: URL completa de verificación (opcional)
        """
        context = {
            "title": "Verifica tu cuenta en Reuse",
            "user_name": user_name,
            "to_email": to_email,
            "verification_url": verification_url or f"{settings.FRONTEND_URL}/verify-email?token={verification_token}",
            "app_name": settings.APP_NAME,
            "email_type": EmailType.VERIFICATION.value
        }

        html_content = await self._render_template("verification.html", context)
        text_content = f"""
        Hola {user_name},

        Bienvenido/a a Reuse, la sistema de intercambio sostenible de la PUCE.

        Para verificar tu cuenta, visita el siguiente enlace:
        {context['verification_url']}

        Este enlace expirará en 24 horas.

        Si no solicitaste esta cuenta, ignora este correo.

        Saludos,
        El equipo de Reuse PUCE
        """

        return await self._send_email(
            to_email=to_email,
            subject="Verifica tu cuenta en Reuse",
            html_content=html_content,
            text_content=text_content
        )

    async def send_password_reset_email(
        self,
        to_email: str,
        user_name: str,
        reset_token: str,
        reset_url: Optional[str] = None
    ) -> bool:
        """
        Envía correo de recuperación de contraseña.

        Args:
            to_email: Email del usuario
            user_name: Nombre del usuario
            reset_token: Token de recuperación
            reset_url: URL de recuperación (opcional)
        """
        context = {
            "title": "Recupera tu contraseña",
            "user_name": user_name,
            "reset_token": reset_token,
            "reset_url": reset_url or f"{settings.FRONTEND_URL}/reset-password?token={reset_token}",
            "app_name": settings.APP_NAME,
            "email_type": EmailType.PASSWORD_RESET.value
        }

        html_content = await self._render_template("password_reset.html", context)
        text_content = f"""
        Hola {user_name},

        Recibimos una solicitud para restablecer tu contraseña en Reuse.

        Tu código de recuperación es: {reset_token}

        O visita: {context['reset_url']}

        Este código expira en 1 hora. Si no solicitaste este cambio, ignora este correo.

        Saludos,
        El equipo de Reuse PUCE
        """

        return await self._send_email(
            to_email=to_email,
            subject="Recupera tu contraseña - Reuse",
            html_content=html_content,
            text_content=text_content
        )

    async def send_exchange_notification(
        self,
        to_email: str,
        user_name: str,
        other_user_name: str,
        offer_title: str,
        exchange_status: str,
        exchange_url: Optional[str] = None
    ) -> bool:
        """
        Envía notificación de intercambio.

        Args:
            to_email: Email del usuario
            user_name: Nombre del usuario
            other_user_name: Nombre del otro usuario
            offer_title: Título de la oferta
            exchange_status: Estado del intercambio
            exchange_url: URL del intercambio (opcional)
        """
        status_messages = {
            "pending": f"{other_user_name} está interesado en tu oferta",
            "accepted": f"Tu solicitud de intercambio fue aceptada",
            "in_progress": "El intercambio está en progreso",
            "completed": "¡Intercambio completado con éxito!",
            "cancelled": "El intercambio fue cancelado"
        }

        context = {
            "title": "Actualización de Intercambio",
            "user_name": user_name,
            "other_user_name": other_user_name,
            "offer_title": offer_title,
            "exchange_status": exchange_status,
            "status_message": status_messages.get(exchange_status, "Actualización de intercambio"),
            "exchange_url": exchange_url,
            "app_name": settings.APP_NAME,
            "email_type": EmailType.EXCHANGE_NOTIFICATION.value
        }

        html_content = await self._render_template("exchange_notification.html", context)
        text_content = f"""
        Hola {user_name},

        {context['status_message']}

        Oferta: {offer_title}
        Estado: {exchange_status}

        Visita Reuse para más detalles.

        Saludos,
        El equipo de Reuse PUCE
        """

        return await self._send_email(
            to_email=to_email,
            subject=f"Intercambio: {context['status_message']} - Reuse",
            html_content=html_content,
            text_content=text_content
        )

    async def send_newsletter(
        self,
        to_emails: List[str],
        subject: str,
        title: str,
        content: str,
        cta_text: Optional[str] = None,
        cta_url: Optional[str] = None
    ) -> Dict[str, bool]:
        """
        Envía newsletter a múltiples destinatarios.

        Args:
            to_emails: Lista de emails
            subject: Asunto del correo
            title: Título del newsletter
            content: Contenido HTML del newsletter
            cta_text: Texto del botón de acción (opcional)
            cta_url: URL del botón de acción (opcional)

        Returns:
            Dict con email: resultado (True/False)
        """
        context = {
            "title": title,
            "content": content,
            "cta_text": cta_text,
            "cta_url": cta_url,
            "app_name": settings.APP_NAME,
            "email_type": EmailType.NEWSLETTER.value
        }

        html_content = await self._render_template("newsletter.html", context)

        results = {}
        for email in to_emails:
            results[email] = await self._send_email(
                to_email=email,
                subject=subject,
                html_content=html_content
            )

        # Log resumen
        sent_count = sum(1 for r in results.values() if r)
        logger.info(f"Newsletter enviado: {sent_count}/{len(to_emails)} exitosos")

        return results

    async def send_custom_email(
        self,
        to_email: str,
        subject: str,
        html_content: str,
        text_content: Optional[str] = None,
        cc: Optional[List[str]] = None,
        bcc: Optional[List[str]] = None
    ) -> bool:
        """
        Envía un correo personalizado con HTML custom.

        Args:
            to_email: Email de destino
            subject: Asunto
            html_content: Contenido HTML personalizado
            text_content: Texto plano alternativo
            cc: Copias
            bcc: Copias ocultas

        Returns:
            bool: True si se envió correctamente
        """
        return await self._send_email(
            to_email=to_email,
            subject=subject,
            html_content=html_content,
            text_content=text_content,
            cc=cc,
            bcc=bcc
        )

    async def send_notification_email(
        self,
        to_email: str,
        user_name: str,
        title: str,
        message: str,
        action_text: Optional[str] = None,
        action_url: Optional[str] = None
    ) -> bool:
        """
        Envía una notificación genérica por email.

        Args:
            to_email: Email de destino
            user_name: Nombre del usuario
            title: Título de la notificación
            message: Mensaje de la notificación
            action_text: Texto del botón de acción
            action_url: URL del botón de acción
        """
        context = {
            "title": title,
            "user_name": user_name,
            "message": message,
            "action_text": action_text,
            "action_url": action_url,
            "app_name": settings.APP_NAME,
            "email_type": EmailType.NOTIFICATION.value
        }

        html_content = await self._render_template("notification.html", context)
        text_content = f"""
        Hola {user_name},

        {title}

        {message}

        Saludos,
        El equipo de Reuse PUCE
        """

        return await self._send_email(
            to_email=to_email,
            subject=title,
            html_content=html_content,
            text_content=text_content
        )


# Instancia Singleton del servicio
email_service = EmailService()
