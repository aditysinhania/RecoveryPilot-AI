"""Planner strategy → Razorpay Sandbox action mapping. No HTTP here."""

from __future__ import annotations

from datetime import timedelta

from services.planner.models import PlannerStrategy
from shared.enums import RecoveryActionType

PAYMENT_LINK_TTL: timedelta = timedelta(hours=48)
MANDATE_SESSION_TTL: timedelta = timedelta(hours=24)

STRATEGY_TO_ACTION_TYPE: dict[PlannerStrategy, RecoveryActionType] = {
    PlannerStrategy.RETRY_PAYMENT: RecoveryActionType.RETRY_PAYMENT,
    PlannerStrategy.RETRY_SILENTLY: RecoveryActionType.RETRY_PAYMENT,
    PlannerStrategy.SEND_PAYMENT_LINK: RecoveryActionType.GENERATE_PAYMENT_LINK,
    PlannerStrategy.SWITCH_PAYMENT_METHOD: RecoveryActionType.SWITCH_PAYMENT_METHOD,
    PlannerStrategy.REQUEST_NEW_MANDATE: RecoveryActionType.SWITCH_PAYMENT_METHOD,
    PlannerStrategy.WAIT_FOR_PAYDAY: RecoveryActionType.WAIT_FOR_PAYDAY,
    PlannerStrategy.HONOUR_PROMISE_TO_PAY: RecoveryActionType.PROMISE_TO_PAY,
    PlannerStrategy.ESCALATE_TO_HUMAN: RecoveryActionType.ESCALATE_TO_AGENT,
    PlannerStrategy.STOP_RECOVERY: RecoveryActionType.STOP_RECOVERY,
}

RAZORPAY_STRATEGIES: frozenset[PlannerStrategy] = frozenset(
    {
        PlannerStrategy.RETRY_PAYMENT,
        PlannerStrategy.RETRY_SILENTLY,
        PlannerStrategy.SEND_PAYMENT_LINK,
        PlannerStrategy.SWITCH_PAYMENT_METHOD,
        PlannerStrategy.REQUEST_NEW_MANDATE,
    }
)

WAIT_STRATEGIES: frozenset[PlannerStrategy] = frozenset(
    {
        PlannerStrategy.WAIT_FOR_PAYDAY,
        PlannerStrategy.HONOUR_PROMISE_TO_PAY,
    }
)
