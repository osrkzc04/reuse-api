"""
Modelo ORM para Preferencias de Usuario.
"""
from sqlalchemy import Column, String, Boolean, Integer, DateTime, ForeignKey
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
from app.db.base import Base


class UserPreferences(Base):
    """Modelo de Preferencias de Usuario."""

    __tablename__ = "user_preferences"

    user_id = Column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)

    # Notificaciones
    email_notifications = Column(Boolean, default=True)
    push_notifications = Column(Boolean, default=True)
    notify_new_messages = Column(Boolean, default=True)
    notify_interests = Column(Boolean, default=True)
    notify_exchanges = Column(Boolean, default=True)
    notify_challenges = Column(Boolean, default=True)
    notify_badges = Column(Boolean, default=True)
    notify_marketing = Column(Boolean, default=False)

    # Privacidad
    profile_visibility = Column(String(20), default='public')
    show_email = Column(Boolean, default=False)
    show_whatsapp = Column(Boolean, default=False)
    show_stats = Column(Boolean, default=True)
    show_badges = Column(Boolean, default=True)

    # Preferencias
    language = Column(String(10), default='es')
    theme = Column(String(20), default='light')
    items_per_page = Column(Integer, default=20)
    saved_filters = Column(JSONB, default=[])

    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    # Relationships
    user = relationship("User", back_populates="preferences")

    def __repr__(self):
        return f"<UserPreferences for user {self.user_id}>"
