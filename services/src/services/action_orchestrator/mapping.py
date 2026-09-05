"""Display status, queue chips, and DB ExecutionStatus mapping. No new PG enums."""

from __future__ import annotations

from typing import Any

from services.action_orchestrator.constants import (
    CHIP_DELIVERED,
    CHIP_FAILED,
    CHIP_LINK_SENT,
    CHIP_RETRYING,
    CHIP_SCHEDULED,
    DISPLAY_CANCELLED,
    DISPLAY_EXPIRED,
    DISPLAY_FAILED,
    DISPLAY_RETRYING,
    DISPLAY_SCHEDULED,
    DISPLAY_SENT,
    DISPLAY_SUCCESS,
)
from services.planner.models import PlannerStrategy
from services.razorpay_actions.constants import STRATEGY_TO_ACTION_TYPE
from shared.enums import ExecutionStatus, RecoveryActionType


def action_type_for(strategy: PlannerStrategy) -> RecoveryActionType:
    """Map a planner strategy onto an existing RecoveryActionType."""
    return STRATEGY_TO_ACTION_TYPE.get(strategy, RecoveryActionType.NO_ACTION)


def db_status_for(display: str) -> ExecutionStatus:
    """Persist display lifecycle onto the existing ExecutionStatus enum."""
    mapping = {
        DISPLAY_SCHEDULED: ExecutionStatus.SCHEDULED,
        DISPLAY_SENT: ExecutionStatus.RUNNING,
        DISPLAY_SUCCESS: ExecutionStatus.SUCCEEDED,
        DISPLAY_FAILED: ExecutionStatus.FAILED,
        DISPLAY_CANCELLED: ExecutionStatus.CANCELLED,
        DISPLAY_EXPIRED: ExecutionStatus.SKIPPED,
        DISPLAY_RETRYING: ExecutionStatus.SCHEDULED,
    }
    return mapping.get(display, ExecutionStatus.SCHEDULED)


def display_status_for(metadata: dict[str, Any], execution_status: ExecutionStatus) -> str:
    """Compute the merchant-facing lifecycle label from row status + metadata."""
    if metadata.get("dead_lettered"):
        return DISPLAY_FAILED
    if metadata.get("expired"):
        return DISPLAY_EXPIRED
    stored = metadata.get("display_status")
    if isinstance(stored, str) and stored:
        return stored
    reverse = {
        ExecutionStatus.SCHEDULED: DISPLAY_SCHEDULED,
        ExecutionStatus.RUNNING: DISPLAY_SENT,
        ExecutionStatus.SUCCEEDED: DISPLAY_SUCCESS,
        ExecutionStatus.FAILED: DISPLAY_FAILED,
        ExecutionStatus.SKIPPED: DISPLAY_EXPIRED,
        ExecutionStatus.CANCELLED: DISPLAY_CANCELLED,
    }
    return reverse.get(execution_status, DISPLAY_SCHEDULED)


def action_chip_for(
    display: str,
    action_type: RecoveryActionType | str,
    *,
    payment_link: str | None = None,
) -> str:
    """Queue chip: Scheduled, Link Sent, Retrying, Delivered, Failed."""
    kind = action_type.value if isinstance(action_type, RecoveryActionType) else str(action_type)
    if display == DISPLAY_RETRYING:
        return CHIP_RETRYING
    if display in {DISPLAY_FAILED, DISPLAY_EXPIRED, DISPLAY_CANCELLED}:
        return CHIP_FAILED
    if display == DISPLAY_SUCCESS:
        return CHIP_DELIVERED
    if display == DISPLAY_SENT:
        if kind == RecoveryActionType.GENERATE_PAYMENT_LINK.value or payment_link:
            return CHIP_LINK_SENT
        if kind == RecoveryActionType.RETRY_PAYMENT.value:
            return CHIP_RETRYING
        if payment_link:
            return CHIP_LINK_SENT
        return CHIP_RETRYING
    if display == DISPLAY_SCHEDULED:
        return CHIP_SCHEDULED
    return CHIP_SCHEDULED
