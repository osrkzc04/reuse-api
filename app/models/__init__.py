"""
Módulo de modelos ORM.
Importa todos los modelos para que SQLAlchemy los reconozca.
"""
from app.db.base import Base

# Catálogos
from app.models.faculty import Faculty
from app.models.category import Category
from app.models.location import Location

# Usuarios y Autenticación
from app.models.user import User
from app.models.refresh_token import RefreshToken
from app.models.email_verification_token import EmailVerificationToken
from app.models.user_preferences import UserPreferences
from app.models.user_reputation_metrics import UserReputationMetrics

# Ofertas
from app.models.offer import Offer
from app.models.offer_photo import OfferPhoto
from app.models.offer_interest import OfferInterest

# Chat
from app.models.conversation import Conversation
from app.models.message import Message

# Intercambios
from app.models.exchange import Exchange, ExchangeEvent, ExchangeRating

# Créditos
from app.models.credits import CreditsLedger, RewardsCatalog, RewardClaim

# Gamificación
from app.models.gamification import Challenge, UserChallenge, BadgesCatalog, UserBadge

# Notificaciones
from app.models.notification import Notification

# Auditoría (Log de actividades)
from app.models.moderation import ActivityLog

# Auditoría
from app.models.audit import AuditHistory

__all__ = [
    "Base",
    # Catálogos
    "Faculty",
    "Category",
    "Location",
    # Usuarios
    "User",
    "RefreshToken",
    "EmailVerificationToken",
    "UserPreferences",
    "UserReputationMetrics",
    # Ofertas
    "Offer",
    "OfferPhoto",
    "OfferInterest",
    # Chat
    "Conversation",
    "Message",
    # Intercambios
    "Exchange",
    "ExchangeEvent",
    "ExchangeRating",
    # Créditos
    "CreditsLedger",
    "RewardsCatalog",
    "RewardClaim",
    # Gamificación
    "Challenge",
    "UserChallenge",
    "BadgesCatalog",
    "UserBadge",
    # Notificaciones
    "Notification",
    # Auditoría (Log de actividades)
    "ActivityLog",
    # Auditoría
    "AuditHistory",
]
