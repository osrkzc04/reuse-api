"""
Endpoints de ubicaciones del campus (catalogo).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.deps import get_db, get_current_admin_user
from app.models.location import Location
from app.models.user import User
from app.schemas.catalog import (
    LocationCreate,
    LocationUpdate,
    LocationResponse,
    LocationListResponse,
)

router = APIRouter()


# ================================================================
# ENDPOINTS PUBLICOS
# ================================================================

@router.get("", response_model=List[LocationResponse])
def get_locations(
    include_inactive: bool = Query(False, description="Incluir ubicaciones inactivas (solo admin)"),
    db: Session = Depends(get_db)
):
    """
    Obtener lista de ubicaciones del campus.
    Por defecto solo devuelve ubicaciones activas.
    No requiere autenticacion.
    """
    if include_inactive:
        locations = db.query(Location).order_by(Location.name).all()
    else:
        locations = db.query(Location).filter(Location.is_active == True).order_by(Location.name).all()
    return locations


@router.get("/{location_id}", response_model=LocationResponse)
def get_location(
    location_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener una ubicacion por ID.
    No requiere autenticacion.
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicacion no encontrada")
    return location


# ================================================================
# ENDPOINTS ADMIN
# ================================================================

@router.post("", response_model=LocationResponse, status_code=201)
def create_location(
    location_in: LocationCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Crear una nueva ubicacion.
    Requiere rol de administrador o moderador.
    """
    # Verificar que el nombre no exista
    existing = db.query(Location).filter(Location.name == location_in.name).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una ubicacion con el nombre '{location_in.name}'"
        )

    new_location = Location(
        name=location_in.name,
        description=location_in.description,
        latitude=location_in.latitude,
        longitude=location_in.longitude,
        is_active=True
    )
    db.add(new_location)
    db.commit()
    db.refresh(new_location)
    return new_location


@router.put("/{location_id}", response_model=LocationResponse)
def update_location(
    location_id: int,
    location_in: LocationUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar una ubicacion.
    Requiere rol de administrador o moderador.
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicacion no encontrada")

    # Verificar nombre unico si se esta actualizando
    if location_in.name and location_in.name != location.name:
        existing = db.query(Location).filter(Location.name == location_in.name).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe una ubicacion con el nombre '{location_in.name}'"
            )

    # Actualizar campos
    update_data = location_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(location, field, value)

    db.commit()
    db.refresh(location)
    return location


@router.delete("/{location_id}")
def delete_location(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar una ubicacion.
    Requiere rol de administrador o moderador.
    Nota: Se recomienda desactivar en lugar de eliminar.
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicacion no encontrada")

    # Verificar que no tenga ofertas asociadas
    from app.models.offer import Offer
    offers_count = db.query(Offer).filter(Offer.location_id == location_id).count()
    if offers_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {offers_count} ofertas asociadas a esta ubicacion. Desactivela en su lugar."
        )

    # Verificar que no tenga intercambios asociados
    from app.models.exchange import Exchange
    exchanges_count = db.query(Exchange).filter(Exchange.location_id == location_id).count()
    if exchanges_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {exchanges_count} intercambios asociados a esta ubicacion. Desactivela en su lugar."
        )

    db.delete(location)
    db.commit()
    return {"message": "Ubicacion eliminada exitosamente"}


@router.patch("/{location_id}/toggle", response_model=LocationResponse)
def toggle_location_status(
    location_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Activar/desactivar una ubicacion.
    Requiere rol de administrador o moderador.
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicacion no encontrada")

    location.is_active = not location.is_active
    db.commit()
    db.refresh(location)
    return location


@router.patch("/{location_id}/coordinates", response_model=LocationResponse)
def update_location_coordinates(
    location_id: int,
    latitude: float = Query(..., ge=-90, le=90),
    longitude: float = Query(..., ge=-180, le=180),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar coordenadas de una ubicacion.
    Requiere rol de administrador o moderador.
    """
    location = db.query(Location).filter(Location.id == location_id).first()
    if not location:
        raise HTTPException(status_code=404, detail="Ubicacion no encontrada")

    location.latitude = latitude
    location.longitude = longitude
    db.commit()
    db.refresh(location)
    return location
