"""Policy cooldown and blocked-channel gates. Does not change the policy engine."""

from __future__ import annotations

import logging
from datetime import datetime

from services.action_orchestrator.models import GateDecision
from services.planner.models import PlannerStrategy, RecoveryPlan
from services.policy.models import PolicyDecision, PolicyDecisionResult
from services.razorpay_actions.constants import WAIT_STRATEGIES

logger = logging.getLogger(__name__)

_BLOCK_DECISIONS = frozenset({PolicyDecision.DENY, PolicyDecision.STOP})


def evaluate_gates(
    plan: RecoveryPlan,
    policy: PolicyDecisionResult,
    *,
    as_of: datetime,
    force_schedule: bool = False,
) -> GateDecision:
    """Decide whether to execute now, defer, or skip.

    Args:
        plan: Existing planner output. Not modified.
        policy: Existing policy output. Not modified.
        as_of: Orchestrator clock.
        force_schedule: When True, always defer to ``plan.scheduled_at``.

    Returns:
        GateDecision consumed by the orchestrator before any Razorpay call.
    """
    blocked = list(policy.blocked_channels or [])
    if policy.decision in _BLOCK_DECISIONS:
        logger.info(
            "orchestrator.gate.block",
            extra={
                "decision": policy.decision.value,
                "recovery_case_id": str(plan.recovery_case_id),
            },
        )
        return GateDecision(
            allow_now=False,
            block=True,
            reason=policy.reason,
            blocked_channels=blocked,
        )
    if policy.decision == PolicyDecision.ESCALATE and plan.strategy != PlannerStrategy.ESCALATE_TO_HUMAN:
        return GateDecision(
            allow_now=False,
            block=True,
            reason=policy.reason or "Policy escalated this case",
            blocked_channels=blocked,
        )
    run_at = plan.scheduled_at
    cooldown = policy.cooldown_until
    if cooldown is not None and cooldown > as_of:
        run_at = max(run_at, cooldown) if run_at else cooldown
        logger.info(
            "orchestrator.gate.cooldown",
            extra={"recovery_case_id": str(plan.recovery_case_id)},
        )
        return GateDecision(
            allow_now=False,
            defer=True,
            reason="POLICY_COOLDOWN",
            run_at=run_at,
            blocked_channels=blocked,
        )
    if policy.decision == PolicyDecision.WAIT:
        wait_until = cooldown or plan.scheduled_at
        if wait_until > as_of:
            return GateDecision(
                allow_now=False,
                defer=True,
                reason="POLICY_WAIT",
                run_at=wait_until,
                blocked_channels=blocked,
            )
    if force_schedule or (
        plan.strategy in WAIT_STRATEGIES and plan.scheduled_at > as_of
    ):
        return GateDecision(
            allow_now=False,
            defer=True,
            reason=plan.strategy.value,
            run_at=plan.scheduled_at,
            blocked_channels=blocked,
        )
    return GateDecision(
        allow_now=True,
        reason="ALLOW",
        run_at=plan.scheduled_at if plan.scheduled_at > as_of else as_of,
        blocked_channels=blocked,
    )
