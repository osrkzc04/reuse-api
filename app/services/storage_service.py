"""
Servicio de almacenamiento multipropósito.
Soporta almacenamiento local (desarrollo) y Cloudflare R2 (producción).

Uso:
    from app.services.storage_service import storage_service, StorageFolder

    # Subir archivo
    result = await storage_service.upload_file(
        content=file_bytes,
        folder=StorageFolder.OFFERS,
        filename="image.jpg"
    )
    # result = {"url": "https://...", "object_key": "offers/uuid.jpg", "size": 12345}

    # Eliminar archivo
    await storage_service.delete_file("offers/uuid.jpg")
"""
import logging
import uuid
from enum import Enum
from pathlib import Path
from typing import Optional

import aioboto3

from app.config import get_settings

logger = logging.getLogger(__name__)


class StorageFolder(str, Enum):
    """Carpetas disponibles para almacenamiento."""
    OFFERS = "offers"
    AVATARS = "avatars"
    DOCUMENTS = "documents"


class StorageService:
    """
    Servicio de almacenamiento abstracto.
    Soporta almacenamiento local y Cloudflare R2.
    """

    _instance = None

    # Extensiones permitidas por tipo
    ALLOWED_IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp"}
    ALLOWED_DOCUMENT_EXTENSIONS = {".pdf", ".doc", ".docx"}

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        settings = get_settings()

        self.r2_enabled = settings.R2_ENABLED
        self.upload_dir = Path(settings.UPLOAD_DIR)
        self.max_file_size = settings.MAX_FILE_SIZE

        # URL base de la API (para almacenamiento local)
        self.api_base_url = settings.API_BASE_URL.rstrip("/")

        # Configuración R2
        self.r2_account_id = settings.R2_ACCOUNT_ID
        self.r2_access_key = settings.R2_ACCESS_KEY_ID
        self.r2_secret_key = settings.R2_SECRET_ACCESS_KEY
        self.r2_bucket = settings.R2_BUCKET_NAME
        self.r2_public_url = settings.R2_PUBLIC_URL.rstrip("/")

        # Endpoint de Cloudflare R2
        self.r2_endpoint = f"https://{self.r2_account_id}.r2.cloudflarestorage.com"

        # Crear directorio local si no existe
        self.upload_dir.mkdir(parents=True, exist_ok=True)

        mode = "R2" if self.r2_enabled else "Local"
        logger.info(f"StorageService inicializado en modo: {mode}")

    def is_configured(self) -> bool:
        """Verifica si el servicio está correctamente configurado."""
        if not self.r2_enabled:
            return True  # Local siempre está disponible

        return bool(
            self.r2_account_id and
            self.r2_access_key and
            self.r2_secret_key and
            self.r2_bucket
        )

    def _get_extension(self, filename: str) -> str:
        """Obtener extensión del archivo."""
        return Path(filename).suffix.lower()

    def _generate_filename(self, original_filename: str, prefix: str = "") -> str:
        """Generar nombre único para archivo."""
        ext = self._get_extension(original_filename)
        unique_id = uuid.uuid4().hex[:12]
        if prefix:
            return f"{prefix}_{unique_id}{ext}"
        return f"{unique_id}{ext}"

    def validate_image(self, filename: str, size: int) -> tuple[bool, str]:
        """
        Validar imagen.

        Returns:
            (is_valid, error_message)
        """
        ext = self._get_extension(filename)

        if ext not in self.ALLOWED_IMAGE_EXTENSIONS:
            allowed = ", ".join(self.ALLOWED_IMAGE_EXTENSIONS)
            return False, f"Extensión no permitida. Usar: {allowed}"

        if size > self.max_file_size:
            max_mb = self.max_file_size / (1024 * 1024)
            return False, f"Archivo muy grande. Máximo: {max_mb:.1f}MB"

        return True, ""

    def validate_document(self, filename: str, size: int) -> tuple[bool, str]:
        """
        Validar documento.

        Returns:
            (is_valid, error_message)
        """
        ext = self._get_extension(filename)

        if ext not in self.ALLOWED_DOCUMENT_EXTENSIONS:
            allowed = ", ".join(self.ALLOWED_DOCUMENT_EXTENSIONS)
            return False, f"Extensión no permitida. Usar: {allowed}"

        if size > self.max_file_size:
            max_mb = self.max_file_size / (1024 * 1024)
            return False, f"Archivo muy grande. Máximo: {max_mb:.1f}MB"

        return True, ""

    def _get_content_type(self, filename: str) -> str:
        """Obtener Content-Type basado en extensión."""
        ext = self._get_extension(filename)
        content_types = {
            ".jpg": "image/jpeg",
            ".jpeg": "image/jpeg",
            ".png": "image/png",
            ".gif": "image/gif",
            ".webp": "image/webp",
            ".pdf": "application/pdf",
            ".doc": "application/msword",
            ".docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        }
        return content_types.get(ext, "application/octet-stream")

    async def upload_file(
        self,
        content: bytes,
        folder: StorageFolder,
        filename: str,
        prefix: str = ""
    ) -> dict:
        """
        Subir archivo al storage.

        Args:
            content: Contenido del archivo en bytes
            folder: Carpeta destino (offers, avatars, documents)
            filename: Nombre original del archivo
            prefix: Prefijo opcional para el nombre (ej: user_id)

        Returns:
            {
                "url": "https://cdn.example.com/offers/abc123.jpg",
                "object_key": "offers/abc123.jpg",
                "size": 123456,
                "filename": "abc123.jpg"
            }
        """
        # Generar nombre único
        new_filename = self._generate_filename(filename, prefix)
        object_key = f"{folder.value}/{new_filename}"

        if self.r2_enabled:
            return await self._upload_to_r2(content, object_key, filename)
        else:
            return await self._upload_to_local(content, object_key, folder)

    async def _upload_to_r2(self, content: bytes, object_key: str, filename: str) -> dict:
        """Subir archivo a Cloudflare R2."""
        try:
            session = aioboto3.Session()
            content_type = self._get_content_type(filename)

            async with session.client(
                "s3",
                endpoint_url=self.r2_endpoint,
                aws_access_key_id=self.r2_access_key,
                aws_secret_access_key=self.r2_secret_key,
                region_name="auto"
            ) as s3:
                await s3.put_object(
                    Bucket=self.r2_bucket,
                    Key=object_key,
                    Body=content,
                    ContentType=content_type
                )

            url = f"{self.r2_public_url}/{object_key}"
            logger.info(f"Archivo subido a R2: {object_key}")

            return {
                "url": url,
                "object_key": object_key,
                "size": len(content),
                "filename": object_key.split("/")[-1]
            }

        except Exception as e:
            error_msg = str(e) if e else "Error desconocido"
            logger.error(f"Error subiendo a R2: {error_msg}")
            raise RuntimeError(f"Error al subir archivo a R2: {error_msg}")

    async def _upload_to_local(self, content: bytes, object_key: str, folder: StorageFolder) -> dict:
        """Subir archivo a almacenamiento local."""
        try:
            # Crear subcarpeta si no existe
            folder_path = self.upload_dir / folder.value
            folder_path.mkdir(parents=True, exist_ok=True)

            # Guardar archivo
            filename = object_key.split("/")[-1]
            file_path = folder_path / filename
            file_path.write_bytes(content)

            # Generar URL completa con la base de la API
            url = f"{self.api_base_url}/uploads/{object_key}"
            logger.info(f"Archivo guardado localmente: {file_path}")

            return {
                "url": url,
                "object_key": object_key,
                "size": len(content),
                "filename": filename
            }

        except Exception as e:
            logger.error(f"Error guardando localmente: {e}")
            raise RuntimeError(f"Error al guardar archivo: {str(e)}")

    async def delete_file(self, object_key: str) -> bool:
        """
        Eliminar archivo del storage.

        Args:
            object_key: Clave del objeto (ej: "offers/abc123.jpg")

        Returns:
            True si se eliminó correctamente
        """
        if not object_key:
            return False

        if self.r2_enabled:
            return await self._delete_from_r2(object_key)
        else:
            return await self._delete_from_local(object_key)

    async def _delete_from_r2(self, object_key: str) -> bool:
        """Eliminar archivo de Cloudflare R2."""
        try:
            session = aioboto3.Session()

            async with session.client(
                "s3",
                endpoint_url=self.r2_endpoint,
                aws_access_key_id=self.r2_access_key,
                aws_secret_access_key=self.r2_secret_key,
                region_name="auto"
            ) as s3:
                await s3.delete_object(
                    Bucket=self.r2_bucket,
                    Key=object_key
                )

            logger.info(f"Archivo eliminado de R2: {object_key}")
            return True

        except Exception as e:
            logger.error(f"Error eliminando de R2: {e}")
            return False

    async def _delete_from_local(self, object_key: str) -> bool:
        """Eliminar archivo de almacenamiento local."""
        try:
            file_path = self.upload_dir / object_key

            if file_path.exists():
                file_path.unlink()
                logger.info(f"Archivo eliminado localmente: {file_path}")
                return True
            else:
                logger.warning(f"Archivo no encontrado: {file_path}")
                return False

        except Exception as e:
            logger.error(f"Error eliminando localmente: {e}")
            return False

    def get_public_url(self, object_key: str) -> str:
        """
        Obtener URL pública de un archivo.

        Args:
            object_key: Clave del objeto

        Returns:
            URL pública del archivo
        """
        if not object_key:
            return ""

        if self.r2_enabled:
            return f"{self.r2_public_url}/{object_key}"
        else:
            return f"{self.api_base_url}/uploads/{object_key}"

    def extract_object_key_from_url(self, url: str) -> Optional[str]:
        """
        Extraer object_key de una URL.

        Args:
            url: URL del archivo

        Returns:
            object_key o None si no se puede extraer
        """
        if not url:
            return None

        # URL de R2
        if self.r2_public_url and url.startswith(self.r2_public_url):
            return url.replace(f"{self.r2_public_url}/", "")

        # URL local con API base (nuevo formato: http://localhost:5002/uploads/...)
        if self.api_base_url and url.startswith(f"{self.api_base_url}/uploads/"):
            return url.replace(f"{self.api_base_url}/uploads/", "")

        # URL local relativa (formato antiguo: /uploads/...)
        if url.startswith("/uploads/"):
            return url.replace("/uploads/", "")

        return None


# Instancia Singleton del servicio
storage_service = StorageService()
