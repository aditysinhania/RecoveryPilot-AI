"""Supported Razorpay webhook event types and ingest keys."""

from __future__ import annotations

INGEST_KEY: str = "_rp_ingest"

EVENT_PAYMENT_FAILED: str = "payment.failed"
EVENT_PAYMENT_CAPTURED: str = "payment.captured"
EVENT_PAYMENT_AUTHORIZED: str = "payment.authorized"
EVENT_PAYMENT_LINK_PAID: str = "payment_link.paid"
EVENT_SUBSCRIPTION_CHARGED: str = "subscription.charged"
EVENT_SUBSCRIPTION_CANCELLED: str = "subscription.cancelled"
EVENT_SUBSCRIPTION_PAUSED: str = "subscription.paused"

SUPPORTED_EVENTS: frozenset[str] = frozenset(
    {
        EVENT_PAYMENT_FAILED,
        EVENT_PAYMENT_CAPTURED,
        EVENT_PAYMENT_AUTHORIZED,
        EVENT_PAYMENT_LINK_PAID,
        EVENT_SUBSCRIPTION_CHARGED,
        EVENT_SUBSCRIPTION_CANCELLED,
        EVENT_SUBSCRIPTION_PAUSED,
    }
)

CAPTURE_EVENTS: frozenset[str] = frozenset(
    {EVENT_PAYMENT_CAPTURED, EVENT_PAYMENT_LINK_PAID, EVENT_SUBSCRIPTION_CHARGED}
)
STOP_EVENTS: frozenset[str] = frozenset({EVENT_SUBSCRIPTION_CANCELLED, EVENT_SUBSCRIPTION_PAUSED})

WEBHOOK_ACTOR: str = "Razorpay Webhook"
DISPLAY_WEBHOOK_REPLAY: str = "WEBHOOK_REPLAY"
