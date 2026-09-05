"""JSON helpers that never leak secrets."""

from __future__ import annotations

import json
from typing import Any

_SECRET_KEYS = ("secret", "password", "token", "api_key", "apikey", "gemini", "razorpay")


def dumps(payload: Any) -> str:
    """Serialize ``payload`` to JSON with a stable default."""
    return json.dumps(payload, default=str, separators=(",", ":"))


def redact_mapping(payload: dict[str, Any]) -> dict[str, Any]:
    """Return a copy with secret-like keys replaced by ``***``."""
    redacted: dict[str, Any] = {}
    for key, value in payload.items():
        lowered = key.lower()
        if any(token in lowered for token in _SECRET_KEYS):
            redacted[key] = "***"
        else:
            redacted[key] = value
    return redacted
