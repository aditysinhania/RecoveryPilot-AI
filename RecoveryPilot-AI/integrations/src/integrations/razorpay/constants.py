"""Razorpay Sandbox HTTP constants. Live (rzp_live_) keys are rejected."""

from __future__ import annotations

SANDBOX_BASE_URL: str = "https://api.razorpay.com/v1"
REQUEST_TIMEOUT_SECONDS: float = 15.0
PAYMENT_LINK_EXPIRE_SECONDS: int = 48 * 60 * 60
MANDATE_SESSION_EXPIRE_SECONDS: int = 24 * 60 * 60

PLACEHOLDER_KEY_IDS: frozenset[str] = frozenset(
    {
        "",
        "rzp_test_placeholder",
        "changeme",
        "your_key_id_here",
    }
)
PLACEHOLDER_SECRETS: frozenset[str] = frozenset(
    {
        "",
        "placeholder_secret",
        "changeme",
        "your_key_secret_here",
    }
)

IDEMPOTENCY_HEADER: str = "X-Razorpay-Idempotency"
TRANSIENT_STATUS_CODES: frozenset[int] = frozenset({408, 409, 429, 500, 502, 503, 504})
