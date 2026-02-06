"""
Endpoints de categorias (catalogo).
"""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session
from typing import List, Optional

from app.core.deps import get_db, get_current_admin_user
from app.models.category import Category
from app.models.user import User
from app.schemas.catalog import (
    CategoryCreate,
    CategoryUpdate,
    CategoryResponse,
    CategoryListResponse,
)

router = APIRouter()


# ================================================================
# ENDPOINTS PUBLICOS
# ================================================================

@router.get("", response_model=List[CategoryResponse])
def get_categories(
    include_inactive: bool = Query(False, description="Incluir categorias inactivas (solo admin)"),
    parent_id: Optional[int] = Query(None, description="Filtrar por categoria padre"),
    db: Session = Depends(get_db)
):
    """
    Obtener lista de categorias.
    Por defecto solo devuelve categorias activas.
    No requiere autenticacion.
    """
    query = db.query(Category)

    if not include_inactive:
        query = query.filter(Category.is_active == True)

    if parent_id is not None:
        query = query.filter(Category.parent_id == parent_id)

    categories = query.order_by(Category.name).all()
    return categories


@router.get("/root", response_model=List[CategoryResponse])
def get_root_categories(
    db: Session = Depends(get_db)
):
    """
    Obtener lista de categorias raiz (sin padre).
    No requiere autenticacion.
    """
    categories = db.query(Category).filter(
        Category.is_active == True,
        Category.parent_id == None
    ).order_by(Category.name).all()
    return categories


@router.get("/{category_id}", response_model=CategoryResponse)
def get_category(
    category_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener una categoria por ID.
    No requiere autenticacion.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")
    return category


@router.get("/{category_id}/children", response_model=List[CategoryResponse])
def get_category_children(
    category_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtener subcategorias de una categoria.
    No requiere autenticacion.
    """
    # Verificar que la categoria padre existe
    parent = db.query(Category).filter(Category.id == category_id).first()
    if not parent:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")

    children = db.query(Category).filter(
        Category.is_active == True,
        Category.parent_id == category_id
    ).order_by(Category.name).all()
    return children


# ================================================================
# ENDPOINTS ADMIN
# ================================================================

@router.post("", response_model=CategoryResponse, status_code=201)
def create_category(
    category_in: CategoryCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Crear una nueva categoria.
    Requiere rol de administrador o moderador.
    """
    # Verificar que el nombre no exista en el mismo nivel
    existing = db.query(Category).filter(
        Category.name == category_in.name,
        Category.parent_id == category_in.parent_id
    ).first()
    if existing:
        raise HTTPException(
            status_code=400,
            detail=f"Ya existe una categoria con el nombre '{category_in.name}' en este nivel"
        )

    # Verificar que la categoria padre exista si se especifica
    if category_in.parent_id:
        parent = db.query(Category).filter(Category.id == category_in.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=400,
                detail=f"La categoria padre con ID {category_in.parent_id} no existe"
            )

    new_category = Category(
        name=category_in.name,
        description=category_in.description,
        parent_id=category_in.parent_id,
        icon=category_in.icon,
        is_active=True
    )
    db.add(new_category)
    db.commit()
    db.refresh(new_category)
    return new_category


@router.put("/{category_id}", response_model=CategoryResponse)
def update_category(
    category_id: int,
    category_in: CategoryUpdate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Actualizar una categoria.
    Requiere rol de administrador o moderador.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")

    # Verificar nombre unico en el mismo nivel si se esta actualizando
    if category_in.name and category_in.name != category.name:
        parent_id = category_in.parent_id if category_in.parent_id is not None else category.parent_id
        existing = db.query(Category).filter(
            Category.name == category_in.name,
            Category.parent_id == parent_id,
            Category.id != category_id
        ).first()
        if existing:
            raise HTTPException(
                status_code=400,
                detail=f"Ya existe una categoria con el nombre '{category_in.name}' en este nivel"
            )

    # Verificar que no se cree una referencia circular
    if category_in.parent_id is not None:
        if category_in.parent_id == category_id:
            raise HTTPException(
                status_code=400,
                detail="Una categoria no puede ser su propio padre"
            )
        # Verificar que el padre no sea un hijo de esta categoria
        parent = db.query(Category).filter(Category.id == category_in.parent_id).first()
        if not parent:
            raise HTTPException(
                status_code=400,
                detail=f"La categoria padre con ID {category_in.parent_id} no existe"
            )

    # Actualizar campos
    update_data = category_in.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(category, field, value)

    db.commit()
    db.refresh(category)
    return category


@router.delete("/{category_id}")
def delete_category(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Eliminar una categoria.
    Requiere rol de administrador o moderador.
    Nota: Se recomienda desactivar en lugar de eliminar.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")

    # Verificar que no tenga subcategorias
    children_count = db.query(Category).filter(Category.parent_id == category_id).count()
    if children_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: tiene {children_count} subcategorias. Desactivela o elimine las subcategorias primero."
        )

    # Verificar que no tenga ofertas asociadas
    from app.models.offer import Offer
    offers_count = db.query(Offer).filter(Offer.category_id == category_id).count()
    if offers_count > 0:
        raise HTTPException(
            status_code=400,
            detail=f"No se puede eliminar: hay {offers_count} ofertas asociadas a esta categoria. Desactivela en su lugar."
        )

    db.delete(category)
    db.commit()
    return {"message": "Categoria eliminada exitosamente"}


@router.patch("/{category_id}/toggle", response_model=CategoryResponse)
def toggle_category_status(
    category_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_admin_user)
):
    """
    Activar/desactivar una categoria.
    Requiere rol de administrador o moderador.
    """
    category = db.query(Category).filter(Category.id == category_id).first()
    if not category:
        raise HTTPException(status_code=404, detail="Categoria no encontrada")

    category.is_active = not category.is_active
    db.commit()
    db.refresh(category)
    return category
