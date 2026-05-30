"""Gestión de sesiones de SQLAlchemy."""

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from forge.core.config import get_settings

settings = get_settings()

# Engine (SQLite en MVP, será PostgreSQL en v0.4+)
engine = create_engine(
    settings.database_url,
    echo=settings.debug,  # Log de SQL en modo debug
    # SQLite-specific settings
    connect_args={"check_same_thread": False} if "sqlite" in settings.database_url else {},
)

# SessionLocal factory
SessionLocal = sessionmaker(
    autocommit=False,
    autoflush=False,
    bind=engine,
    expire_on_commit=False,  # Para que los objetos sigan disponibles después del commit
)


def get_session() -> Generator[Session, None, None]:
    """
    Dependency para obtener sesión de DB en FastAPI.

    Uso:
        @router.get("/endpoint")
        def endpoint(session: Session = Depends(get_session)):
            ...

    Yields:
        Session de SQLAlchemy
    """
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()
