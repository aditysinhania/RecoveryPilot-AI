"""Fold independent rule verdicts into one policy decision."""

from __future__ import annotations

from collections.abc import Sequence

from services.policy.consent import split_channels
from services.policy.constants import CHANNELS, DECISION_PRIORITY, POLICY_PRECEDENCE
from services.policy.models import (
    EvaluatedRule,
    PolicyContext,
    PolicyDecision,
    PolicyDecisionResult,
    PolicyRuleResult,
    RuleVerdict,
)
from services.policy.registry import iter_policies

_VERDICT_TO_DECISION: dict[RuleVerdict, PolicyDecision] = {
    RuleVerdict.STOP: PolicyDecision.STOP,
    RuleVerdict.ESCALATE: PolicyDecision.ESCALATE,
    RuleVerdict.FAIL: PolicyDecision.DENY,
    RuleVerdict.WAIT: PolicyDecision.WAIT,
    RuleVerdict.PASS: PolicyDecision.ALLOW,
}

# Blocking strength. STOP beats ESCALATE beats DENY beats WAIT beats ALLOW.
_SEVERITY: dict[RuleVerdict, int] = {
    RuleVerdict.STOP: 4,
    RuleVerdict.ESCALATE: 3,
    RuleVerdict.FAIL: 2,
    RuleVerdict.WAIT: 1,
    RuleVerdict.PASS: 0,
}


def evaluate_rules(context: PolicyContext) -> list[PolicyRuleResult]:
    """Run every registered rule independently.

    Args:
        context: Read-only policy snapshots plus diagnosis.

    Returns:
        One result per registry entry, in precedence order.
    """
    results: list[PolicyRuleResult] = []
    for item in iter_policies():
        results.append(item.fn(context))
    return results


def _order_index(name: str) -> int:
    """Precedence index; unknown names sort last."""
    try:
        return POLICY_PRECEDENCE.index(name)
    except ValueError:
        return len(POLICY_PRECEDENCE)


def pick_winner(results: Sequence[PolicyRuleResult]) -> PolicyRuleResult | None:
    """Highest-severity blocking rule; ties break by registry order.

    WAIT does not hide a later STOP/ESCALATE. Among the same severity, the
    earlier policy in ``POLICY_PRECEDENCE`` wins.
    """
    blocking = [row for row in results if row.verdict != RuleVerdict.PASS]
    if not blocking:
        return None
    return max(
        blocking,
        key=lambda row: (_SEVERITY[row.verdict], -_order_index(row.policy_name)),
    )


def _merge_channels(
    context: PolicyContext,
    results: Sequence[PolicyRuleResult],
    decision: PolicyDecision,
) -> tuple[list[str], list[str]]:
    """Start from consent, then union blocks from non-PASS rules."""
    allowed, blocked = split_channels(context.customer)
    blocked_set = set(blocked)
    allowed_set = set(allowed)
    for row in results:
        if row.verdict == RuleVerdict.PASS and not row.blocked_channels:
            continue
        extra_block = row.blocked_channels or []
        extra_allow = row.allowed_channels
        blocked_set.update(extra_block)
        if extra_allow is not None:
            allowed_set = allowed_set.intersection(extra_allow) if allowed_set else set(extra_allow)
            allowed_set.difference_update(blocked_set)
    if decision in {PolicyDecision.STOP, PolicyDecision.DENY}:
        return [], [name for name in CHANNELS]
    if decision == PolicyDecision.ESCALATE:
        return [], [name for name in CHANNELS]
    allowed_final = [name for name in CHANNELS if name in allowed_set and name not in blocked_set]
    blocked_final = [name for name in CHANNELS if name not in allowed_final]
    return allowed_final, blocked_final


def _diagnosis_evidence(context: PolicyContext) -> list[str]:
    """Evidence codes copied from the diagnosis result."""
    codes = [item.code for item in context.diagnosis.evidence_items if item.code]
    if not codes:
        codes = list(context.diagnosis.triggered_rules)
    return codes


def fold_decision(
    context: PolicyContext,
    results: Sequence[PolicyRuleResult],
    *,
    policy_version: str,
) -> PolicyDecisionResult:
    """Combine rule results, diagnosis evidence, and channel lists.

    Args:
        context: Evaluation snapshots.
        results: Independent rule outcomes.
        policy_version: Stamp written onto the decision.

    Returns:
        A single ``PolicyDecisionResult``. Nothing is executed.
    """
    winner = pick_winner(results)
    waits = [row for row in results if row.verdict == RuleVerdict.WAIT]
    if winner is None:
        decision = PolicyDecision.ALLOW
        notable = [
            row
            for row in results
            if row.evidence_codes or row.priority_boost or row.manual_review_required
        ]
        high = next(
            (row for row in results if row.policy_name == "high_value" and row.priority_boost),
            None,
        )
        lead = high or (notable[0] if notable else None)
        policy_name = lead.policy_name if lead is not None else "default_allow"
        reason = (
            lead.reason
            if lead is not None
            else "All policy checks passed. Recovery action is allowed."
        )
        cooldown = None
        winner_codes = list(lead.evidence_codes) if lead is not None else []
        silent = False
    else:
        decision = _VERDICT_TO_DECISION[winner.verdict]
        policy_name = winner.policy_name
        winner_codes = list(winner.evidence_codes)
        silent = winner.silent_retry_allowed
        if decision == PolicyDecision.WAIT:
            reason = " ".join(row.reason for row in waits) or winner.reason
            stamps = [row.cooldown_until for row in waits if row.cooldown_until is not None]
            cooldown = max(stamps) if stamps else winner.cooldown_until
            silent = any(row.silent_retry_allowed for row in waits)
        else:
            reason = winner.reason
            cooldown = winner.cooldown_until
    allowed, blocked = _merge_channels(context, results, decision)
    boost = sum(row.priority_boost for row in results)
    priority = min(100.0, max(0.0, context.diagnosis.priority_score + boost))
    triggered = [row.policy_name for row in results if row.verdict != RuleVerdict.PASS]
    failed = [
        row.policy_name
        for row in results
        if row.verdict in {RuleVerdict.FAIL, RuleVerdict.STOP, RuleVerdict.ESCALATE}
    ]
    evidence = list(dict.fromkeys(_diagnosis_evidence(context) + winner_codes))
    for row in results:
        if row.verdict != RuleVerdict.PASS:
            for code in row.evidence_codes:
                if code not in evidence:
                    evidence.append(code)
    manual = any(row.manual_review_required for row in results)
    if decision in {PolicyDecision.STOP, PolicyDecision.ESCALATE}:
        silent = False
    evaluated_rules = [
        EvaluatedRule(
            policy_name=row.policy_name,
            result=row.verdict,
            reason=row.reason,
        )
        for row in results
    ]
    return PolicyDecisionResult(
        policy_name=policy_name,
        decision=decision,
        reason=reason,
        evidence_codes=evidence,
        priority_score=round(priority, 2),
        decision_priority=DECISION_PRIORITY[decision.value],
        evaluated_at=context.as_of,
        cooldown_until=cooldown,
        allowed_channels=allowed,
        blocked_channels=blocked,
        manual_review_required=manual,
        policy_version=policy_version,
        triggered_policies=triggered,
        failed_policies=failed,
        evaluated_rules=evaluated_rules,
        silent_retry_allowed=silent,
        recovery_case_id=context.recovery_case_id or context.diagnosis.recovery_case_id,
        payment_id=context.payment.id,
        diagnosis=context.diagnosis.diagnosis.value,
        features={
            "customer_segment": context.customer.segment.value,
            "consent_status": context.customer.consent_status.value,
            "payment_amount": context.payment.amount,
        },
    )
