"""UTC clock helpers."""

from __future__ import annotations

from datetime import UTC, datetime

from app.config.constants import DEFAULT_TIMEZONE


def utc_now() -> datetime:
    """Return timezone-aware UTC now."""
    return datetime.now(UTC)


def isoformat_now() -> str:
    """Return an ISO-8601 UTC timestamp."""
    return utc_now().isoformat()


def default_timezone() -> str:
    """Return the merchant default timezone constant."""
    return DEFAULT_TIMEZONE
