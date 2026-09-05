"""Deterministic diagnosis orchestrator. No I/O, no side effects."""

from __future__ import annotations

import logging
from datetime import UTC, datetime

from services.diagnosis.constants import (
    DIAGNOSIS_MODEL,
    DIAGNOSIS_PRECEDENCE,
    DIAGNOSIS_VERSION,
    EVIDENCE_NO_RULE,
    RECOMMENDED_ACTION,
)
from services.diagnosis.features import extract_features
from services.diagnosis.models import (
    DiagnosisCategory,
    DiagnosisContext,
    DiagnosisResult,
    EvidenceItem,
    RuleHit,
)
from services.diagnosis.rules import evaluate_rules
from services.diagnosis.scorer import evidence_items_for_hit, score_confidence, score_priority

logger = logging.getLogger(__name__)


def _pick_primary(hits: list[RuleHit]) -> DiagnosisCategory:
    """Choose exactly one diagnosis using the documented precedence order."""
    fired = {hit.diagnosis.value for hit in hits}
    for name in DIAGNOSIS_PRECEDENCE:
        if name in fired:
            return DiagnosisCategory(name)
    return DiagnosisCategory.UNKNOWN


def _human_evidence(hit: RuleHit) -> list[str]:
    """Messages for the existing ``evidence: list[str]`` field.

    Structured items whose ``message`` appears in the combined rule evidence
    string are listed individually. Extra scoring-only items (for example a
    recorded NSF reason alongside salary-cycle sentences) stay off this list.
    """
    items = evidence_items_for_hit(hit)
    messages = [item.message for item in items if item.message in hit.evidence]
    return messages or [hit.evidence]


def diagnose(context: DiagnosisContext) -> DiagnosisResult:
    """Run feature extraction, independent rules, and scoring.

    Args:
        context: Snapshots for one failed payment / recovery case.

    Returns:
        A structured ``DiagnosisResult``. Nothing is written to the database
        and no recovery action is executed.
    """
    logger.info(
        "diagnosis.start",
        extra={
            "payment_id": str(context.payment.id),
            "amount": context.payment.amount,
        },
    )
    features = extract_features(context)
    hits = evaluate_rules(features)
    diagnosis = _pick_primary(hits)
    confidence, contributors = score_confidence(features, diagnosis, hits)
    priority, bucket = score_priority(features)
    evidence: list[str] = []
    evidence_items: list[EvidenceItem] = []
    for hit in hits:
        evidence.extend(_human_evidence(hit))
        evidence_items.extend(evidence_items_for_hit(hit))
    if not evidence:
        unknown_msg = "No rule fired; diagnosis is UNKNOWN."
        evidence = [unknown_msg]
        evidence_items = [
            EvidenceItem(code=EVIDENCE_NO_RULE, weight=0.0, message=unknown_msg)
        ]
    result = DiagnosisResult(
        diagnosis=diagnosis,
        confidence=confidence,
        priority_score=priority,
        priority_bucket=bucket,
        evidence=evidence,
        evidence_items=evidence_items,
        triggered_rules=[hit.rule_id for hit in hits],
        confidence_contributors=contributors,
        recommended_action_placeholder=RECOMMENDED_ACTION[diagnosis.value],
        diagnosis_model=DIAGNOSIS_MODEL,
        diagnosis_version=DIAGNOSIS_VERSION,
        generated_at=datetime.now(UTC),
        payment_id=context.payment.id,
        features={
            "days_since_failure": features.days_since_failure,
            "days_until_payday": features.days_until_payday,
            "retry_count": features.retry_count,
            "payment_method": (
                features.payment_method.value if features.payment_method else None
            ),
            "customer_segment": features.customer_segment.value,
            "mandate_status": (
                features.mandate_status.value if features.mandate_status else None
            ),
            "subscription_plan": features.subscription_plan,
            "payment_amount": features.payment_amount,
            "outage_detected": features.outage_detected,
            "previous_success_rate": features.previous_success_rate,
            "promise_pending": features.promise_pending,
            "weekend_payment": features.weekend_payment,
            "festival_period": features.festival_period,
            "recorded_failure_reason": (
                features.recorded_failure_reason.value
                if features.recorded_failure_reason
                else None
            ),
        },
    )
    logger.info(
        "diagnosis.ok",
        extra={
            "payment_id": str(context.payment.id),
            "diagnosis": diagnosis.value,
            "confidence": confidence,
            "priority_score": priority,
        },
    )
    return result
