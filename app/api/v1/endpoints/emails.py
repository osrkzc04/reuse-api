"""
Endpoints de Email para Administradores.

Solo usuarios con rol 'administrador' pueden acceder a estos endpoints.
Los correos automaticos del sistema (verificacion, password reset, etc.)
se envian internamente sin necesidad de estos endpoints.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from typing import List

from app.core.deps import get_current_superadmin_user
from app.services.email_service import email_service
from app.schemas.email import (
    SendEmailRequest,
    SendNewsletterRequest,
    SendNotificationRequest,
    EmailResponse,
    NewsletterResponse,
    EmailConfigStatus,
    EmailType
)

router = APIRouter()


@router.get(
    "/status",
    response_model=EmailConfigStatus,
    summary="Estado de configuracion de email",
    description="Verifica si el servicio de email esta configurado correctamente."
)
async def get_email_status(
    current_user = Depends(get_current_superadmin_user)
):
    """
    Obtener el estado de configuracion del servicio de email.
    Solo administradores pueden ver esta informacion.
    """
    return EmailConfigStatus(
        enabled=email_service.enabled,
        configured=email_service.is_configured(),
        smtp_host=email_service.smtp_host,
        smtp_port=email_service.smtp_port,
        from_email=email_service.from_email or "No configurado"
    )


@router.post(
    "/send",
    response_model=EmailResponse,
    summary="Enviar correo personalizado",
    description="Envia un correo electronico personalizado con contenido HTML."
)
async def send_custom_email(
    email_data: SendEmailRequest,
    current_user = Depends(get_current_superadmin_user)
):
    """
    Enviar un correo electronico personalizado.

    - **to_email**: Email de destino
    - **subject**: Asunto del correo
    - **html_content**: Contenido HTML del correo
    - **text_content**: Contenido de texto plano (opcional, fallback)
    - **cc**: Lista de emails en copia (opcional)
    - **bcc**: Lista de emails en copia oculta (opcional)

    Solo administradores pueden usar este endpoint.
    """
    if not email_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de email no esta configurado. Configure las variables SMTP en el servidor."
        )

    success = await email_service.send_custom_email(
        to_email=email_data.to_email,
        subject=email_data.subject,
        html_content=email_data.html_content,
        text_content=email_data.text_content,
        cc=email_data.cc,
        bcc=email_data.bcc
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al enviar el correo. Verifique los logs del servidor."
        )

    return EmailResponse(
        success=True,
        message=f"Correo enviado exitosamente a {email_data.to_email}",
        email_type=EmailType.CUSTOM
    )


@router.post(
    "/newsletter",
    response_model=NewsletterResponse,
    summary="Enviar newsletter",
    description="Envia un newsletter a multiples destinatarios (maximo 100 por solicitud)."
)
async def send_newsletter(
    newsletter_data: SendNewsletterRequest,
    current_user = Depends(get_current_superadmin_user)
):
    """
    Enviar un newsletter a multiples destinatarios.

    - **to_emails**: Lista de emails (maximo 100)
    - **subject**: Asunto del correo
    - **title**: Titulo del newsletter
    - **content**: Contenido HTML del newsletter
    - **cta_text**: Texto del boton de accion (opcional)
    - **cta_url**: URL del boton de accion (opcional)

    Solo administradores pueden usar este endpoint.
    """
    if not email_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de email no esta configurado. Configure las variables SMTP en el servidor."
        )

    results = await email_service.send_newsletter(
        to_emails=newsletter_data.to_emails,
        subject=newsletter_data.subject,
        title=newsletter_data.title,
        content=newsletter_data.content,
        cta_text=newsletter_data.cta_text,
        cta_url=newsletter_data.cta_url
    )

    sent_count = sum(1 for r in results.values() if r)
    failed_count = len(results) - sent_count

    return NewsletterResponse(
        total=len(results),
        sent=sent_count,
        failed=failed_count,
        results=results
    )


@router.post(
    "/notification",
    response_model=EmailResponse,
    summary="Enviar notificacion por email",
    description="Envia una notificacion personalizada a un usuario."
)
async def send_notification_email(
    notification_data: SendNotificationRequest,
    current_user = Depends(get_current_superadmin_user)
):
    """
    Enviar una notificacion por email a un usuario.

    - **to_email**: Email de destino
    - **user_name**: Nombre del usuario
    - **title**: Titulo de la notificacion
    - **message**: Mensaje de la notificacion
    - **action_text**: Texto del boton (opcional)
    - **action_url**: URL del boton (opcional)

    Solo administradores pueden usar este endpoint.
    """
    if not email_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de email no esta configurado. Configure las variables SMTP en el servidor."
        )

    success = await email_service.send_notification_email(
        to_email=notification_data.to_email,
        user_name=notification_data.user_name,
        title=notification_data.title,
        message=notification_data.message,
        action_text=notification_data.action_text,
        action_url=notification_data.action_url
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al enviar el correo. Verifique los logs del servidor."
        )

    return EmailResponse(
        success=True,
        message=f"Notificacion enviada exitosamente a {notification_data.to_email}",
        email_type=EmailType.NOTIFICATION
    )


@router.post(
    "/test",
    response_model=EmailResponse,
    summary="Enviar correo de prueba",
    description="Envia un correo de prueba para verificar la configuracion SMTP."
)
async def send_test_email(
    current_user = Depends(get_current_superadmin_user)
):
    """
    Envia un correo de prueba al email del administrador actual.
    Util para verificar que la configuracion SMTP funciona correctamente.
    """
    if not email_service.is_configured():
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="El servicio de email no esta configurado. Configure las variables SMTP en el servidor."
        )

    test_html = """
    <div style="font-family: Arial, sans-serif; padding: 20px;">
        <h1 style="color: #2E7D32;">Prueba de Email - Reuse</h1>
        <p>Este es un correo de prueba enviado desde el panel de administracion de Reuse.</p>
        <p>Si recibes este correo, la configuracion SMTP esta funcionando correctamente.</p>
        <hr>
        <p style="color: #666; font-size: 12px;">
            Enviado desde: Reuse API<br>
            Servidor SMTP: {smtp_host}:{smtp_port}
        </p>
    </div>
    """.format(
        smtp_host=email_service.smtp_host,
        smtp_port=email_service.smtp_port
    )

    success = await email_service.send_custom_email(
        to_email=current_user.email,
        subject="Prueba de Email - Reuse",
        html_content=test_html,
        text_content="Este es un correo de prueba de Reuse. La configuracion SMTP esta funcionando correctamente."
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error al enviar el correo de prueba. Verifique la configuracion SMTP y los logs del servidor."
        )

    return EmailResponse(
        success=True,
        message=f"Correo de prueba enviado a {current_user.email}",
        email_type=EmailType.CUSTOM
    )
