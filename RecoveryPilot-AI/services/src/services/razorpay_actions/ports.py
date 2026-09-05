"""Port the orchestrator uses for Razorpay Sandbox. Implemented in integrations."""

from __future__ import annotations

from typing import Any, Protocol

from services.razorpay_actions.models import RazorpayActionRequest, RazorpayActionResult


class RazorpayActionsPort(Protocol):
    """Create payment links, retry orders, and mandate/card-update sessions."""

    def create_payment_link(self, request: RazorpayActionRequest) -> RazorpayActionResult:
        """Create a Razorpay Payment Link in Sandbox."""
        ...

    def retry_payment(self, request: RazorpayActionRequest) -> RazorpayActionResult:
        """Submit a retry payment (order) in Sandbox."""
        ...

    def create_mandate_session(self, request: RazorpayActionRequest) -> RazorpayActionResult:
        """Create a hosted mandate/card-update session in Sandbox."""
        ...


class RazorpayHttpPort(Protocol):
    """Low-level dict client. ``integrations.razorpay.RazorpaySandboxClient`` matches this."""

    def create_payment_link(
        self, payload: dict[str, Any], *, idempotency_key: str
    ) -> Any:
        """POST payment links."""
        ...

    def create_order(self, payload: dict[str, Any], *, idempotency_key: str) -> Any:
        """POST orders (retry)."""
        ...

    def create_mandate_session(
        self, payload: dict[str, Any], *, idempotency_key: str
    ) -> Any:
        """POST mandate/card-update session."""
        ...
