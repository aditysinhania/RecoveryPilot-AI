"""HMAC-SHA256 verification for inbound Razorpay webhooks. No HTTP calls."""

from __future__ import annotations

import hashlib
import hmac
import logging

logger = logging.getLogger(__name__)

SIGNATURE_HEADER: str = "X-Razorpay-Signature"


def expected_webhook_signature(body: bytes, secret: str) -> str:
    """Return the hex HMAC-SHA256 of ``body`` using ``secret``.

    Args:
        body: Raw request bytes. Must match what Razorpay signed.
        secret: ``RAZORPAY_WEBHOOK_SECRET``. Never logged.

    Returns:
        Lowercase hex digest.
    """
    key = secret.encode("utf-8")
    return hmac.new(key, body, hashlib.sha256).hexdigest()


def verify_webhook_signature(body: bytes, signature: str, secret: str) -> bool:
    """True when ``signature`` matches HMAC-SHA256(body, secret).

    Args:
        body: Raw webhook bytes.
        signature: Value of ``X-Razorpay-Signature``.
        secret: Webhook secret. Empty secret always fails.

    Returns:
        Whether the signature is valid. Timing-safe compare.
    """
    if not secret or not signature:
        logger.info("razorpay.webhook.signature.rejected", extra={"reason": "missing_secret_or_header"})
        return False
    expected = expected_webhook_signature(body, secret)
    provided = signature.strip()
    if len(provided) != len(expected):
        logger.info("razorpay.webhook.signature.rejected", extra={"reason": "mismatch"})
        return False
    ok = hmac.compare_digest(expected, provided)
    if not ok:
        logger.info("razorpay.webhook.signature.rejected", extra={"reason": "mismatch"})
    return ok
