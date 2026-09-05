"""Deterministic policy orchestrator. No I/O, no side effects."""

from __future__ import annotations

import logging
from collections import Counter
from uuid import UUID

from services.policy.constants import POLICY_VERSION
from services.policy.evaluator import evaluate_rules, fold_decision
from services.policy.models import (
    BatchPolicyResult,
    BatchPolicySummary,
    PolicyContext,
    PolicyDecisionResult,
)

logger = logging.getLogger(__name__)


def evaluate(context: PolicyContext) -> PolicyDecisionResult:
    """Run the registry and fold one compliance decision.

    Args:
        context: Diagnosis plus read-only recovery snapshots.

    Returns:
        A structured ``PolicyDecisionResult``. Nothing is written and no
        recovery action is executed.
    """
    logger.info(
        "policy.start",
        extra={
            "payment_id": str(context.payment.id),
            "recovery_case_id": str(context.recovery_case_id) if context.recovery_case_id else None,
            "diagnosis": context.diagnosis.diagnosis.value,
        },
    )
    results = evaluate_rules(context)
    decision = fold_decision(context, results, policy_version=POLICY_VERSION)
    logger.info(
        "policy.ok",
        extra={
            "payment_id": str(context.payment.id),
            "decision": decision.decision.value,
            "policy_name": decision.policy_name,
            "priority_score": decision.priority_score,
        },
    )
    return decision


def summarize_decisions(results: list[PolicyDecisionResult]) -> BatchPolicySummary:
    """Roll up decision distribution and blocked-channel counts.

    Args:
        results: Per-case engine outputs.

    Returns:
        Dashboard-oriented summary. Does not query the database.
    """
    dist = Counter(item.decision.value for item in results)
    blocked_counts: Counter[str] = Counter()
    for item in results:
        blocked_counts.update(item.blocked_channels)
    return BatchPolicySummary(
        total_cases=len(results),
        decision_distribution=dict(dist),
        stopped_cases=dist.get("STOP", 0),
        escalated_cases=dist.get("ESCALATE", 0),
        waiting_cases=dist.get("WAIT", 0),
        allowed_cases=dist.get("ALLOW", 0),
        denied_cases=dist.get("DENY", 0),
        blocked_channel_counts=dict(blocked_counts),
    )


def evaluate_many(contexts: list[PolicyContext]) -> BatchPolicyResult:
    """Evaluate many in-memory contexts and return a batch summary.

    Args:
        contexts: Independent policy inputs.

    Returns:
        Per-context decisions and an aggregate summary.
    """
    results = [evaluate(item) for item in contexts]
    return BatchPolicyResult(
        results=results,
        missing_case_ids=[],
        summary=summarize_decisions(results),
    )


def evaluate_batch_contexts(
    contexts: list[PolicyContext],
    *,
    missing_case_ids: list[UUID] | None = None,
) -> BatchPolicyResult:
    """Evaluate contexts and attach caller-supplied missing ids.

    Args:
        contexts: Loaded snapshots.
        missing_case_ids: Ids the service could not load.

    Returns:
        Batch result with ``total_cases`` including missing ids.
    """
    batch = evaluate_many(contexts)
    missing = missing_case_ids or []
    summary = batch.summary.model_copy(
        update={"total_cases": len(contexts) + len(missing)}
    )
    return BatchPolicyResult(
        results=batch.results,
        missing_case_ids=missing,
        summary=summary,
    )
