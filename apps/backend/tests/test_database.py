"""Database dependency initialization tests. No live queries required."""

from __future__ import annotations

import pytest

pytest.importorskip("psycopg")

from sqlalchemy.engine import Engine

from app.db.session import SessionLocal, get_db, get_engine, get_session_factory


def test_engine_initializes() -> None:
    """Engine is created with the PostgreSQL driver and a recycled pool."""
    engine = get_engine()
    assert isinstance(engine, Engine)
    assert engine.url.drivername.startswith("postgresql")
    assert engine.pool is not None


def test_session_factory_and_get_db() -> None:
    """SessionLocal and get_db produce closeable sessions without querying."""
    factory = get_session_factory()
    session = factory()
    try:
        assert session.bind is get_engine()
    finally:
        session.close()

    opened = SessionLocal()
    opened.close()

    gen = get_db()
    db = next(gen)
    try:
        assert db is not None
    finally:
        gen.close()
