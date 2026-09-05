"""PostgreSQL engine, session factory, and FastAPI dependency."""

from __future__ import annotations

from collections.abc import Generator

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine
from sqlalchemy.exc import OperationalError, ProgrammingError
from sqlalchemy.orm import Session, sessionmaker

from app.config.constants import POOL_RECYCLE_SECONDS
from app.config.logging import get_logger
from app.config.settings import settings
from app.core.exceptions import DatabaseUnavailableError, auth_schema_missing_error

logger = get_logger(__name__)

_engine: Engine | None = None
_session_factory: sessionmaker[Session] | None = None


def get_engine() -> Engine:
    """Create (once) a pooled SQLAlchemy engine.

    Pool recycle and pre-ping keep connections healthy behind Docker/NAT.
    Echo is opt-in via ``DB_ECHO`` so production logs never dump SQL.
    """
    global _engine
    if _engine is None:
        logger.info("db.engine.create", extra={"driver": "postgresql+psycopg"})
        _engine = create_engine(
            settings.database_url,
            pool_pre_ping=True,
            pool_size=settings.db_pool_size,
            max_overflow=settings.db_max_overflow,
            pool_recycle=POOL_RECYCLE_SECONDS,
            echo=settings.db_echo,
            future=True,
            connect_args={"connect_timeout": 3},
        )
    return _engine


def get_session_factory() -> sessionmaker[Session]:
    """Return the process-wide ``sessionmaker`` bound to the engine."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(
            bind=get_engine(),
            autoflush=False,
            autocommit=False,
            expire_on_commit=False,
            class_=Session,
        )
    return _session_factory


def SessionLocal() -> Session:
    """Open a session. Prefer ``get_db`` inside FastAPI request handlers."""
    return get_session_factory()()


def get_db() -> Generator[Session, None, None]:
    """Yield a request-scoped SQLAlchemy session.

    Connection timeouts and missing-schema errors become HTTP 503 with a
    merchant-facing message instead of an unhandled 500.
    """
    try:
        session = SessionLocal()
    except OperationalError as exc:
        logger.warning("db.operational", extra={"error_type": type(exc).__name__})
        raise DatabaseUnavailableError() from exc
    try:
        yield session
    except OperationalError as exc:
        logger.warning("db.operational", extra={"error_type": type(exc).__name__})
        raise DatabaseUnavailableError() from exc
    except ProgrammingError as exc:
        logger.warning("db.schema_missing", extra={"error_type": type(exc).__name__})
        raise auth_schema_missing_error() from exc
    finally:
        session.close()


def dispose_engine() -> None:
    """Close pooled connections on shutdown."""
    global _engine, _session_factory
    if _engine is not None:
        logger.info("db.engine.dispose")
        _engine.dispose()
        _engine = None
        _session_factory = None
