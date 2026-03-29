"""Database session dependency helpers."""

from collections.abc import Generator

from sqlmodel import Session, create_engine

from sidekick.api.settings import get_settings

_engine = None


def get_engine():
    """Return a lazily created SQLAlchemy engine."""
    global _engine
    if _engine is None:
        settings = get_settings()
        if not settings.database_url:
            raise RuntimeError("DATABASE_URL is required")
        _engine = create_engine(settings.database_url)
    return _engine


def get_session() -> Generator[Session, None, None]:
    """Yield a database session for request-scoped dependencies."""
    with Session(get_engine()) as session:
        yield session
