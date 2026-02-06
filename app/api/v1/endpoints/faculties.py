"""
Endpoints de facultades (catalogo).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.deps import get_db, get_current_admin_user
from app.models.faculty import Faculty
from app.models.user import User
from app.schemas.catalog import (
    FacultyCreate,
    FacultyUpdate,
    FacultyResponse,
    FacultyListResponse,
)
from app.crud import faculty as crud_faculty

router = APIRouter()


# ================================================================
# ENDPOINTS PUBLICOS
# ================================================================

@router.get("", response_model=List[FacultyResponse])
def get_faculties(
    include_inactive: bool = Query(False, description="Incluir facultades inactivas (solo admin)"),
    db: Session = Depends(get_db)
):
    """
    Obtener lista de facultades.
    Por defecto solo devuelve facultades activas.
    No requiere autenticacion.
    """
    if include_inactive:
        faculties = db.query(Faculty).order_by(Faculty.name).all()
    else:
        faculties = db.query(Faculty).filter(Faculty.is_active == True).order_by(Faculty.name).all()
    return faculties


@router.get("/{faculty_id}", response_model=FacultyResponse)
def get_faculty(
    faculty_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener una facultad por ID.
    No requiere autenticacion.
    """
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Facultad no encontrada")
    return faculty


# ================================================================
# ENDPOINTS ADMIN
# ================================================================

@router.post("", response_model=FacultyResponse, status_code=201)
def create_faculty(
    faculty_in: FacultyCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Crear una nueva facultad.
    Requiere rol de administrador o moderador.
    """
    # Verificar que el codigo no exista
    existing = db.query(Faculty).filter(Faculty.code == faculty_in.code).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una facultad con el codigo '{faculty_in.code}'"
        )

    # Verificar que el nombre no exista
    existing_name = db.query(Faculty).filter(Faculty.name == faculty_in.name).first()
    if existing_name:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una facultad con el nombre '{faculty_in.name}'"
        )

    new_faculty = Faculty(
        name=faculty_in.name,
        code=faculty_in.code,
        is_active=True
    )
    db.add(new_faculty)
    db.commit()
    db.refresh(new_faculty)
    return new_faculty


@router.put("/{faculty_id}", response_model=FacultyResponse)
def update_faculty(
    faculty_id: int,
    faculty_in: FacultyUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar una facultad.
    Requiere rol de administrador o moderador.
    """
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Facultad no encontrada")

    # Verificar codigo unico si se esta actualizando
    if faculty_in.code and faculty_in.code != faculty.code:
        existing = db.query(Faculty).filter(Faculty.code == faculty_in.code).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe una facultad con el codigo '{faculty_in.code}'"
            )

    # Verificar nombre unico si se esta actualizando
    if faculty_in.name and faculty_in.name != faculty.name:
        existing = db.query(Faculty).filter(Faculty.name == faculty_in.name).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe una facultad con el nombre '{faculty_in.name}'"
            )

    # Actualizar campos
    update_data = faculty_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(faculty, field, value)

    db.commit()
    db.refresh(faculty)
    return faculty


@router.delete("/{faculty_id}")
def delete_faculty(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar una facultad.
    Requiere rol de administrador o moderador.
    Nota: Se recomienda desactivar en lugar de eliminar.
    """
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Facultad no encontrada")

    # Verificar que no tenga usuarios asociados
    from app.models.user import User as UserModel
    users_count = db.query(UserModel).filter(UserModel.faculty_id == faculty_id).count()
    if users_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {users_count} usuarios asociados a esta facultad. Desactivela en su lugar."
        )

    db.delete(faculty)
    db.commit()
    return {"message": "Facultad eliminada exitosamente"}


@router.patch("/{faculty_id}/toggle", response_model=FacultyResponse)
def toggle_faculty_status(
    faculty_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Activar/desactivar una facultad.
    Requiere rol de administrador o moderador.
    """
    faculty = db.query(Faculty).filter(Faculty.id == faculty_id).first()
    if not faculty:
        raise HTTPException(status_code=404, detail="Facultad no encontrada")

    faculty.is_active = not faculty.is_active
    db.commit()
    db.refresh(faculty)
    return faculty
