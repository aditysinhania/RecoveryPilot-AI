"""SQLAlchemy connectivity probe. Does not expose credentials."""

from __future__ import annotations

from sqlalchemy import text

from app.config.logging import get_logger
from app.db.session import get_engine

logger = get_logger(__name__)


def ping_database() -> bool:
    """Return True if ``SELECT 1`` succeeds.

    Failures are logged without the connection URL.
    """
    try:
        with get_engine().connect() as connection:
            connection.execute(text("SELECT 1"))
        logger.info("db.health.ok")
        return True
    except Exception as exc:
        logger.warning("db.health.failed", extra={"error_type": type(exc).__name__})
        return False
