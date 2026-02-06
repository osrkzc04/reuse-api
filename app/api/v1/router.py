"""
Router principal de la API v1.
Incluye todos los endpoints de la aplicación.
"""
from fastapi import APIRouter

from app.api.v1.endpoints import (
    auth,
    users,
    offers,
    faculties,
    categories,
    locations,
    notifications,
    conversations,
    messages,
    exchanges,
    interests,
    challenges,
    badges,
    rewards,
    ranking,
    preferences,
    stats,
    offer_photos,
    uploads,
    emails,
    statistics,
    admin,
    reports,
)

api_router = APIRouter()

# ============================================================================
# AUTENTICACIÓN
# ============================================================================
api_router.include_router(
    auth.router,
    prefix="/auth",
    tags=["Autenticación"]
)

# ============================================================================
# USUARIOS
# ============================================================================
api_router.include_router(
    users.router,
    prefix="/users",
    tags=["Usuarios"]
)

api_router.include_router(
    preferences.router,
    prefix="/preferences",
    tags=["Usuarios"]
)

api_router.include_router(
    stats.router,
    prefix="/stats",
    tags=["Estadísticas"]
)

# ============================================================================
# OFERTAS
# ============================================================================
api_router.include_router(
    offers.router,
    prefix="/offers",
    tags=["Ofertas"]
)

api_router.include_router(
    interests.router,
    prefix="/interests",
    tags=["Ofertas"]
)

api_router.include_router(
    offer_photos.router,
    prefix="",  # Ya tiene el prefijo completo en las rutas
    tags=["Ofertas"]
)

api_router.include_router(
    uploads.router,
    prefix="",  # Ya tiene el prefijo completo en las rutas
    tags=["Uploads"]
)

# ============================================================================
# INTERCAMBIOS
# ============================================================================
api_router.include_router(
    exchanges.router,
    prefix="/exchanges",
    tags=["Intercambios"]
)

# ============================================================================
# CHAT
# ============================================================================
api_router.include_router(
    conversations.router,
    prefix="/conversations",
    tags=["Chat"]
)

api_router.include_router(
    messages.router,
    prefix="/messages",
    tags=["Chat"]
)

# ============================================================================
# GAMIFICACIÓN
# ============================================================================
api_router.include_router(
    challenges.router,
    prefix="/challenges",
    tags=["Gamificación"]
)

api_router.include_router(
    badges.router,
    prefix="/badges",
    tags=["Gamificación"]
)

api_router.include_router(
    rewards.router,
    prefix="/rewards",
    tags=["Gamificación"]
)

api_router.include_router(
    ranking.router,
    prefix="/ranking",
    tags=["Gamificación"]
)

# ============================================================================
# CATÁLOGOS
# ============================================================================
api_router.include_router(
    faculties.router,
    prefix="/faculties",
    tags=["Catálogos"]
)

api_router.include_router(
    categories.router,
    prefix="/categories",
    tags=["Catálogos"]
)

api_router.include_router(
    locations.router,
    prefix="/locations",
    tags=["Catálogos"]
)

# ============================================================================
# NOTIFICACIONES
# ============================================================================
api_router.include_router(
    notifications.router,
    prefix="/notifications",
    tags=["Notificaciones"]
)

# ============================================================================
# EMAILS (Solo Administradores)
# ============================================================================
api_router.include_router(
    emails.router,
    prefix="/emails",
    tags=["Emails - Admin"]
)

# ============================================================================
# ESTADÍSTICAS Y AUDITORÍA (Dashboard Admin)
# ============================================================================
api_router.include_router(
    statistics.router,
    prefix="/statistics",
    tags=["Estadísticas y Auditoría"]
)

# ============================================================================
# ADMINISTRACIÓN (Solo Administradores)
# ============================================================================
api_router.include_router(
    admin.router,
    prefix="/admin",
    tags=["Administración"]
)

# ============================================================================
# REPORTES (Solo Administradores)
# ============================================================================
api_router.include_router(
    reports.router,
    prefix="/reports",
    tags=["Reportes"]
)
