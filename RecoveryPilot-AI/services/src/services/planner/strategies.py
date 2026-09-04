"""Map diagnosis + policy onto exactly one primary strategy and a fallback."""

from __future__ import annotations

from services.diagnosis.models import DiagnosisCategory
from services.planner.constants import FALLBACK_STRATEGY
from services.planner.models import PlannerContext, PlannerStrategy, StrategyChoice
from services.policy.models import PolicyDecision


def _fallback(strategy: PlannerStrategy) -> PlannerStrategy:
    """Always return one fallback strategy."""
    name = FALLBACK_STRATEGY.get(strategy.value, "ESCALATE_TO_HUMAN")
    return PlannerStrategy(name)


def select_strategy(context: PlannerContext) -> StrategyChoice:
    """Choose the primary planner strategy from diagnosis and policy.

    Policy STOP / DENY / ESCALATE win. WAIT and ALLOW then map through the
    diagnosis matrix. Exactly one primary is returned.

    Args:
        context: Diagnosis, policy, and customer snapshots.

    Returns:
        Primary strategy, fallback, and selection steps.
    """
    diagnosis = context.diagnosis.diagnosis
    decision = context.policy.decision
    evidence = set(context.policy.evidence_codes)
    evidence.update(context.diagnosis.triggered_rules)
    evidence.update(item.code for item in context.diagnosis.evidence_items)
    policy_name = context.policy.policy_name
    steps: list[str] = [
        f"Diagnosis is {diagnosis.value}.",
        f"Policy decision is {decision.value} ({policy_name}).",
    ]

    if decision == PolicyDecision.STOP:
        strategy = PlannerStrategy.STOP_RECOVERY
        steps.append("Policy STOP maps to STOP_RECOVERY.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)

    if decision == PolicyDecision.ESCALATE:
        strategy = PlannerStrategy.ESCALATE_TO_HUMAN
        steps.append("Policy ESCALATE maps to ESCALATE_TO_HUMAN.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)

    if decision == PolicyDecision.DENY:
        strategy = PlannerStrategy.STOP_RECOVERY
        steps.append("Policy DENY (no consent to contact) maps to STOP_RECOVERY.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)

    if decision == PolicyDecision.WAIT:
        if "PROMISE_ACTIVE" in evidence or policy_name == "promise_to_pay":
            strategy = PlannerStrategy.HONOUR_PROMISE_TO_PAY
            steps.append("Active promise-to-pay → HONOUR_PROMISE_TO_PAY.")
            return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
        if diagnosis in {DiagnosisCategory.BANK_TIMEOUT, DiagnosisCategory.UPI_TIMEOUT}:
            strategy = PlannerStrategy.RETRY_SILENTLY
            steps.append("Rail timeout while waiting → RETRY_SILENTLY.")
            return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
        if diagnosis == DiagnosisCategory.INSUFFICIENT_FUNDS:
            strategy = PlannerStrategy.WAIT_FOR_PAYDAY
            steps.append("INSUFFICIENT_FUNDS + WAIT → WAIT_FOR_PAYDAY.")
            return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
        if context.policy.silent_retry_allowed:
            strategy = PlannerStrategy.RETRY_SILENTLY
            steps.append("Policy allows silent retry → RETRY_SILENTLY.")
            return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
        strategy = PlannerStrategy.RETRY_PAYMENT
        steps.append("WAIT with cooldown → RETRY_PAYMENT after the wait.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)

    # ALLOW
    if diagnosis == DiagnosisCategory.CARD_EXPIRED:
        strategy = PlannerStrategy.REQUEST_NEW_MANDATE
        steps.append("CARD_EXPIRED + ALLOW → REQUEST_NEW_MANDATE.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
    if diagnosis == DiagnosisCategory.AUTHENTICATION_FAILED:
        strategy = PlannerStrategy.SWITCH_PAYMENT_METHOD
        steps.append("AUTHENTICATION_FAILED + ALLOW → SWITCH_PAYMENT_METHOD.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
    if "MANDATE_EXPIRED" in evidence or diagnosis == DiagnosisCategory.MANDATE_REVOKED:
        strategy = PlannerStrategy.REQUEST_NEW_MANDATE
        steps.append("Mandate update path → REQUEST_NEW_MANDATE.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
    if "PROMISE_BROKEN" in evidence:
        strategy = PlannerStrategy.ESCALATE_TO_HUMAN
        steps.append("Broken promise + ALLOW → ESCALATE_TO_HUMAN.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
    if diagnosis == DiagnosisCategory.INSUFFICIENT_FUNDS:
        strategy = PlannerStrategy.SEND_PAYMENT_LINK
        steps.append("NSF with ALLOW → SEND_PAYMENT_LINK now.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
    if diagnosis in {DiagnosisCategory.BANK_TIMEOUT, DiagnosisCategory.UPI_TIMEOUT}:
        strategy = PlannerStrategy.RETRY_PAYMENT
        steps.append("Timeout with ALLOW → RETRY_PAYMENT.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
    if diagnosis in {DiagnosisCategory.ALREADY_PAID, DiagnosisCategory.DUPLICATE_PAYMENT}:
        strategy = PlannerStrategy.STOP_RECOVERY
        steps.append("Invoice already settled → STOP_RECOVERY.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
    if diagnosis == DiagnosisCategory.CHARGEBACK_ACTIVE:
        strategy = PlannerStrategy.ESCALATE_TO_HUMAN
        steps.append("Chargeback with ALLOW still escalates.")
        return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)

    strategy = PlannerStrategy.SEND_PAYMENT_LINK
    steps.append("Default ALLOW path → SEND_PAYMENT_LINK.")
    return StrategyChoice(strategy=strategy, fallback=_fallback(strategy), steps=steps)
