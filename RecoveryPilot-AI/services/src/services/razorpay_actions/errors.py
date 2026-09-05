"""Domain errors for Razorpay action mapping. No HTTP types leak into callers."""

from __future__ import annotations


class RazorpayActionError(Exception):
    """Sandbox action failed."""


class RazorpayActionTransientError(RazorpayActionError):
    """Retryable Sandbox failure (timeout, 429, 5xx)."""


class RazorpayActionPermanentError(RazorpayActionError):
    """Non-retryable Sandbox failure."""
