"""Process-local TTL cache for Gemini explanations. No Redis, no database."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import Any

from integrations.gemini.constants import CACHE_TTL

logger = logging.getLogger(__name__)


class ExplanationCache:
    """In-memory cache keyed by case + type + planner/policy versions."""

    def __init__(self) -> None:
        self._rows: dict[str, tuple[datetime, dict[str, Any]]] = {}

    def make_key(
        self,
        case_id: str,
        explanation_type: str,
        planner_version: str,
        policy_version: str,
    ) -> str:
        """Stable cache key. Same inputs always collide."""
        return f"{case_id}:{explanation_type}:{planner_version}:{policy_version}"

    def get(self, key: str) -> dict[str, Any] | None:
        """Return a stored payload if present and unexpired."""
        row = self._rows.get(key)
        if row is None:
            return None
        expires_at, payload = row
        if datetime.now(UTC) >= expires_at:
            self._rows.pop(key, None)
            logger.info("gemini.cache.expired", extra={"key": key})
            return None
        logger.info("gemini.cache.hit", extra={"key": key})
        return dict(payload)

    def set(self, key: str, payload: dict[str, Any]) -> None:
        """Store a JSON-serializable explanation for 24 hours."""
        expires_at = datetime.now(UTC) + CACHE_TTL
        self._rows[key] = (expires_at, dict(payload))
        logger.info("gemini.cache.set", extra={"key": key})

    def clear(self) -> None:
        """Drop every entry. Used by tests."""
        self._rows.clear()


_CACHE = ExplanationCache()


def get_explanation_cache() -> ExplanationCache:
    """Process-wide explanation cache singleton."""
    return _CACHE
