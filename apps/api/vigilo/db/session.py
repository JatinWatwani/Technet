"""Database engine, connection pool, and session lifecycle management."""
from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import Engine, create_engine
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy.pool import NullPool, QueuePool, StaticPool

from .base import Base


def normalize_database_url(url: str | None) -> str:
    """Normalizes postgresql:// URL to postgresql+psycopg:// for psycopg3 compatibility."""
    if not url:
        # Fallback to local SQLite file database for zero-config local persistence
        return os.getenv("SQLITE_URL", "sqlite:///vigilo_local.db")

    if url.startswith("postgres://"):
        url = "postgresql+psycopg://" + url[len("postgres://"):]
    elif url.startswith("postgresql://") and not url.startswith("postgresql+"):
        url = "postgresql+psycopg://" + url[len("postgresql://"):]

    return url


def create_db_engine(database_url: str | None = None, echo: bool = False) -> Engine:
    """Creates a production-ready SQLAlchemy engine with appropriate connection pooling."""
    url = normalize_database_url(database_url)

    if url.startswith("sqlite"):
        if ":memory:" in url:
            return create_engine(
                url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=echo,
            )
        return create_engine(
            url,
            connect_args={"check_same_thread": False},
            echo=echo,
        )

    # PostgreSQL / Supabase connection pool
    return create_engine(
        url,
        poolclass=QueuePool,
        pool_size=10,
        max_overflow=20,
        pool_timeout=30,
        pool_pre_ping=True,
        pool_recycle=1800,
        echo=echo,
    )


def init_db(engine: Engine) -> None:
    """Creates all database tables defined in ORM metadata if they do not exist."""
    Base.metadata.create_all(bind=engine)


_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def configure_db(database_url: str | None = None) -> tuple[Engine, sessionmaker[Session]]:
    global _engine, _session_factory
    _engine = create_db_engine(database_url)
    init_db(_engine)
    _session_factory = sessionmaker(bind=_engine, autoflush=False, autocommit=False, expire_on_commit=False)
    return _engine, _session_factory


def get_global_session_factory() -> sessionmaker[Session]:
    global _session_factory
    if _session_factory is None:
        db_url = os.getenv("DATABASE_URL")
        configure_db(db_url)
    assert _session_factory is not None
    return _session_factory


@contextmanager
def db_session() -> Generator[Session, None, None]:
    """Context manager for transactional database sessions."""
    factory = get_global_session_factory()
    session = factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_db() -> Generator[Session, None, None]:
    """FastAPI dependency for injected database sessions."""
    with db_session() as session:
        yield session
