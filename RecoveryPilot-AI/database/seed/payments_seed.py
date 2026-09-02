"""Payment seed scaffolding. No synthetic rows yet."""

from __future__ import annotations

import logging

from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)


def seed_payments(db: Session) -> None:
    """Insert demo payment attempts once seed data is defined.

    Args:
        db: Open SQLAlchemy session. Unused until fake data is added.
    """
    logger.info("seed.payments.skipped", extra={"reason": "no_data_yet"})
