"""
Configuración de sesión de base de datos SQLAlchemy con patrón Singleton.
"""
from sqlalchemy import create_engine, Engine
from sqlalchemy.orm import sessionmaker, Session
from typing import Optional
from app.config import get_settings


class DatabaseConnection:
    """
    Singleton para la conexión a la base de datos.
    Garantiza una única instancia de engine y sessionmaker.
    """
    _instance: Optional['DatabaseConnection'] = None
    _engine: Optional[Engine] = None
    _session_factory: Optional[sessionmaker] = None

    def __new__(cls):
        """Implementación del patrón Singleton."""
        if cls._instance is None:
            cls._instance = super(DatabaseConnection, cls).__new__(cls)
        return cls._instance

    def __init__(self):
        """Inicializar conexión solo una vez."""
        if self._engine is None:
            settings = get_settings()

            # Crear engine de SQLAlchemy
            self._engine = create_engine(
                settings.DATABASE_URL,
                pool_pre_ping=True,      # Verificar conexiones antes de usar
                pool_recycle=3600,        # Reciclar conexiones cada hora
                pool_size=5,              # Tamaño del pool de conexiones
                max_overflow=10,          # Conexiones adicionales permitidas
                echo=settings.DEBUG,      # Log SQL queries en modo debug
            )

            # Crear SessionLocal
            self._session_factory = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self._engine
            )

    @property
    def engine(self) -> Engine:
        """Obtener engine de SQLAlchemy."""
        return self._engine

    @property
    def session_factory(self) -> sessionmaker:
        """Obtener factory de sesiones."""
        return self._session_factory

    def get_session(self) -> Session:
        """Crear nueva sesión de base de datos."""
        return self._session_factory()

    def close(self):
        """Cerrar todas las conexiones."""
        if self._engine:
            self._engine.dispose()


# Instancia Singleton
_db = DatabaseConnection()

# Exports para compatibilidad con código existente
engine = _db.engine
SessionLocal = _db.session_factory


def get_db_connection() -> DatabaseConnection:
    """Obtener instancia Singleton de conexión."""
    return _db
