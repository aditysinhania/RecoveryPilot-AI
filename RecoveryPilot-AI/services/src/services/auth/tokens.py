"""JWT access and refresh tokens. Secrets never go in the payload."""

from __future__ import annotations

import hashlib
import logging
from datetime import UTC, datetime, timedelta
from typing import Any
from uuid import UUID

import jwt

from services.auth.constants import TOKEN_TYPE_ACCESS, TOKEN_TYPE_REFRESH
from services.auth.errors import UnauthorizedError

logger = logging.getLogger(__name__)


def hash_refresh_token(token: str) -> str:
    """SHA-256 hex digest used as the session lookup key."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()


def encode_token(
    payload: dict[str, Any],
    *,
    secret: str,
    algorithm: str,
    expires_delta: timedelta,
) -> str:
    """Sign a JWT. ``exp`` and ``iat`` are always UTC."""
    now = datetime.now(UTC)
    body = {
        **payload,
        "iat": int(now.timestamp()),
        "exp": int((now + expires_delta).timestamp()),
    }
    return jwt.encode(body, secret, algorithm=algorithm)


def decode_token(token: str, *, secret: str, algorithm: str) -> dict[str, Any]:
    """Decode and validate exp. Raises UnauthorizedError on any failure."""
    try:
        data = jwt.decode(token, secret, algorithms=[algorithm])
    except jwt.PyJWTError as exc:
        logger.info("auth.jwt.invalid", extra={"error_type": type(exc).__name__})
        raise UnauthorizedError("Invalid or expired token") from exc
    if not isinstance(data, dict):
        raise UnauthorizedError("Invalid or expired token")
    return data


def access_payload(
    user_id: UUID,
    email: str,
    merchant_id: UUID | None,
    session_id: UUID,
) -> dict[str, Any]:
    """Claims for a short-lived access token."""
    return {
        "sub": str(user_id),
        "email": email,
        "merchant_id": str(merchant_id) if merchant_id else None,
        "sid": str(session_id),
        "typ": TOKEN_TYPE_ACCESS,
    }


def refresh_payload(user_id: UUID, session_id: UUID) -> dict[str, Any]:
    """Claims for a refresh token bound to ``auth_sessions.id``."""
    return {
        "sub": str(user_id),
        "sid": str(session_id),
        "typ": TOKEN_TYPE_REFRESH,
    }
