"""Sentry bootstrap. Disabled when SENTRY_DSN is empty. No domain logic."""

from __future__ import annotations

import logging
from typing import Any

from app.config.settings import Settings
from app.core.exceptions import ApplicationException

logger = logging.getLogger(__name__)


def _before_send(event: dict[str, Any], hint: dict[str, Any]) -> dict[str, Any] | None:
    """Drop expected business / client errors so they do not page on-call."""
    exc_info = hint.get("exc_info")
    if exc_info:
        exc = exc_info[1]
        if isinstance(exc, ApplicationException):
            return None
        status = getattr(exc, "status_code", None)
        if isinstance(status, int) and 400 <= status < 500:
            return None
    return event


def init_sentry(settings: Settings) -> None:
    """Initialize the Sentry SDK when a DSN is configured."""
    dsn = (settings.sentry_dsn or "").strip()
    if not dsn:
        logger.info("sentry.disabled")
        return
    import sentry_sdk
    from sentry_sdk.integrations.fastapi import FastApiIntegration
    from sentry_sdk.integrations.logging import LoggingIntegration
    from sentry_sdk.integrations.starlette import StarletteIntegration

    sentry_sdk.init(
        dsn=dsn,
        environment=settings.app_env,
        release=f"{settings.app_version}+{settings.build_sha}",
        traces_sample_rate=max(0.0, min(1.0, settings.sentry_traces_sample_rate)),
        send_default_pii=False,
        before_send=_before_send,
        integrations=[
            StarletteIntegration(transaction_style="endpoint"),
            FastApiIntegration(transaction_style="endpoint"),
            LoggingIntegration(level=logging.INFO, event_level=logging.ERROR),
        ],
    )
    logger.info(
        "sentry.enabled",
        extra={"environment": settings.app_env, "release": settings.app_version},
    )
