"""Simulate a Razorpay payment retry. No HTTP."""

from __future__ import annotations

import hashlib
import logging

from services.executor.constants import (
    HIGH_PROBABILITY_SUCCESS,
    LOW_PROBABILITY_FAIL,
    RETRY_OUTCOME_BUCKETS,
)
from services.executor.models import ExecutorContext, RetryOutcome
from services.planner.models import RecoveryPlan

logger = logging.getLogger(__name__)


def _bucket(seed: str) -> int:
    """0–99 from sha256. Same seed always lands in the same bucket."""
    digest = hashlib.sha256(seed.encode("utf-8")).hexdigest()
    return int(digest, 16) % 100


def outcome_for(seed: str) -> RetryOutcome:
    """Map a seed onto simulator-style retry buckets."""
    n = _bucket(seed)
    label = "AUTH_FAILURE"
    for ceiling, name in RETRY_OUTCOME_BUCKETS:
        if n < ceiling:
            label = name
            break
    return RetryOutcome(label)


def simulate_retry(plan: RecoveryPlan, context: ExecutorContext) -> RetryOutcome:
    """Pick a deterministic retry outcome.

    High planner probability forces SUCCESS; very low forces a failure class.
    Mid-range uses the copied simulator bucket table.

    Args:
        plan: Planner output (probability biases the mix).
        context: Case/payment snapshots used as the hash seed.

    Returns:
        One of SUCCESS / FAILED / BANK_TIMEOUT / NSF / AUTH_FAILURE.
    """
    p = plan.expected_recovery_probability
    seed = (
        f"{context.recovery_case_id}:{plan.strategy}:"
        f"{plan.scheduled_at.isoformat()}:{context.payment_id}"
    )
    if p >= HIGH_PROBABILITY_SUCCESS:
        logger.info("executor.retry.outcome", extra={"outcome": "SUCCESS", "probability": p})
        return RetryOutcome.SUCCESS
    if p <= LOW_PROBABILITY_FAIL:
        hashed = outcome_for(seed)
        if hashed == RetryOutcome.SUCCESS:
            hashed = RetryOutcome.FAILED
        logger.info("executor.retry.outcome", extra={"outcome": hashed.value, "probability": p})
        return hashed
    diagnosis = (context.diagnosis or plan.features.get("diagnosis") or "").upper()
    hashed = outcome_for(seed)
    if diagnosis == "INSUFFICIENT_FUNDS" and hashed == RetryOutcome.SUCCESS and p < 0.5:
        return RetryOutcome.NSF
    if diagnosis in {"BANK_TIMEOUT", "UPI_TIMEOUT"} and hashed == RetryOutcome.FAILED:
        return RetryOutcome.BANK_TIMEOUT
    logger.info("executor.retry.outcome", extra={"outcome": hashed.value, "probability": p})
    return hashed
