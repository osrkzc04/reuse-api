"""
Endpoints para subir archivos (imágenes).
Soporta almacenamiento local (desarrollo) y Cloudflare R2 (producción).
"""
from fastapi import APIRouter, Depends, HTTPException, status, UploadFile, File
from sqlalchemy.orm import Session
from uuid import UUID
from typing import List
from pydantic import BaseModel

from app.core.deps import get_db, get_current_active_user
from app.models.user import User
from app.models.offer import Offer
from app.models.offer_photo import OfferPhoto
from app.services.storage_service import storage_service, StorageFolder


# Schemas
class UploadResponse(BaseModel):
    """Respuesta de subida de archivo."""
    filename: str
    url: str
    size: int
    object_key: str = ""

    model_config = {"from_attributes": True}


router = APIRouter()


async def _upload_image(
    file: UploadFile,
    folder: StorageFolder,
    prefix: str = ""
) -> dict:
    """
    Función auxiliar para subir imagen validando extensión y tamaño.

    Args:
        file: Archivo a subir
        folder: Carpeta destino
        prefix: Prefijo opcional para el nombre

    Returns:
        Diccionario con información del archivo subido
    """
    # Verificar que se subió un archivo
    if not file or not file.filename:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No se recibió ningún archivo"
        )

    # Leer contenido y tamaño
    content = await file.read()
    file_size = len(content)

    # Validar imagen
    is_valid, error_msg = storage_service.validate_image(file.filename, file_size)
    if not is_valid:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=error_msg
        )

    # Subir archivo
    try:
        result = await storage_service.upload_file(
            content=content,
            folder=folder,
            filename=file.filename,
            prefix=prefix
        )
        return result
    except RuntimeError as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=str(e)
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error inesperado al subir archivo: {str(e)}"
        )


# ===========================================
# ENDPOINTS DE OFERTAS
# ===========================================

@router.post("/upload/offer-photo", response_model=UploadResponse)
async def upload_offer_photo(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Subir una foto para una oferta.

    Requiere autenticación.

    Formatos permitidos: JPG, JPEG, PNG, GIF, WEBP
    Tamaño máximo: 5MB

    Retorna la URL de la imagen subida.
    """
    result = await _upload_image(file, StorageFolder.OFFERS)

    return UploadResponse(
        filename=result["filename"],
        url=result["url"],
        size=result["size"],
        object_key=result["object_key"]
    )


@router.post("/upload/offer-photos-bulk", response_model=List[UploadResponse])
async def upload_multiple_offer_photos(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(get_current_active_user)
):
    """
    Subir múltiples fotos para una oferta (máximo 5).

    Requiere autenticación.

    Formatos permitidos: JPG, JPEG, PNG, GIF, WEBP
    Tamaño máximo por archivo: 5MB
    """
    if len(files) > 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Máximo 5 fotos por vez"
        )

    uploaded_files = []

    for file in files:
        result = await _upload_image(file, StorageFolder.OFFERS)
        uploaded_files.append(UploadResponse(
            filename=result["filename"],
            url=result["url"],
            size=result["size"],
            object_key=result["object_key"]
        ))

    return uploaded_files


@router.post("/offers/{offer_id}/upload-photo", response_model=dict)
async def upload_and_attach_photo(
    offer_id: UUID,
    file: UploadFile = File(...),
    is_primary: bool = False,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Subir una foto Y asociarla directamente a una oferta.

    Endpoint combinado que:
    1. Sube el archivo
    2. Crea el registro en offer_photos
    3. Retorna la información completa

    Requiere autenticación y ser dueño de la oferta.
    """
    # Verificar que la oferta existe y pertenece al usuario
    offer = db.query(Offer).filter(Offer.id == offer_id).first()
    if not offer:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Oferta no encontrada"
        )

    if offer.user_id != current_user.id:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Solo el dueño de la oferta puede subir fotos"
        )

    # Verificar límite de fotos
    current_photos_count = (
        db.query(OfferPhoto)
        .filter(OfferPhoto.offer_id == offer_id)
        .count()
    )

    if current_photos_count >= 5:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Máximo 5 fotos por oferta"
        )

    # Subir archivo
    result = await _upload_image(file, StorageFolder.OFFERS)

    # Si se marca como principal, quitar la marca de las demás
    if is_primary:
        db.query(OfferPhoto).filter(
            OfferPhoto.offer_id == offer_id,
            OfferPhoto.is_primary == True
        ).update({"is_primary": False})

    # Calcular display_order
    from sqlalchemy import func
    max_order = (
        db.query(func.max(OfferPhoto.display_order))
        .filter(OfferPhoto.offer_id == offer_id)
        .scalar() or 0
    )

    # Crear registro en BD
    new_photo = OfferPhoto(
        offer_id=offer_id,
        photo_url=result["url"],
        object_key=result["object_key"],
        is_primary=is_primary,
        display_order=max_order + 1
    )
    db.add(new_photo)
    db.commit()
    db.refresh(new_photo)

    return {
        "id": new_photo.id,
        "offer_id": str(new_photo.offer_id),
        "photo_url": new_photo.photo_url,
        "object_key": new_photo.object_key,
        "is_primary": new_photo.is_primary,
        "display_order": new_photo.display_order,
        "filename": result["filename"],
        "size": result["size"]
    }


# ===========================================
# ENDPOINTS DE AVATAR
# ===========================================

@router.post("/upload/avatar", response_model=UploadResponse)
async def upload_avatar(
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Subir foto de perfil del usuario actual.

    Reemplaza la foto anterior si existe.

    Formatos permitidos: JPG, JPEG, PNG, GIF, WEBP
    Tamaño máximo: 5MB
    """
    # Guardar referencia al avatar anterior
    old_avatar_url = current_user.profile_photo_url

    # Subir nuevo avatar con prefijo del user_id
    user_prefix = str(current_user.id).split("-")[0]  # Primeros caracteres del UUID
    result = await _upload_image(file, StorageFolder.AVATARS, prefix=user_prefix)

    # Actualizar URL en la BD
    current_user.profile_photo_url = result["url"]
    db.add(current_user)
    db.commit()

    # Eliminar avatar anterior si existe
    if old_avatar_url:
        old_object_key = storage_service.extract_object_key_from_url(old_avatar_url)
        if old_object_key:
            await storage_service.delete_file(old_object_key)

    return UploadResponse(
        filename=result["filename"],
        url=result["url"],
        size=result["size"],
        object_key=result["object_key"]
    )


@router.delete("/upload/avatar")
async def delete_avatar(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_active_user)
):
    """
    Eliminar foto de perfil del usuario actual.
    """
    if not current_user.profile_photo_url:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No tienes foto de perfil"
        )

    # Obtener object_key de la URL
    object_key = storage_service.extract_object_key_from_url(current_user.profile_photo_url)

    # Eliminar del storage
    if object_key:
        await storage_service.delete_file(object_key)

    # Limpiar URL en BD
    current_user.profile_photo_url = None
    db.add(current_user)
    db.commit()

    return {"message": "Foto de perfil eliminada"}
