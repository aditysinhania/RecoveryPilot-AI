"""FastAPI dependencies: session, settings, request id, logger, future merchant."""

from __future__ import annotations

import logging
from typing import Annotated, Any

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from app.config.logging import get_logger
from app.config.settings import Settings, get_settings
from app.db.session import get_db
from app.utils.request_id import get_correlation_id as context_correlation_id
from app.utils.request_id import get_request_id as context_request_id

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


def get_current_merchant() -> dict[str, Any] | None:
    """Placeholder until merchant auth lands. Routers may Depend on this now."""
    return None


RequestIdDep = Annotated[str, Depends(request_id_dep)]
CorrelationIdDep = Annotated[str, Depends(correlation_id_dep)]
LoggerDep = Annotated[logging.Logger, Depends(logger_dep)]
MerchantDep = Annotated[dict[str, Any] | None, Depends(get_current_merchant)]
