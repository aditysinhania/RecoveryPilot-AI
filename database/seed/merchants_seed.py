"""Merchant seed scaffolding. No synthetic rows yet."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def seed_merchants(db: Session) -> None:
    """Insert demo merchants once seed data is defined.

    Args:
        db: Open SQLAlchemy session. Unused until fake data is added.
    """
    logger.info("seed.merchants.skipped", extra={"reason": "no_data_yet"})
