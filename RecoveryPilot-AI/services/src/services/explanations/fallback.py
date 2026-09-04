"""Deterministic explanation templates used when Gemini is unavailable."""

from __future__ import annotations

from datetime import UTC, datetime

from services.explanations.formatter import (
    amount_rupees,
    blocked_policies,
    first_name_only,
    human_diagnosis,
    human_strategy,
    with_merchant_disclaimer,
)
from services.explanations.models import (
    ComplianceExplanation,
    CustomerMessage,
    DashboardSummary,
    ExplanationContext,
    ExplanationSource,
    ExplanationType,
    MerchantExplanation,
)


def fallback_merchant(context: ExplanationContext) -> MerchantExplanation:
    """2–4 sentence merchant explanation from engine fields only."""
    reason = human_diagnosis(str(context.diagnosis.diagnosis))
    strategy = human_strategy(str(context.plan.strategy))
    expected = context.plan.expected_outcome or "The next recovery step is scheduled."
    evidence = context.diagnosis.evidence[0] if context.diagnosis.evidence else ""
    sentences = [
        f"The payment did not go through because of {reason}.",
        f"RecoveryPilot chose to {strategy} based on the diagnosis and policy decision ({context.policy.decision.value}).",
        expected if expected.endswith(".") else f"{expected}.",
    ]
    if evidence:
        sentences.append("Supporting note: " + evidence.rstrip(".") + ".")
    if context.execution is not None:
        sentences[2] = (
            f"The latest simulated execution finished as {context.execution.outcome}."
        )
    text = with_merchant_disclaimer(" ".join(sentences[:4]))
    return MerchantExplanation(
        text=text,
        source=ExplanationSource.FALLBACK,
        generated_at=datetime.now(UTC),
        case_id=context.case_id or context.plan.recovery_case_id,
    )


def fallback_customer(context: ExplanationContext, channel: str) -> CustomerMessage:
    """Friendly payment reminder. Never sent by this function."""
    name = first_name_only(context.customer_first_name) or "there"
    merchant = context.merchant_name or "FitLife Gym"
    rupees = amount_rupees(context.plan.estimated_recovery_value)
    body = (
        f"Hi {name}, your {merchant} payment could not be completed. "
        f"Please pay ₹{rupees} when convenient. Thank you."
    )
    if channel == "SMS" and len(body) > 320:
        body = f"Hi {name}, {merchant} payment of ₹{rupees} is pending. Please complete it. Thank you."
    hinglish = (
        "Namaste {first_name}, aapka {merchant} payment pending hai. "
        "Kripya ₹{amount_rupees} pay karein. Link: {payment_link}"
    )
    type_map = {
        "WhatsApp": ExplanationType.CUSTOMER_WHATSAPP,
        "SMS": ExplanationType.CUSTOMER_SMS,
        "Email": ExplanationType.CUSTOMER_EMAIL,
    }
    return CustomerMessage(
        channel=channel,
        language="en",
        body=body,
        hinglish_placeholder=hinglish,
        source=ExplanationSource.FALLBACK,
        explanation_type=type_map.get(channel, ExplanationType.CUSTOMER_SMS),
        generated_at=datetime.now(UTC),
        case_id=context.case_id or context.plan.recovery_case_id,
    )


def fallback_compliance(context: ExplanationContext) -> ComplianceExplanation:
    """Factual audit narrative assembled only from engine outputs."""
    outcome = "not executed"
    if context.execution is not None:
        outcome = context.execution.outcome
    evidence = list(context.diagnosis.evidence)
    triggered = list(context.policy.triggered_policies)
    blocked = blocked_policies(context.policy)
    diagnosis = str(context.diagnosis.diagnosis)
    strategy = str(context.plan.strategy)
    evidence_text = "; ".join(evidence) if evidence else "none provided"
    triggered_text = ", ".join(triggered) if triggered else "none"
    blocked_text = ", ".join(blocked) if blocked else "none"
    narrative = (
        f"Diagnosis {diagnosis}. Evidence: {evidence_text}. "
        f"Triggered policies: {triggered_text}. Blocked policies: {blocked_text}. "
        f"Planner strategy {strategy}. Execution outcome {outcome}."
    )
    return ComplianceExplanation(
        diagnosis=diagnosis,
        evidence=evidence,
        triggered_policies=triggered,
        blocked_policies=blocked,
        planner_strategy=strategy,
        execution_outcome=outcome,
        narrative=narrative,
        source=ExplanationSource.FALLBACK,
        generated_at=datetime.now(UTC),
        case_id=context.case_id or context.plan.recovery_case_id,
    )


def fallback_dashboard(context: ExplanationContext) -> DashboardSummary:
    """One-sentence card. Risk and next action come from the engines."""
    title = human_diagnosis(str(context.diagnosis.diagnosis)).title()
    action = human_strategy(str(context.plan.strategy))
    summary = f"{title}: next, {action}."
    if len(summary) > 160:
        summary = summary[:157] + "..."
    return DashboardSummary(
        title=title[:80] or "Recovery case",
        summary=summary,
        risk_level=str(context.diagnosis.priority_bucket),
        next_action=action,
        source=ExplanationSource.FALLBACK,
        generated_at=datetime.now(UTC),
        case_id=context.case_id or context.plan.recovery_case_id,
    )
