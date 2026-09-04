"""Deterministic payment-link and card-update session generators. No HTTP."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID, uuid5

from services.executor.constants import (
    CARD_UPDATE_TTL,
    IDEMPOTENCY_NAMESPACE,
    PAYMENT_LINK_TTL,
)
from services.executor.models import ExecutorContext
from shared.enums import PaymentMethod

logger = logging.getLogger(__name__)


def _short_token(kind: str, seed: str) -> str:
    """Razorpay-like public id fragment."""
    hexed = uuid5(IDEMPOTENCY_NAMESPACE, f"{kind}:{seed}").hex
    return hexed[:14]


def payment_link_id(context: ExecutorContext) -> str:
    """Stable ``plink_`` id for this case and schedule."""
    seed = f"{context.recovery_case_id}:{context.plan.scheduled_at.isoformat()}"
    return f"plink_{_short_token('plink', seed)}"


def card_session_id(context: ExecutorContext) -> str:
    """Stable card-update session id."""
    seed = f"{context.recovery_case_id}:{context.plan.scheduled_at.isoformat()}:card"
    return f"cs_{_short_token('card', seed)}"


def generate_payment_link(
    context: ExecutorContext,
    *,
    method: PaymentMethod | None = None,
    as_of: datetime,
) -> dict[str, object]:
    """Build a hosted payment-link payload. Status GENERATED; 48h expiry.

    Args:
        context: Executor snapshots.
        method: Instrument advertised on the link.
        as_of: Clock used for expiry.

    Returns:
        Link id, expiry, method, merchant reference, and status.
    """
    link_id = payment_link_id(context)
    case = context.recovery_case_id or UUID(int=0)
    instrument = method or context.payment_method or PaymentMethod.UPI
    expires = as_of + PAYMENT_LINK_TTL
    logger.info(
        "executor.payment_link.generated",
        extra={"payment_link_id": link_id, "amount": context.payment_amount},
    )
    return {
        "payment_link_id": link_id,
        "expires_at": expires,
        "payment_method": instrument.value,
        "merchant_reference": f"rp-{case}:{context.plan.strategy}",
        "status": "GENERATED",
        "url": f"https://rzp.io/i/{link_id[6:]}",
    }


def generate_card_update_session(
    context: ExecutorContext,
    *,
    as_of: datetime,
) -> dict[str, object]:
    """Build a card-update session. No real Razorpay checkout.

    Args:
        context: Executor snapshots.
        as_of: Clock used for expiry.

    Returns:
        Session id, expiry, and status.
    """
    session_id = card_session_id(context)
    expires = as_of + CARD_UPDATE_TTL
    expired = as_of >= expires
    logger.info(
        "executor.card_update.generated",
        extra={"update_session_id": session_id, "status": "EXPIRED" if expired else "CREATED"},
    )
    return {
        "update_session_id": session_id,
        "expires_at": expires,
        "status": "EXPIRED" if expired else "CREATED",
        "payment_method": PaymentMethod.CARD.value,
    }


def link_is_expired(expires_at: datetime, as_of: datetime) -> bool:
    """True when ``as_of`` is at or after the link expiry."""
    return as_of >= expires_at
