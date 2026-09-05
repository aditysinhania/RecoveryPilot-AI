"""Razorpay Sandbox adapter errors. Never include secrets in messages."""

from __future__ import annotations


class RazorpayError(Exception):
    """Raised when a Razorpay Sandbox call cannot complete."""

    def __init__(self, message: str, *, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


class RazorpayLiveKeyError(RazorpayError):
    """Raised when a live key is supplied. Phase 9B is sandbox-only."""


class RazorpayTransientError(RazorpayError):
    """Timeouts and 5xx/429 responses that the orchestrator may retry."""


class RazorpayPermanentError(RazorpayError):
    """4xx responses that must not be retried."""
