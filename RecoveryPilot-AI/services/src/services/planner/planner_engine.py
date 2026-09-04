"""Deterministic planner orchestrator. No I/O, no side effects."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime
from uuid import UUID

from services.planner.channels import plan_channels
from services.planner.constants import (
    EXPECTED_OUTCOME,
    PLAN_VERSION,
    PLANNER_VERSION,
    POLICY_DECISION_STRENGTH,
    SEGMENT_PROBABILITY,
    STRATEGY_CONFIDENCE_DIAGNOSIS_WEIGHT,
    STRATEGY_CONFIDENCE_HISTORY_WEIGHT,
    STRATEGY_CONFIDENCE_POLICY_WEIGHT,
    STRATEGY_CONFIDENCE_TIMING_WEIGHT,
)
from services.planner.models import (
    BatchPlannerResult,
    BatchPlannerSummary,
    PlannerContext,
    PlannerStrategy,
    RecoveryPlan,
    ScheduleResult,
    StrategyChoice,
)
from services.planner.scheduler import schedule
from services.planner.strategies import select_strategy

logger = logging.getLogger(__name__)

_RETRY_STRATEGIES = frozenset(
    {
        PlannerStrategy.RETRY_PAYMENT,
        PlannerStrategy.RETRY_SILENTLY,
        PlannerStrategy.WAIT_FOR_PAYDAY,
    }
)


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp ``value`` into ``[lo, hi]``."""
    return max(lo, min(hi, value))


def estimate_probability(context: PlannerContext, strategy: PlannerStrategy) -> float:
    """Deterministic recovery probability from diagnosis and behaviour.

    Args:
        context: Planner snapshots.
        strategy: Chosen primary strategy.

    Returns:
        Probability in ``[0, 1]``. No ML.
    """
    if strategy == PlannerStrategy.STOP_RECOVERY:
        return 0.0
    if strategy == PlannerStrategy.ESCALATE_TO_HUMAN:
        base = 0.22
    else:
        base = 0.18
    score = base
    score += 0.40 * context.diagnosis.confidence
    score += 0.16 * _clamp(context.behaviour.previous_success_rate, 0.0, 1.0)
    if context.customer.salary_dependent and strategy == PlannerStrategy.WAIT_FOR_PAYDAY:
        score += 0.10
    score += SEGMENT_PROBABILITY.get(context.customer.segment.value, 0.02)
    score -= 0.08 * min(context.retry_count, 3) / 3.0
    if context.subscription_age_days >= 90:
        score += 0.05
    if context.behaviour.max_fail_streak >= 2:
        score -= 0.06
    return round(_clamp(score, 0.05, 0.95), 4)


def _timing_certainty(
    context: PlannerContext,
    strategy: PlannerStrategy,
    timed: ScheduleResult,
) -> tuple[float, str]:
    """How sure the schedule is, given strategy and known clocks."""
    if strategy == PlannerStrategy.STOP_RECOVERY:
        return 0.98, "stop is immediate"
    if strategy == PlannerStrategy.HONOUR_PROMISE_TO_PAY and context.promised_date is not None:
        return 0.92, f"promised date {context.promised_date.isoformat()} is exact"
    if strategy == PlannerStrategy.WAIT_FOR_PAYDAY:
        if context.customer.salary_dependent:
            return 0.88, "payday 09:15 IST slot is fixed"
        return 0.70, "payday slot without a salary-dependent flag"
    if strategy == PlannerStrategy.RETRY_SILENTLY:
        if context.outage_ended_at is not None:
            return 0.86, "outage end is known; +60 minute silent retry"
        return 0.58, "outage end inferred from as_of"
    if context.policy.cooldown_until is not None:
        return 0.80, "policy cooldown_until anchors the schedule"
    if timed.retry_window is not None:
        return 0.72, "inside a defined retry window"
    return 0.64, "next business contact window"


def estimate_strategy_confidence(
    context: PlannerContext,
    choice: StrategyChoice,
    timed: ScheduleResult,
) -> tuple[float, str]:
    """Confidence that the chosen strategy is the right one (0–1). Distinct from recovery probability.

    Weighted sum of diagnosis confidence, policy decision strength, payment
    history, and timing certainty. No ML.

    Args:
        context: Planner snapshots.
        choice: Selected primary strategy and steps.
        timed: Timing engine output.

    Returns:
        Confidence in ``[0, 1]`` and a human-readable explanation.
    """
    diagnosis_c = _clamp(context.diagnosis.confidence, 0.0, 1.0)
    policy_c = POLICY_DECISION_STRENGTH.get(context.policy.decision.value, 0.70)
    if context.policy.decision.value == "WAIT" and context.policy.cooldown_until is not None:
        policy_c = min(1.0, policy_c + 0.05)
    history_c = _clamp(
        context.behaviour.previous_success_rate
        if context.behaviour.previous_success_rate is not None
        else context.behaviour.observed_reliability,
        0.0,
        1.0,
    )
    timing_c, timing_hint = _timing_certainty(context, choice.strategy, timed)
    score = (
        STRATEGY_CONFIDENCE_DIAGNOSIS_WEIGHT * diagnosis_c
        + STRATEGY_CONFIDENCE_POLICY_WEIGHT * policy_c
        + STRATEGY_CONFIDENCE_HISTORY_WEIGHT * history_c
        + STRATEGY_CONFIDENCE_TIMING_WEIGHT * timing_c
    )
    confidence = round(_clamp(score, 0.05, 0.99), 4)
    why = choice.steps[-1].rstrip(".") if choice.steps else f"{choice.strategy.value} selected"
    reasoning = (
        f"{why}. Strategy confidence {confidence:.2f} from diagnosis "
        f"{diagnosis_c:.2f}, policy {context.policy.decision.value} strength "
        f"{policy_c:.2f}, prior success rate {history_c:.0%}, and timing "
        f"certainty {timing_c:.2f} ({timing_hint})."
    )
    return confidence, reasoning


def plan(context: PlannerContext) -> RecoveryPlan:
    """Build one RecoveryPlan from diagnosis + policy + customer context.

    Args:
        context: Read-only planner snapshots.

    Returns:
        A structured plan. Nothing is executed or persisted.
    """
    logger.info(
        "planner.start",
        extra={
            "payment_id": str(context.diagnosis.payment_id) if context.diagnosis.payment_id else None,
            "diagnosis": context.diagnosis.diagnosis.value,
            "policy": context.policy.decision.value,
        },
    )
    choice = select_strategy(context)
    timed = schedule(choice.strategy, context)
    channels = plan_channels(choice.strategy, context.policy)
    probability = estimate_probability(context, choice.strategy)
    strategy_confidence, confidence_reasoning = estimate_strategy_confidence(
        context, choice, timed
    )
    value = int(round(context.payment_amount * probability))
    evidence = list(dict.fromkeys(
        [item.code for item in context.diagnosis.evidence_items if item.code]
        + list(context.policy.evidence_codes)
        + list(context.diagnosis.triggered_rules)
    ))
    policy_rules = list(context.policy.triggered_policies)
    if not policy_rules:
        policy_rules = [
            row.policy_name
            for row in context.policy.evaluated_rules
            if row.result.value != "PASS"
        ]
    reasoning = timed.timing_reason
    if choice.steps:
        reasoning = f"{choice.steps[-1]} {timed.timing_reason}"
    result = RecoveryPlan(
        strategy=choice.strategy,
        scheduled_at=timed.scheduled_at,
        reasoning=reasoning,
        recommended_channels=channels.recommended,
        fallback_strategy=choice.fallback,
        expected_outcome=EXPECTED_OUTCOME[choice.strategy.value],
        expected_recovery_probability=probability,
        strategy_confidence=strategy_confidence,
        confidence_reasoning=confidence_reasoning,
        estimated_recovery_value=value,
        estimated_cost=channels.cost_paise,
        plan_version=PLAN_VERSION,
        planner_version=PLANNER_VERSION,
        generated_at=datetime.now(UTC),
        retry_window=timed.retry_window,
        expires_at=timed.expires_at,
        reasoning_steps=choice.steps,
        evidence_codes_used=evidence,
        policy_rules_used=policy_rules,
        timing_reason=timed.timing_reason,
        channel_reason=channels.channel_reason,
        recovery_case_id=context.recovery_case_id or context.diagnosis.recovery_case_id,
        payment_id=context.diagnosis.payment_id,
        features={
            "diagnosis": context.diagnosis.diagnosis.value,
            "policy_decision": context.policy.decision.value,
            "salary_dependent": context.customer.salary_dependent,
            "payment_amount": context.payment_amount,
        },
    )
    logger.info(
        "planner.ok",
        extra={
            "strategy": result.strategy.value,
            "scheduled_at": result.scheduled_at.isoformat(),
            "probability": result.expected_recovery_probability,
            "strategy_confidence": result.strategy_confidence,
            "estimated_recovery_value": result.estimated_recovery_value,
        },
    )
    return result


def summarize_plans(results: list[RecoveryPlan]) -> BatchPlannerSummary:
    """Roll up strategy mix, channels, recovery value, and comms cost.

    Args:
        results: Per-case planner outputs.

    Returns:
        Dashboard-oriented summary. Does not query the database.
    """
    dist = Counter(item.strategy.value for item in results)
    channels: Counter[str] = Counter()
    for item in results:
        channels.update(item.recommended_channels)
    recovery = sum(item.estimated_recovery_value for item in results)
    cost = sum(item.estimated_cost for item in results)
    retries = sum(1 for item in results if item.strategy in _RETRY_STRATEGIES)
    return BatchPlannerSummary(
        total_cases=len(results),
        strategy_distribution=dict(dist),
        scheduled_retries=retries,
        channel_usage=dict(channels),
        estimated_recovery_value=recovery,
        estimated_communication_cost=cost,
        expected_recovered_revenue=recovery,
    )


def plan_many(contexts: list[PlannerContext]) -> BatchPlannerResult:
    """Plan many in-memory contexts and return a batch summary."""
    results = [plan(item) for item in contexts]
    return BatchPlannerResult(
        results=results,
        missing_case_ids=[],
        summary=summarize_plans(results),
    )


def plan_batch_contexts(
    contexts: list[PlannerContext],
    *,
    missing_case_ids: list[UUID] | None = None,
) -> BatchPlannerResult:
    """Plan contexts and attach caller-supplied missing ids."""
    batch = plan_many(contexts)
    missing = missing_case_ids or []
    summary = batch.summary.model_copy(
        update={"total_cases": len(contexts) + len(missing)}
    )
    return BatchPlannerResult(
        results=batch.results,
        missing_case_ids=missing,
        summary=summary,
    )
