"""Map a Razorpay event onto an existing recovery case. No new FKs."""

from __future__ import annotations

import logging
from typing import Any
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Payment, RecoveryAction, RecoveryCase
from services.razorpay_webhooks.mapping import (
    case_id_from_notes,
    order_provider_id,
    payment_link_id,
    payment_provider_id,
    subscription_provider_id,
)

logger = logging.getLogger(__name__)


def resolve_recovery_case_id(db: Session | None, body: dict[str, Any]) -> UUID | None:
    """Find the case using notes, payment ids, order ids, or action resource ids.

    Args:
        db: Request session. ``None`` uses notes only (unit tests).
        body: Razorpay event JSON.

    Returns:
        Recovery case UUID, or ``None`` when nothing matches.
    """
    from_notes = case_id_from_notes(body)
    if db is None:
        return from_notes
    if from_notes is not None and db.get(RecoveryCase, from_notes) is not None:
        return from_notes
    pay_id = payment_provider_id(body)
    if pay_id:
        payment = db.scalar(select(Payment).where(Payment.razorpay_payment_id == pay_id))
        case_id = _case_for_payment(db, payment)
        if case_id is not None:
            return case_id
    order_id = order_provider_id(body)
    if order_id:
        payment = db.scalar(select(Payment).where(Payment.razorpay_order_id == order_id))
        case_id = _case_for_payment(db, payment)
        if case_id is not None:
            return case_id
    tokens = [
        token
        for token in (pay_id, order_id, payment_link_id(body), subscription_provider_id(body))
        if token
    ]
    for token in tokens:
        linked = db.scalar(select(RecoveryAction).where(RecoveryAction.razorpay_payment_link.contains(token)))
        if linked is not None:
            return linked.recovery_case_id
        matched = db.scalar(
            select(RecoveryAction).where(
                RecoveryAction.action_metadata["razorpay_resource_id"].as_string() == token
            )
        )
        if matched is not None:
            return matched.recovery_case_id
    logger.info("webhook.case.unmapped", extra={"event": str(body.get("event") or "")})
    return None


def _case_for_payment(db: Session, payment: Payment | None) -> UUID | None:
    """Return the unique case for a payment row."""
    if payment is None:
        return None
    case = db.scalar(select(RecoveryCase).where(RecoveryCase.payment_id == payment.id))
    return case.id if case is not None else None
