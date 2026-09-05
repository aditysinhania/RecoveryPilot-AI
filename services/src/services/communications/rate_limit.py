"""In-memory token buckets for sandbox communication adapters."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from threading import Lock

from services.communications.constants import RATE_LIMITS, RATE_WINDOW

logger = logging.getLogger(__name__)


class RateLimiter:
    """Per merchant+channel token bucket. Process-local; not shared across workers."""

    def __init__(self, limits: dict[str, int] | None = None) -> None:
        self._limits = limits or RATE_LIMITS
        self._lock = Lock()
        self._buckets: dict[str, tuple[float, datetime]] = {}

    def allow(self, *, merchant_key: str, channel: str) -> bool:
        """Consume one token. False when the bucket is empty.

        Args:
            merchant_key: Merchant id or ``global`` when unknown.
            channel: SMS / WhatsApp / Email.

        Returns:
            True when the send may proceed.
        """
        cap = self._limits.get(channel, 10)
        key = f"{merchant_key}:{channel}"
        now = datetime.now(UTC)
        with self._lock:
            tokens, refreshed = self._buckets.get(key, (float(cap), now))
            elapsed = (now - refreshed).total_seconds()
            refill = elapsed / RATE_WINDOW.total_seconds() * cap
            tokens = min(float(cap), tokens + refill)
            if tokens < 1:
                logger.info(
                    "comms.rate_limited",
                    extra={"channel": channel, "merchant_key": merchant_key},
                )
                self._buckets[key] = (tokens, now)
                return False
            self._buckets[key] = (tokens - 1, now)
            return True
