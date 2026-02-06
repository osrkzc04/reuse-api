"""
Servicio de inicialización de la aplicación.
Crea datos iniciales necesarios al arrancar.
"""
import sys
import time
from sqlalchemy.orm import Session
from sqlalchemy import text
from app.config import get_settings
from app.db.session import SessionLocal
from app.models.user import User
from app.core.security import get_password_hash


def log(message: str):
    """Imprimir mensaje con flush para Docker."""
    print(message, flush=True)
    sys.stdout.flush()


def wait_for_db(max_retries: int = 10, delay: int = 2) -> bool:
    """
    Esperar a que la base de datos esté lista.

    Args:
        max_retries: Número máximo de reintentos
        delay: Segundos entre reintentos

    Returns:
        True si la BD está lista, False si falló
    """
    for attempt in range(max_retries):
        try:
            db = SessionLocal()
            # Verificar que la tabla users existe
            db.execute(text("SELECT 1 FROM users LIMIT 1"))
            db.close()
            return True
        except Exception as e:
            if attempt < max_retries - 1:
                log(f"⏳ Esperando base de datos... intento {attempt + 1}/{max_retries}")
                time.sleep(delay)
            else:
                log(f"❌ Base de datos no disponible después de {max_retries} intentos: {e}")
                return False
    return False


def init_admin_user() -> bool:
    """
    Crear usuario administrador inicial si no existe.

    Usa las variables de entorno ADMIN_EMAIL y ADMIN_PASSWORD.

    Returns:
        True si se creó el usuario, False si ya existía o hubo error
    """
    settings = get_settings()

    # Verificar que las credenciales estén configuradas
    if not settings.ADMIN_EMAIL or not settings.ADMIN_PASSWORD:
        log("⚠️  ADMIN_EMAIL o ADMIN_PASSWORD no configurados")
        return False

    log(f"📧 Admin email configurado: {settings.ADMIN_EMAIL}")

    # Esperar a que la BD esté lista
    if not wait_for_db():
        return False

    db: Session = SessionLocal()

    try:
        # Verificar si el admin ya existe
        existing_admin = db.query(User).filter(
            User.email == settings.ADMIN_EMAIL
        ).first()

        if existing_admin:
            log(f"✅ Usuario administrador ya existe: {settings.ADMIN_EMAIL}")
            return False

        # Crear usuario administrador
        admin_user = User(
            email=settings.ADMIN_EMAIL,
            password_hash=get_password_hash(settings.ADMIN_PASSWORD),
            full_name="Administrador",
            role="administrador",
            status="active",
            is_email_verified=True,
        )

        db.add(admin_user)
        db.commit()

        log(f"✅ Usuario administrador creado: {settings.ADMIN_EMAIL}")
        log("⚠️  IMPORTANTE: Cambia la contraseña después del primer login")

        return True

    except Exception as e:
        db.rollback()
        log(f"❌ Error al crear usuario administrador: {e}")
        import traceback
        traceback.print_exc()
        return False

    finally:
        db.close()


def run_initialization():
    """
    Ejecutar todas las tareas de inicialización.
    Llamar desde el evento startup de FastAPI.
    """
    log("\n🔧 Ejecutando inicialización...")

    # Crear admin
    init_admin_user()

    log("🔧 Inicialización completada\n")
