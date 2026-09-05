"""Apply mapped Razorpay events onto recovery_cases through the orchestrator path."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from sqlalchemy.orm import Session

from database.models import RecoveryCase
from services.razorpay_webhooks.constants import (
    CAPTURE_EVENTS,
    EVENT_PAYMENT_AUTHORIZED,
    EVENT_PAYMENT_FAILED,
    STOP_EVENTS,
)
from shared.enums import PaymentStatus, RecoveryStatus

logger = logging.getLogger(__name__)


def apply_recovery_status(
    db: Session | None,
    recovery_case_id: UUID,
    provider_event: str,
    *,
    as_of: datetime,
) -> RecoveryStatus | None:
    """Update ``recovery_status`` (and payment ledger) for a mapped webhook.

    Planner, diagnosis, and policy engines are not invoked. ``db`` is omitted
    in unit tests that only exercise the action store.

    Args:
        db: Session owning the case row.
        recovery_case_id: Mapped case.
        provider_event: Razorpay event name.
        as_of: Webhook clock.

    Returns:
        The status written, or ``None`` when the case is missing / no-op.
    """
    if db is None:
        return _status_for_event(provider_event)
    case = db.get(RecoveryCase, recovery_case_id)
    if case is None:
        logger.info("webhook.case.missing", extra={"recovery_case_id": str(recovery_case_id)})
        return None
    status = _status_for_event(provider_event)
    if status is None:
        return None
    case.recovery_status = status
    if status in {RecoveryStatus.RECOVERED, RecoveryStatus.STOPPED, RecoveryStatus.CLOSED}:
        case.recovery_completed_at = as_of
    payment = case.payment
    if payment is not None:
        if provider_event in CAPTURE_EVENTS:
            payment.payment_status = PaymentStatus.RECOVERED
            payment.paid_at = as_of
        elif provider_event == EVENT_PAYMENT_FAILED:
            payment.payment_status = PaymentStatus.FAILED
        elif provider_event == EVENT_PAYMENT_AUTHORIZED:
            payment.payment_status = PaymentStatus.AUTHORIZED
        elif provider_event in STOP_EVENTS:
            payment.payment_status = PaymentStatus.CANCELLED
    db.flush()
    logger.info(
        "webhook.case.status",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "recovery_status": status.value,
            "event": provider_event,
        },
    )
    return status


def _status_for_event(provider_event: str) -> RecoveryStatus | None:
    """Map a Razorpay event onto RecoveryStatus. None means leave the case as-is."""
    if provider_event in CAPTURE_EVENTS:
        return RecoveryStatus.RECOVERED
    if provider_event in STOP_EVENTS:
        return RecoveryStatus.STOPPED
    if provider_event == EVENT_PAYMENT_FAILED:
        return RecoveryStatus.WAITING_RETRY
    if provider_event == EVENT_PAYMENT_AUTHORIZED:
        return RecoveryStatus.WAITING_RETRY
    return None
