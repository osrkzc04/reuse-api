"""
CRUD para ubicaciones/puntos de encuentro.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_
from decimal import Decimal

from app.crud.base import CRUDBase
from app.models.location import Location


class CRUDLocation(CRUDBase[Location, dict, dict]):
    """CRUD específico para ubicaciones."""

    def get_active(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Location]:
        """
        Obtener ubicaciones activas.

        Args:
            db: Sesión de base de datos
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de ubicaciones activas
        """
        return (
            db.query(Location)
            .filter(Location.is_active == True)
            .order_by(Location.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def search(
        self, db: Session, *, query: str, skip: int = 0, limit: int = 20
    ) -> List[Location]:
        """
        Buscar ubicaciones por nombre o descripción.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de ubicaciones que coinciden
        """
        search_term = f"%{query}%"
        return (
            db.query(Location)
            .filter(
                or_(
                    Location.name.ilike(search_term),
                    Location.description.ilike(search_term)
                ),
                Location.is_active == True
            )
            .order_by(Location.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_location(
        self,
        db: Session,
        *,
        name: str,
        description: Optional[str] = None,
        latitude: Optional[Decimal] = None,
        longitude: Optional[Decimal] = None
    ) -> Location:
        """
        Crear nueva ubicación.

        Args:
            db: Sesión de base de datos
            name: Nombre de la ubicación
            description: Descripción opcional
            latitude: Latitud GPS (opcional)
            longitude: Longitud GPS (opcional)

        Returns:
            Ubicación creada
        """
        new_location = Location(
            name=name,
            description=description,
            latitude=latitude,
            longitude=longitude,
            is_active=True
        )
        db.add(new_location)
        db.commit()
        db.refresh(new_location)
        return new_location

    def update_coordinates(
        self,
        db: Session,
        *,
        location_id: int,
        latitude: Decimal,
        longitude: Decimal
    ) -> Optional[Location]:
        """
        Actualizar coordenadas GPS de una ubicación.

        Args:
            db: Sesión de base de datos
            location_id: ID de la ubicación
            latitude: Nueva latitud
            longitude: Nueva longitud

        Returns:
            Ubicación actualizada o None
        """
        location = self.get(db, id=location_id)
        if location:
            location.latitude = latitude
            location.longitude = longitude
            db.commit()
            db.refresh(location)
        return location

    def toggle_active(
        self, db: Session, *, location_id: int
    ) -> Optional[Location]:
        """
        Activar/desactivar una ubicación.

        Args:
            db: Sesión de base de datos
            location_id: ID de la ubicación

        Returns:
            Ubicación actualizada o None
        """
        location = self.get(db, id=location_id)
        if location:
            location.is_active = not location.is_active
            db.commit()
            db.refresh(location)
        return location

    def get_nearest_locations(
        self,
        db: Session,
        *,
        latitude: Decimal,
        longitude: Decimal,
        limit: int = 5
    ) -> List[Location]:
        """
        Obtener ubicaciones más cercanas a unas coordenadas.

        Usa la fórmula de Haversine para calcular distancias.

        Args:
            db: Sesión de base de datos
            latitude: Latitud de referencia
            longitude: Longitud de referencia
            limit: Cantidad máxima de resultados

        Returns:
            Lista de ubicaciones ordenadas por distancia
        """
        from sqlalchemy import func

        # Fórmula de Haversine para calcular distancia
        # Esto es una aproximación simple, para producción considerar usar PostGIS
        distance = func.sqrt(
            func.pow(Location.latitude - latitude, 2) +
            func.pow(Location.longitude - longitude, 2)
        )

        return (
            db.query(Location)
            .filter(
                Location.is_active == True,
                Location.latitude.isnot(None),
                Location.longitude.isnot(None)
            )
            .order_by(distance)
            .limit(limit)
            .all()
        )


# Instancia global del CRUD
location = CRUDLocation(Location)
