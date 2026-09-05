"""Independent diagnosis rules. Each function inspects features only."""

from __future__ import annotations

from collections.abc import Callable

from services.diagnosis.constants import (
    EVIDENCE_DAYS_UNTIL_PAYDAY,
    EVIDENCE_PRE_PAYDAY_WINDOW,
    EVIDENCE_PRIOR_SUCCESS,
    EVIDENCE_RECORDED_INSUFFICIENT_FUNDS,
    EVIDENCE_SALARY_DEPENDENT,
)
from services.diagnosis.models import (
    DiagnosisCategory,
    DiagnosisFeatures,
    EvidenceItem,
    RuleHit,
)
from shared.enums import FailureReason, MandateStatus

RuleFn = Callable[[DiagnosisFeatures], RuleHit | None]


def _hit(
    rule_id: str,
    diagnosis: DiagnosisCategory,
    weight: float,
    message: str,
    items: list[EvidenceItem] | None = None,
) -> RuleHit:
    """Build a rule hit with at least one structured evidence item."""
    evidence_items = items or [
        EvidenceItem(code=rule_id.upper(), weight=weight, message=message)
    ]
    return RuleHit(
        rule_id=rule_id,
        diagnosis=diagnosis,
        weight=weight,
        evidence=message,
        evidence_items=evidence_items,
    )


def rule_already_paid(features: DiagnosisFeatures) -> RuleHit | None:
    """Successful capture after the failed attempt."""
    if not features.already_paid_after_failure:
        return None
    return _hit(
        "already_paid_after_failure",
        DiagnosisCategory.ALREADY_PAID,
        0.90,
        "Customer already has a successful payment after this failure.",
    )


def rule_duplicate_payment(features: DiagnosisFeatures) -> RuleHit | None:
    """Another capture in the duplicate window for the same invoice."""
    if not features.duplicate_captured:
        return None
    return _hit(
        "duplicate_captured_invoice",
        DiagnosisCategory.DUPLICATE_PAYMENT,
        0.85,
        "A matching successful payment exists within the duplicate window.",
    )


def rule_chargeback_active(features: DiagnosisFeatures) -> RuleHit | None:
    """Dispute / chargeback signal on the failed payment."""
    if not features.dispute_signal:
        return None
    return _hit(
        "dispute_or_chargeback",
        DiagnosisCategory.CHARGEBACK_ACTIVE,
        0.88,
        "Payment is flagged as a dispute; chargeback path is active.",
    )


def rule_customer_cancelled(features: DiagnosisFeatures) -> RuleHit | None:
    """Subscription cancelled or recorded customer-cancelled failure."""
    cancelled = features.subscription_cancelled or (
        features.recorded_failure_reason == FailureReason.CUSTOMER_CANCELLED
    )
    if not cancelled:
        return None
    return _hit(
        "customer_cancelled",
        DiagnosisCategory.CUSTOMER_CANCELLED,
        0.86,
        "Subscription is cancelled or the failure was recorded as customer cancelled.",
    )


def rule_mandate_revoked(features: DiagnosisFeatures) -> RuleHit | None:
    """Autopay mandate revoked or expired."""
    revoked = features.mandate_revoked or (
        features.recorded_failure_reason == FailureReason.MANDATE_REVOKED
    )
    expired = features.mandate_status == MandateStatus.EXPIRED and not features.card_method
    if not revoked and not expired:
        return None
    return _hit(
        "mandate_revoked",
        DiagnosisCategory.MANDATE_REVOKED,
        0.87,
        f"Mandate status is {features.mandate_status}.",
    )


def rule_card_expired(features: DiagnosisFeatures) -> RuleHit | None:
    """Card rail with expiry signal or expired mandate on a card method."""
    recorded = features.recorded_failure_reason == FailureReason.CARD_EXPIRED
    expired_card = features.card_method and features.mandate_status == MandateStatus.EXPIRED
    if not recorded and not expired_card:
        return None
    return _hit(
        "card_expired",
        DiagnosisCategory.CARD_EXPIRED,
        0.84,
        "Card expiry is indicated by the failure reason or an expired card mandate.",
    )


def rule_bank_timeout(features: DiagnosisFeatures) -> RuleHit | None:
    """Bank/card/netbanking outage or recorded BANK_TIMEOUT during an outage."""
    rail = (features.outage_rail or "").upper()
    outage_bank = features.outage_detected and rail in {"CARD", "NETBANKING"}
    recorded = features.recorded_failure_reason == FailureReason.BANK_TIMEOUT
    if not outage_bank and not (recorded and features.outage_detected):
        if recorded and not features.upi_method:
            return _hit(
                "recorded_bank_timeout",
                DiagnosisCategory.BANK_TIMEOUT,
                0.55,
                "Failure reason is BANK_TIMEOUT.",
            )
        return None
    summary = features.outage_summary or "rail outage"
    return _hit(
        "outage_bank_timeout",
        DiagnosisCategory.BANK_TIMEOUT,
        0.82,
        f"Payment occurred during {summary} on the {rail or 'bank'} rail.",
    )


def rule_upi_timeout(features: DiagnosisFeatures) -> RuleHit | None:
    """UPI rail outage. Maps NPCI/UPI_FAILURE windows to UPI_TIMEOUT."""
    rail = (features.outage_rail or "").upper()
    if features.outage_detected and rail == "UPI":
        summary = features.outage_summary or "UPI outage"
        return _hit(
            "outage_upi_timeout",
            DiagnosisCategory.UPI_TIMEOUT,
            0.83,
            f"Payment occurred during {summary}.",
        )
    if (
        features.recorded_failure_reason == FailureReason.UPI_FAILURE
        and features.weekend_payment
        and features.upi_method
    ):
        return _hit(
            "weekend_upi_timeout",
            DiagnosisCategory.UPI_TIMEOUT,
            0.48,
            "UPI failure on a weekend, consistent with rail congestion.",
        )
    return None


def rule_authentication_failed(features: DiagnosisFeatures) -> RuleHit | None:
    """UPI/auth failure without an outage, often with retries."""
    if features.outage_detected:
        return None
    upi_fail = features.recorded_failure_reason == FailureReason.UPI_FAILURE
    retried_upi = features.upi_method and features.retry_count >= 2
    if not upi_fail and not retried_upi:
        return None
    return _hit(
        "authentication_failed",
        DiagnosisCategory.AUTHENTICATION_FAILED,
        0.62,
        "UPI authentication failed and no matching rail outage was found.",
    )


def _nsf_evidence(features: DiagnosisFeatures) -> list[tuple[str, float, str]]:
    """Relative NSF evidence shares. Scaled later to the rule weight."""
    rows: list[tuple[str, float, str]] = []
    if features.recorded_failure_reason == FailureReason.INSUFFICIENT_FUNDS:
        rows.append(
            (
                EVIDENCE_RECORDED_INSUFFICIENT_FUNDS,
                1.0,
                "Failure reason is INSUFFICIENT_FUNDS.",
            )
        )
    if features.salary_dependent:
        rows.append(
            (EVIDENCE_SALARY_DEPENDENT, 1.2, "Salary-dependent customer.")
        )
    if features.pre_payday_window:
        rows.append(
            (
                EVIDENCE_PRE_PAYDAY_WINDOW,
                1.3,
                f"Failure occurred on day {features.calendar_day} (pre-payday squeeze).",
            )
        )
    if features.days_until_payday:
        rows.append(
            (
                EVIDENCE_DAYS_UNTIL_PAYDAY,
                1.1,
                f"Salary expected in {features.days_until_payday} day(s).",
            )
        )
    if features.previous_success_count:
        rows.append(
            (
                EVIDENCE_PRIOR_SUCCESS,
                1.0,
                f"{features.previous_success_count} previous successful payment(s) on file.",
            )
        )
    return rows


def rule_insufficient_funds(features: DiagnosisFeatures) -> RuleHit | None:
    """NSF, especially salary-cycle failures before payday."""
    recorded = features.recorded_failure_reason == FailureReason.INSUFFICIENT_FUNDS
    salary_nsf = features.salary_dependent and features.pre_payday_window
    if not recorded and not salary_nsf:
        return None
    rule_weight = 0.78 if salary_nsf else 0.60
    raw = _nsf_evidence(features)
    if not raw:
        raw = [
            (
                EVIDENCE_RECORDED_INSUFFICIENT_FUNDS,
                1.0,
                "Failure reason is INSUFFICIENT_FUNDS.",
            )
        ]
    total_share = sum(share for _, share, _ in raw)
    items: list[EvidenceItem] = []
    allocated = 0.0
    for index, (code, share, message) in enumerate(raw):
        if index == len(raw) - 1:
            item_weight = round(rule_weight - allocated, 4)
        else:
            item_weight = round(rule_weight * share / total_share, 4)
            allocated += item_weight
        items.append(
            EvidenceItem(
                code=code,
                weight=max(0.0, min(1.0, item_weight)),
                message=message,
            )
        )
    # Human-readable list keeps the original salary-cycle sentences first;
    # recorded-reason is included only when it is the sole item.
    display = [item.message for item in items if item.code != EVIDENCE_RECORDED_INSUFFICIENT_FUNDS]
    if not display:
        display = [items[0].message]
    return RuleHit(
        rule_id="insufficient_funds",
        diagnosis=DiagnosisCategory.INSUFFICIENT_FUNDS,
        weight=rule_weight,
        evidence=" ".join(display),
        evidence_items=items,
    )


RULES: tuple[RuleFn, ...] = (
    rule_already_paid,
    rule_duplicate_payment,
    rule_chargeback_active,
    rule_customer_cancelled,
    rule_mandate_revoked,
    rule_card_expired,
    rule_bank_timeout,
    rule_upi_timeout,
    rule_authentication_failed,
    rule_insufficient_funds,
)


def evaluate_rules(features: DiagnosisFeatures) -> list[RuleHit]:
    """Run every rule independently and collect hits.

    Args:
        features: Extracted feature vector.

    Returns:
        All rules that fired. The engine picks one primary diagnosis.
    """
    hits: list[RuleHit] = []
    for rule in RULES:
        hit = rule(features)
        if hit is not None:
            hits.append(hit)
    return hits
