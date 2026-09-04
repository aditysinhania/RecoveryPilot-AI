"""Simulate Razorpay webhook delivery and replay. No HTTP, no DB inbox."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import uuid5

from services.executor.constants import IDEMPOTENCY_NAMESPACE, RETRY_WEBHOOK
from services.executor.execution_log import ExecutionLogStore
from services.executor.models import ExecutorContext, RetryOutcome, SimulatedWebhookEvent

logger = logging.getLogger(__name__)

SUPPORTED_EVENTS: tuple[str, ...] = (
    "payment.authorized",
    "payment.captured",
    "payment.failed",
    "subscription.charged",
    "subscription.pending",
    "subscription.halted",
    "payment_link.paid",
)


def webhook_event_id(event_type: str, context: ExecutorContext, index: int) -> str:
    """Stable ``evt_`` id so replays share the provider event id."""
    seed = (
        f"{context.recovery_case_id}:{context.plan.scheduled_at.isoformat()}:"
        f"{event_type}:{index}"
    )
    return f"evt_{uuid5(IDEMPOTENCY_NAMESPACE, seed).hex[:16]}"


def build_webhooks(
    context: ExecutorContext,
    *,
    event_types: tuple[str, ...],
    created_at: datetime,
    extra: dict[str, object] | None = None,
) -> list[SimulatedWebhookEvent]:
    """Create normalized webhook events for this execution."""
    body = {
        "payment_id": str(context.payment_id) if context.payment_id else None,
        "amount": context.payment_amount,
        "method": context.payment_method.value if context.payment_method else None,
        **(extra or {}),
    }
    rows: list[SimulatedWebhookEvent] = []
    for index, event_type in enumerate(event_types):
        rows.append(
            SimulatedWebhookEvent(
                event_id=webhook_event_id(event_type, context, index),
                event_type=event_type,
                payload={"event": event_type, "payload": body},
                replay=False,
                created_at=created_at,
            )
        )
    return rows


def webhooks_for_retry(
    context: ExecutorContext,
    outcome: RetryOutcome,
    created_at: datetime,
) -> list[SimulatedWebhookEvent]:
    """Map a retry outcome onto payment.authorized / captured / failed."""
    types = RETRY_WEBHOOK.get(outcome.value, ("payment.failed",))
    extra: dict[str, str] = {"retry_outcome": outcome.value}
    if outcome == RetryOutcome.SUCCESS:
        extra["status"] = "captured"
    return build_webhooks(context, event_types=types, created_at=created_at, extra=extra)


def process_webhooks(
    events: list[SimulatedWebhookEvent],
    store: ExecutionLogStore,
) -> list[SimulatedWebhookEvent]:
    """Mark duplicates as replay. First delivery of an event_id wins.

    Args:
        events: Newly generated events.
        store: In-memory webhook id ledger.

    Returns:
        Same events with ``replay`` set when the id was already seen.
    """
    processed: list[SimulatedWebhookEvent] = []
    for event in events:
        replay = store.seen_webhook(event.event_id)
        if not replay:
            store.remember_webhook(event.event_id)
        processed.append(event.model_copy(update={"replay": replay}))
    replays = sum(1 for item in processed if item.replay)
    logger.info(
        "executor.webhooks.processed",
        extra={"count": len(processed), "replays": replays},
    )
    return processed
