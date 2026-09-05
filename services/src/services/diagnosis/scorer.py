"""Confidence (0–1) and priority (0–100) scorers. Pure functions."""

from __future__ import annotations

from services.diagnosis.constants import (
    CONFIDENCE_BASE,
    CONFIDENCE_HISTORY,
    CONFIDENCE_MANDATE,
    CONFIDENCE_OUTAGE_MATCH,
    CONFIDENCE_PAYDAY,
    CONFIDENCE_RECORDED_REASON_MATCH,
    CONFIDENCE_RETRY,
    EVIDENCE_BASE,
    EVIDENCE_CUSTOMER_HISTORY,
    EVIDENCE_MANDATE_STATE,
    EVIDENCE_OUTAGE_MATCH,
    EVIDENCE_PAYMENT_RETRIES,
    EVIDENCE_RECORDED_FAILURE_REASON,
    EVIDENCE_SALARY_CYCLE,
    PRIORITY_HIGH_MIN,
    PRIORITY_MEDIUM_MIN,
    RULE_EVIDENCE_SCALE,
    SEGMENT_PRIORITY_POINTS,
    TIER_PRIORITY_POINTS,
)
from services.diagnosis.models import (
    ConfidenceContributor,
    DiagnosisCategory,
    DiagnosisFeatures,
    EvidenceItem,
    PriorityBucket,
    RuleHit,
)
from shared.enums import FailureReason, MandateStatus

_REASON_TO_DIAGNOSIS: dict[FailureReason, DiagnosisCategory] = {
    FailureReason.INSUFFICIENT_FUNDS: DiagnosisCategory.INSUFFICIENT_FUNDS,
    FailureReason.BANK_TIMEOUT: DiagnosisCategory.BANK_TIMEOUT,
    FailureReason.UPI_FAILURE: DiagnosisCategory.UPI_TIMEOUT,
    FailureReason.CARD_EXPIRED: DiagnosisCategory.CARD_EXPIRED,
    FailureReason.MANDATE_REVOKED: DiagnosisCategory.MANDATE_REVOKED,
    FailureReason.CUSTOMER_CANCELLED: DiagnosisCategory.CUSTOMER_CANCELLED,
    FailureReason.DISPUTE: DiagnosisCategory.CHARGEBACK_ACTIVE,
    FailureReason.ALREADY_PAID: DiagnosisCategory.ALREADY_PAID,
    FailureReason.UNKNOWN: DiagnosisCategory.UNKNOWN,
}


def _clamp(value: float, lo: float, hi: float) -> float:
    """Clamp ``value`` into ``[lo, hi]``."""
    return max(lo, min(hi, value))


def recorded_reason_matches(
    features: DiagnosisFeatures, diagnosis: DiagnosisCategory
) -> bool:
    """True when the stored FailureReason maps onto the chosen diagnosis."""
    reason = features.recorded_failure_reason
    if reason is None:
        return False
    mapped = _REASON_TO_DIAGNOSIS.get(reason)
    if mapped == diagnosis:
        return True
    if reason == FailureReason.UPI_FAILURE and diagnosis == DiagnosisCategory.AUTHENTICATION_FAILED:
        return True
    return False


def evidence_items_for_hit(hit: RuleHit) -> list[EvidenceItem]:
    """Structured evidence for a rule hit, synthesizing one item if needed."""
    if hit.evidence_items:
        return list(hit.evidence_items)
    return [
        EvidenceItem(code=hit.rule_id.upper(), weight=hit.weight, message=hit.evidence)
    ]


def _contributor(
    *,
    label: str,
    code: str,
    weight: float,
    message: str,
    evidence_weight: float | None,
    applied_weight: float,
) -> ConfidenceContributor:
    """Build a confidence term that exposes evidence weights in the output."""
    return ConfidenceContributor(
        label=label,
        weight=weight,
        code=code,
        message=message,
        evidence_weight=evidence_weight,
        applied_weight=applied_weight,
    )


def score_confidence(
    features: DiagnosisFeatures,
    diagnosis: DiagnosisCategory,
    hits: list[RuleHit],
) -> tuple[float, list[ConfidenceContributor]]:
    """Weighted confidence for the chosen primary diagnosis.

    Matching-rule evidence item weights are scaled by ``RULE_EVIDENCE_SCALE``
    and added to a base prior plus corroborating signals. Each term is listed
    on the contributor list with ``code``, ``weight``, ``message``,
    ``evidence_weight``, and ``applied_weight``.

    Args:
        features: Extracted feature vector.
        diagnosis: Single primary label.
        hits: All rules that fired (used as evidence weights).

    Returns:
        Confidence in ``[0, 1]`` and the contributor list.
    """
    contributors: list[ConfidenceContributor] = [
        _contributor(
            label="base",
            code=EVIDENCE_BASE,
            weight=CONFIDENCE_BASE,
            message="Base prior applied to every diagnosis.",
            evidence_weight=CONFIDENCE_BASE,
            applied_weight=CONFIDENCE_BASE,
        )
    ]
    score = CONFIDENCE_BASE
    matching_hits = [hit for hit in hits if hit.diagnosis == diagnosis]
    for hit in matching_hits:
        items = evidence_items_for_hit(hit)
        for item in items:
            applied = item.weight * RULE_EVIDENCE_SCALE
            contributors.append(
                _contributor(
                    label=f"rule:{hit.rule_id}" if len(items) == 1 else f"evidence:{item.code}",
                    code=item.code,
                    weight=item.weight,
                    message=item.message,
                    evidence_weight=item.weight,
                    applied_weight=round(applied, 4),
                )
            )
            score += applied
    if recorded_reason_matches(features, diagnosis):
        contributors.append(
            _contributor(
                label="recorded_failure_reason",
                code=EVIDENCE_RECORDED_FAILURE_REASON,
                weight=CONFIDENCE_RECORDED_REASON_MATCH,
                message="Recorded payment failure reason maps to the primary diagnosis.",
                evidence_weight=CONFIDENCE_RECORDED_REASON_MATCH,
                applied_weight=CONFIDENCE_RECORDED_REASON_MATCH,
            )
        )
        score += CONFIDENCE_RECORDED_REASON_MATCH
    if features.outage_detected and diagnosis in {
        DiagnosisCategory.BANK_TIMEOUT,
        DiagnosisCategory.UPI_TIMEOUT,
    }:
        contributors.append(
            _contributor(
                label="outage_match",
                code=EVIDENCE_OUTAGE_MATCH,
                weight=CONFIDENCE_OUTAGE_MATCH,
                message="Payment timestamp falls inside a matching rail outage window.",
                evidence_weight=CONFIDENCE_OUTAGE_MATCH,
                applied_weight=CONFIDENCE_OUTAGE_MATCH,
            )
        )
        score += CONFIDENCE_OUTAGE_MATCH
    if features.previous_success_rate >= 0.5 and diagnosis == DiagnosisCategory.INSUFFICIENT_FUNDS:
        contributors.append(
            _contributor(
                label="customer_history",
                code=EVIDENCE_CUSTOMER_HISTORY,
                weight=CONFIDENCE_HISTORY,
                message="Prior successful payments support a temporary-funds diagnosis.",
                evidence_weight=CONFIDENCE_HISTORY,
                applied_weight=CONFIDENCE_HISTORY,
            )
        )
        score += CONFIDENCE_HISTORY
    if features.retry_count > 0 and diagnosis in {
        DiagnosisCategory.AUTHENTICATION_FAILED,
        DiagnosisCategory.UPI_TIMEOUT,
        DiagnosisCategory.BANK_TIMEOUT,
    }:
        contributors.append(
            _contributor(
                label="payment_retries",
                code=EVIDENCE_PAYMENT_RETRIES,
                weight=CONFIDENCE_RETRY,
                message="Retry history corroborates an authentication or timeout diagnosis.",
                evidence_weight=CONFIDENCE_RETRY,
                applied_weight=CONFIDENCE_RETRY,
            )
        )
        score += CONFIDENCE_RETRY
    if features.mandate_status in {MandateStatus.REVOKED, MandateStatus.EXPIRED} and diagnosis in {
        DiagnosisCategory.MANDATE_REVOKED,
        DiagnosisCategory.CARD_EXPIRED,
    }:
        contributors.append(
            _contributor(
                label="mandate_state",
                code=EVIDENCE_MANDATE_STATE,
                weight=CONFIDENCE_MANDATE,
                message="Mandate is revoked or expired.",
                evidence_weight=CONFIDENCE_MANDATE,
                applied_weight=CONFIDENCE_MANDATE,
            )
        )
        score += CONFIDENCE_MANDATE
    if features.salary_dependent and diagnosis == DiagnosisCategory.INSUFFICIENT_FUNDS:
        contributors.append(
            _contributor(
                label="salary_cycle",
                code=EVIDENCE_SALARY_CYCLE,
                weight=CONFIDENCE_PAYDAY,
                message="Salary-dependent customer; payday cycle corroborates NSF.",
                evidence_weight=CONFIDENCE_PAYDAY,
                applied_weight=CONFIDENCE_PAYDAY,
            )
        )
        score += CONFIDENCE_PAYDAY
    confidence = round(_clamp(score, 0.05, 0.99), 4)
    return confidence, contributors


def priority_bucket(score: float) -> PriorityBucket:
    """Map a 0–100 score onto HIGH / MEDIUM / LOW."""
    if score >= PRIORITY_HIGH_MIN:
        return PriorityBucket.HIGH
    if score >= PRIORITY_MEDIUM_MIN:
        return PriorityBucket.MEDIUM
    return PriorityBucket.LOW


def score_priority(features: DiagnosisFeatures) -> tuple[float, PriorityBucket]:
    """Queue priority from amount, segment, overdue days, retries, tier, promises.

    Args:
        features: Extracted feature vector.

    Returns:
        Score in ``[0, 100]`` and the bucket label.
    """
    amount_points = min(30.0, features.payment_amount / 50_000.0 * 5.0)
    segment_points = SEGMENT_PRIORITY_POINTS.get(features.customer_segment.value, 8.0)
    overdue_points = min(20.0, float(features.days_overdue) * 2.0)
    retry_points = min(10.0, float(features.retry_count) * 3.0)
    tier_points = TIER_PRIORITY_POINTS.get(features.subscription_tier, 2.0)
    promise_points = 8.0 if features.promise_pending else 0.0
    history_points = 5.0 if features.previous_success_rate >= 0.4 else 0.0
    raw = (
        amount_points
        + segment_points
        + overdue_points
        + retry_points
        + tier_points
        + promise_points
        + history_points
    )
    score = round(_clamp(raw, 0.0, 100.0), 2)
    return score, priority_bucket(score)
