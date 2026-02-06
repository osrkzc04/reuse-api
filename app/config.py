"""
Configuración de la aplicación Reuse.
Maneja variables de entorno y settings globales.
"""
from pydantic_settings import BaseSettings, SettingsConfigDict
from typing import List


class Settings(BaseSettings):
    """Configuración de la aplicación usando Pydantic Settings v2."""

    # Database (REQUERIDO - debe estar en .env)
    DATABASE_URL: str

    # Security (REQUERIDO - debe estar en .env)
    SECRET_KEY: str
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7

    # Application
    APP_NAME: str = "Reuse API"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = False
    ALLOWED_ORIGINS: str = "http://localhost:3000,http://localhost:5173"

    # Initial Admin (opcional)
    ADMIN_EMAIL: str = "admin@puce.edu.ec"
    ADMIN_PASSWORD: str = "changeme123"

    # File Upload
    UPLOAD_DIR: str = "./uploads"
    MAX_FILE_SIZE: int = 5242880  # 5MB

    # Email SMTP Configuration
    SMTP_HOST: str = "smtp.gmail.com"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM_EMAIL: str = ""
    SMTP_FROM_NAME: str = "Reuse PUCE"
    SMTP_USE_TLS: bool = True
    SMTP_ENABLED: bool = False  # Deshabilitado por defecto hasta configurar

    # Frontend URL (para enlaces en correos de verificación, recuperación, etc.)
    # Cambiar según el entorno: desarrollo, producción o cambio de dominio
    FRONTEND_URL: str = "http://localhost:3000"  # Desarrollo local por defecto

    # API Base URL (para generar URLs de archivos en almacenamiento local)
    # Cambiar según el entorno: desarrollo, producción o cambio de dominio
    API_BASE_URL: str = "http://localhost:5002"  # URL base del backend

    # Cloudflare R2 Storage
    R2_ENABLED: bool = False  # False = almacenamiento local, True = Cloudflare R2
    R2_ACCOUNT_ID: str = ""
    R2_ACCESS_KEY_ID: str = ""
    R2_SECRET_ACCESS_KEY: str = ""
    R2_BUCKET_NAME: str = ""
    R2_PUBLIC_URL: str = ""  # URL pública del bucket (ej: https://cdn.tudominio.com)

    # Computed properties
    @property
    def allowed_origins_list(self) -> List[str]:
        """Convierte ALLOWED_ORIGINS string a lista."""
        return [origin.strip() for origin in self.ALLOWED_ORIGINS.split(",")]

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore"
    )


# Instancia Singleton de settings
_settings_instance = None


def get_settings() -> Settings:
    """
    Obtener instancia Singleton de configuración.
    Se carga una sola vez y se reutiliza.
    """
    global _settings_instance
    if _settings_instance is None:
        _settings_instance = Settings()
    return _settings_instance


# Instancia global de settings (Singleton)
settings = get_settings()
