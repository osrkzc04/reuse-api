"""
CRUD para categorías.
"""
from typing import List, Optional
from sqlalchemy.orm import Session
from sqlalchemy import or_

from app.crud.base import CRUDBase
from app.models.category import Category


class CRUDCategory(CRUDBase[Category, dict, dict]):
    """CRUD específico para categorías."""

    def get_active(
        self, db: Session, *, skip: int = 0, limit: int = 100
    ) -> List[Category]:
        """
        Obtener categorías activas.

        Args:
            db: Sesión de base de datos
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de categorías activas
        """
        return (
            db.query(Category)
            .filter(Category.is_active == True)
            .order_by(Category.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def get_root_categories(self, db: Session) -> List[Category]:
        """
        Obtener categorías raíz (sin padre).

        Args:
            db: Sesión de base de datos

        Returns:
            Lista de categorías raíz
        """
        return (
            db.query(Category)
            .filter(Category.parent_id == None, Category.is_active == True)
            .order_by(Category.name)
            .all()
        )

    def get_subcategories(
        self, db: Session, *, parent_id: int
    ) -> List[Category]:
        """
        Obtener subcategorías de una categoría padre.

        Args:
            db: Sesión de base de datos
            parent_id: ID de la categoría padre

        Returns:
            Lista de subcategorías
        """
        return (
            db.query(Category)
            .filter(Category.parent_id == parent_id, Category.is_active == True)
            .order_by(Category.name)
            .all()
        )

    def search(
        self, db: Session, *, query: str, skip: int = 0, limit: int = 20
    ) -> List[Category]:
        """
        Buscar categorías por nombre o descripción.

        Args:
            db: Sesión de base de datos
            query: Término de búsqueda
            skip: Registros a saltar
            limit: Límite de registros

        Returns:
            Lista de categorías que coinciden
        """
        search_term = f"%{query}%"
        return (
            db.query(Category)
            .filter(
                or_(
                    Category.name.ilike(search_term),
                    Category.description.ilike(search_term)
                ),
                Category.is_active == True
            )
            .order_by(Category.name)
            .offset(skip)
            .limit(limit)
            .all()
        )

    def create_category(
        self,
        db: Session,
        *,
        name: str,
        description: Optional[str] = None,
        parent_id: Optional[int] = None,
        icon: Optional[str] = None
    ) -> Category:
        """
        Crear nueva categoría.

        Args:
            db: Sesión de base de datos
            name: Nombre de la categoría
            description: Descripción opcional
            parent_id: ID de la categoría padre (opcional)
            icon: Icono de la categoría (opcional)

        Returns:
            Categoría creada

        Raises:
            ValueError: Si el padre no existe
        """
        # Verificar que el padre existe si se especificó
        if parent_id:
            parent = self.get(db, id=parent_id)
            if not parent:
                raise ValueError(f"La categoría padre con ID {parent_id} no existe")

        new_category = Category(
            name=name,
            description=description,
            parent_id=parent_id,
            icon=icon,
            is_active=True
        )
        db.add(new_category)
        db.commit()
        db.refresh(new_category)
        return new_category

    def toggle_active(
        self, db: Session, *, category_id: int
    ) -> Optional[Category]:
        """
        Activar/desactivar una categoría.

        Args:
            db: Sesión de base de datos
            category_id: ID de la categoría

        Returns:
            Categoría actualizada o None
        """
        category = self.get(db, id=category_id)
        if category:
            category.is_active = not category.is_active
            db.commit()
            db.refresh(category)
        return category

    def get_category_tree(self, db: Session) -> List[dict]:
        """
        Obtener árbol completo de categorías (padre-hijo).

        Args:
            db: Sesión de base de datos

        Returns:
            Lista de categorías con sus hijos anidados
        """
        # Obtener todas las categorías activas
        all_categories = (
            db.query(Category)
            .filter(Category.is_active == True)
            .order_by(Category.name)
            .all()
        )

        # Construir árbol
        category_map = {cat.id: {
            "id": cat.id,
            "name": cat.name,
            "description": cat.description,
            "icon": cat.icon,
            "parent_id": cat.parent_id,
            "children": []
        } for cat in all_categories}

        tree = []
        for cat_data in category_map.values():
            if cat_data["parent_id"] is None:
                tree.append(cat_data)
            elif cat_data["parent_id"] in category_map:
                category_map[cat_data["parent_id"]]["children"].append(cat_data)

        return tree


# Instancia global del CRUD
category = CRUDCategory(Category)
