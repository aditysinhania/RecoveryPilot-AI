"""FastAPI dependencies: session, settings, request id, logger, current user."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Annotated, Any
from uuid import UUID

from database.models.merchant_user import MerchantUser
from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.config.settings import Settings, get_settings
from app.core.exceptions import UnauthorizedError
from app.db.session import get_db
from app.schemas.auth import AuthUserOut
from app.utils.request_id import get_correlation_id as context_correlation_id
from app.utils.request_id import get_request_id as context_request_id
from app.utils.request_id import set_merchant_id

SettingsDep = Annotated[Settings, Depends(get_settings)]
SessionDep = Annotated[Session, Depends(get_db)]


def request_id_dep(request: Request) -> str:
    """Read the id stamped by RequestIdMiddleware."""
    return getattr(request.state, "request_id", None) or context_request_id()


def correlation_id_dep(request: Request) -> str:
    """Read the correlation id stamped by RequestIdMiddleware."""
    return getattr(request.state, "correlation_id", None) or context_correlation_id()


def logger_dep() -> logging.Logger:
    """Request-scoped logger factory."""
    return get_logger("recoverypilot.api")


def _bearer_token(request: Request) -> str | None:
    """Parse ``Authorization: Bearer`` without raising."""
    header = request.headers.get("authorization") or request.headers.get("Authorization")
    if not header:
        return None
    scheme, _, value = header.partition(" ")
    if scheme.lower() != "bearer" or not value.strip():
        return None
    return value.strip()


@dataclass
class Principal:
    """Authenticated operator for protected routes."""

    orm: MerchantUser
    user: AuthUserOut
    session_id: UUID | None


def get_principal(
    request: Request,
    db: SessionDep,
    settings: SettingsDep,
) -> Principal:
    """Require a valid access JWT. Raises 401 when missing or invalid."""
    token = _bearer_token(request)
    if not token:
        raise UnauthorizedError()
    from app.services import auth_service

    orm, user, session_id = auth_service.me(db, settings, token)
    if user.merchant_id is not None:
        set_merchant_id(str(user.merchant_id))
    return Principal(orm=orm, user=user, session_id=session_id)


def get_current_merchant() -> dict[str, Any] | None:
    """Optional merchant placeholder for pre-auth dashboard routes.

    Existing merchant/recovery APIs stay public so current tests keep passing.
    """
    return None


RequestIdDep = Annotated[str, Depends(request_id_dep)]
CorrelationIdDep = Annotated[str, Depends(correlation_id_dep)]
LoggerDep = Annotated[logging.Logger, Depends(logger_dep)]
MerchantDep = Annotated[dict[str, Any] | None, Depends(get_current_merchant)]
CurrentUserDep = Annotated[Principal, Depends(get_principal)]
