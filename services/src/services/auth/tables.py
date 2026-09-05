"""Create auth tables if they are missing. Idempotent (checkfirst)."""

from __future__ import annotations

import logging

from database.models.auth_session import AuthSession
from database.models.merchant_settings import MerchantSettings
from database.models.merchant_user import MerchantUser
from sqlalchemy.orm import Session

logger = logging.getLogger(__name__)

_READY = False


def ensure_auth_tables(session: Session) -> None:
    """Create merchant_users, auth_sessions, and merchant_settings when absent."""
    global _READY
    if _READY:
        return
    bind = session.get_bind()
    MerchantUser.__table__.create(bind, checkfirst=True)
    AuthSession.__table__.create(bind, checkfirst=True)
    MerchantSettings.__table__.create(bind, checkfirst=True)
    _READY = True
    logger.info("auth.tables.ready")
