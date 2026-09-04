"""Deterministic diagnosis engine tests. No database, Gemini, or Razorpay."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from services.diagnosis.diagnosis_engine import diagnose
from services.diagnosis.features import extract_features
from services.diagnosis.models import (
    CustomerSnapshot,
    DiagnosisCategory,
    DiagnosisContext,
    OutageWindow,
    PaymentSnapshot,
    PriorityBucket,
    SubscriptionSnapshot,
)
from services.diagnosis.scorer import score_confidence, score_priority
from services.diagnosis_service import summarize_results
from shared.enums import (
    CustomerSegment,
    FailureReason,
    MandateStatus,
    PaymentMethod,
    PaymentStatus,
    SubscriptionStatus,
)

IST = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 9, 2, 18, 0, tzinfo=IST)


def _payment(
    *,
    created_at: datetime,
    status: PaymentStatus = PaymentStatus.FAILED,
    method: PaymentMethod = PaymentMethod.UPI,
    reason: FailureReason | None = FailureReason.INSUFFICIENT_FUNDS,
    amount: int = 99_900,
    attempt_number: int = 1,
    paid_at: datetime | None = None,
    subscription_id=None,
) -> PaymentSnapshot:
    """Build a payment snapshot for engine tests."""
    sub_id = subscription_id if subscription_id is not None else uuid4()
    return PaymentSnapshot(
        id=uuid4(),
        amount=amount,
        status=status,
        method=method,
        failure_reason=reason,
        attempt_number=attempt_number,
        created_at=created_at,
        paid_at=paid_at,
        due_date=created_at.date(),
        subscription_id=sub_id,
        customer_id=uuid4(),
    )


def _customer(
    segment: CustomerSegment = CustomerSegment.AT_RISK,
    salary_dependent: bool = True,
) -> CustomerSnapshot:
    """Build a customer snapshot."""
    return CustomerSnapshot(
        id=uuid4(),
        segment=segment,
        salary_dependent=salary_dependent,
    )


def _subscription(
    *,
    mandate: MandateStatus = MandateStatus.ACTIVE,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
    name: str = "FitLife Pro",
    amount: int = 99_900,
) -> SubscriptionSnapshot:
    """Build a subscription snapshot."""
    return SubscriptionSnapshot(
        id=uuid4(),
        name=name,
        billing_amount=amount,
        mandate_status=mandate,
        subscription_status=status,
    )


def _context(
    payment: PaymentSnapshot,
    *,
    customer: CustomerSnapshot | None = None,
    subscription: SubscriptionSnapshot | None = None,
    others: list[PaymentSnapshot] | None = None,
    outages: list[OutageWindow] | None = None,
) -> DiagnosisContext:
    """Assemble a diagnosis context around one failed payment."""
    sub = subscription or _subscription()
    pay = payment.model_copy(update={"subscription_id": payment.subscription_id or sub.id})
    return DiagnosisContext(
        as_of=AS_OF,
        timezone="Asia/Kolkata",
        payment=pay,
        customer=customer or _customer(),
        subscription=sub.model_copy(update={"id": pay.subscription_id or sub.id}),
        customer_payments=others or [],
        outages=outages or [],
    )


def test_outage_detection_upi_timeout() -> None:
    """A UPI payment inside an NPCI window diagnoses as UPI_TIMEOUT."""
    failed_at = datetime(2026, 7, 15, 12, 0, tzinfo=IST)
    outage = OutageWindow(
        rail="UPI",
        failure_reason="UPI_FAILURE",
        started_at=failed_at - timedelta(hours=1),
        ended_at=failed_at + timedelta(hours=3),
        institution="NPCI",
        summary="NPCI UPI switch timeout",
    )
    payment = _payment(
        created_at=failed_at,
        method=PaymentMethod.UPI,
        reason=FailureReason.UPI_FAILURE,
    )
    result = diagnose(_context(payment, outages=[outage]))
    assert result.diagnosis == DiagnosisCategory.UPI_TIMEOUT
    assert "outage_upi_timeout" in result.triggered_rules
    assert result.recommended_action_placeholder == "RETRY_PAYMENT"


def test_outage_detection_bank_timeout() -> None:
    """A netbanking payment inside a CBS window diagnoses as BANK_TIMEOUT."""
    failed_at = datetime(2026, 7, 20, 9, 0, tzinfo=IST)
    outage = OutageWindow(
        rail="NETBANKING",
        failure_reason="BANK_TIMEOUT",
        started_at=failed_at - timedelta(minutes=30),
        ended_at=failed_at + timedelta(hours=4),
        institution="SBI",
        summary="SBI scheduled CBS maintenance",
    )
    payment = _payment(
        created_at=failed_at,
        method=PaymentMethod.NETBANKING,
        reason=FailureReason.BANK_TIMEOUT,
    )
    result = diagnose(_context(payment, outages=[outage]))
    assert result.diagnosis == DiagnosisCategory.BANK_TIMEOUT
    assert "outage_bank_timeout" in result.triggered_rules


def test_mandate_revoked() -> None:
    """Revoked Autopay diagnoses as MANDATE_REVOKED."""
    payment = _payment(
        created_at=datetime(2026, 8, 10, 11, 0, tzinfo=IST),
        reason=FailureReason.MANDATE_REVOKED,
        method=PaymentMethod.MANDATE,
    )
    result = diagnose(
        _context(
            payment,
            subscription=_subscription(mandate=MandateStatus.REVOKED),
        )
    )
    assert result.diagnosis == DiagnosisCategory.MANDATE_REVOKED
    assert "mandate_revoked" in result.triggered_rules
    assert result.recommended_action_placeholder == "STOP_RECOVERY"


def test_already_paid() -> None:
    """A later capture for the same subscription diagnoses as ALREADY_PAID."""
    failed_at = datetime(2026, 8, 1, 10, 0, tzinfo=IST)
    sub_id = uuid4()
    failed = _payment(
        created_at=failed_at,
        reason=FailureReason.INSUFFICIENT_FUNDS,
        subscription_id=sub_id,
    )
    later = _payment(
        created_at=failed_at + timedelta(days=2),
        status=PaymentStatus.CAPTURED,
        reason=None,
        paid_at=failed_at + timedelta(days=2, hours=1),
        amount=failed.amount,
        subscription_id=sub_id,
    )
    result = diagnose(_context(failed, others=[later]))
    assert result.diagnosis == DiagnosisCategory.ALREADY_PAID
    assert "already_paid_after_failure" in result.triggered_rules
    assert result.recommended_action_placeholder == "NO_ACTION"


def test_duplicate_payment() -> None:
    """A near-simultaneous capture of the same invoice is DUPLICATE_PAYMENT."""
    failed_at = datetime(2026, 8, 12, 16, 0, tzinfo=IST)
    sub_id = uuid4()
    failed = _payment(
        created_at=failed_at,
        reason=FailureReason.UNKNOWN,
        subscription_id=sub_id,
        amount=49_900,
    )
    twin = _payment(
        created_at=failed_at - timedelta(hours=1),
        status=PaymentStatus.CAPTURED,
        reason=None,
        paid_at=failed_at - timedelta(minutes=50),
        amount=49_900,
        subscription_id=sub_id,
    )
    result = diagnose(_context(failed, others=[twin]))
    assert result.diagnosis == DiagnosisCategory.DUPLICATE_PAYMENT
    assert "duplicate_captured_invoice" in result.triggered_rules


def test_insufficient_funds_salary_cycle() -> None:
    """Pre-payday NSF on a salary-dependent customer is INSUFFICIENT_FUNDS."""
    failed_at = datetime(2026, 8, 30, 10, 0, tzinfo=IST)
    payment = _payment(
        created_at=failed_at,
        reason=FailureReason.INSUFFICIENT_FUNDS,
        method=PaymentMethod.UPI,
    )
    prior = _payment(
        created_at=datetime(2026, 8, 5, 10, 0, tzinfo=IST),
        status=PaymentStatus.CAPTURED,
        reason=None,
        paid_at=datetime(2026, 8, 5, 10, 5, tzinfo=IST),
        amount=payment.amount,
        subscription_id=payment.subscription_id,
    )
    result = diagnose(
        _context(
            payment,
            customer=_customer(segment=CustomerSegment.AT_RISK, salary_dependent=True),
            others=[prior],
        )
    )
    assert result.diagnosis == DiagnosisCategory.INSUFFICIENT_FUNDS
    assert "insufficient_funds" in result.triggered_rules
    assert result.recommended_action_placeholder == "WAIT_FOR_PAYDAY"
    joined = " ".join(result.evidence)
    assert "Salary-dependent" in joined
    features = extract_features(
        _context(
            payment,
            customer=_customer(segment=CustomerSegment.AT_RISK, salary_dependent=True),
        )
    )
    assert features.days_until_payday == 2
    assert features.pre_payday_window is True


def test_confidence_scoring_outage_higher_than_unknown() -> None:
    """Outage-backed timeout confidence is higher than a bare UNKNOWN case."""
    failed_at = datetime(2026, 7, 15, 12, 0, tzinfo=IST)
    outage = OutageWindow(
        rail="UPI",
        failure_reason="UPI_FAILURE",
        started_at=failed_at - timedelta(hours=1),
        ended_at=failed_at + timedelta(hours=2),
        institution="NPCI",
        summary="NPCI UPI switch timeout",
    )
    timed_out = diagnose(
        _context(
            _payment(
                created_at=failed_at,
                method=PaymentMethod.UPI,
                reason=FailureReason.UPI_FAILURE,
            ),
            outages=[outage],
        )
    )
    unknown = diagnose(
        _context(
            _payment(
                created_at=failed_at,
                method=PaymentMethod.WALLET,
                reason=FailureReason.UNKNOWN,
            )
        )
    )
    assert timed_out.confidence > unknown.confidence
    assert timed_out.confidence_contributors
    assert 0.0 <= timed_out.confidence <= 1.0
    features = extract_features(
        _context(
            _payment(
                created_at=failed_at,
                method=PaymentMethod.UPI,
                reason=FailureReason.UPI_FAILURE,
            ),
            outages=[outage],
        )
    )
    _, contributors = score_confidence(features, DiagnosisCategory.UPI_TIMEOUT, [])
    assert any(item.label == "outage_match" for item in contributors)


def test_priority_scoring_high_value_vs_new() -> None:
    """HIGH_VALUE premium invoices score into a higher bucket than NEW starter."""
    failed_at = datetime(2026, 8, 20, 10, 0, tzinfo=IST)
    high = diagnose(
        _context(
            _payment(
                created_at=failed_at,
                amount=249_900,
                reason=FailureReason.BANK_TIMEOUT,
                method=PaymentMethod.CARD,
            ),
            customer=_customer(
                segment=CustomerSegment.HIGH_VALUE, salary_dependent=False
            ),
            subscription=_subscription(name="FitLife Premium", amount=249_900),
        )
    )
    low = diagnose(
        _context(
            _payment(
                created_at=failed_at,
                amount=49_900,
                reason=FailureReason.UNKNOWN,
                method=PaymentMethod.UPI,
            ),
            customer=_customer(segment=CustomerSegment.NEW, salary_dependent=False),
            subscription=_subscription(name="FitLife Starter", amount=49_900),
        )
    )
    assert high.priority_score > low.priority_score
    assert high.priority_bucket in {PriorityBucket.HIGH, PriorityBucket.MEDIUM}
    score, bucket = score_priority(
        extract_features(
            _context(
                _payment(created_at=failed_at, amount=249_900, method=PaymentMethod.CARD),
                customer=_customer(
                    segment=CustomerSegment.HIGH_VALUE, salary_dependent=False
                ),
                subscription=_subscription(name="FitLife Premium", amount=249_900),
            )
        )
    )
    assert 0.0 <= score <= 100.0
    assert bucket in PriorityBucket


def test_batch_diagnosis_summary() -> None:
    """Batch rollup counts diagnoses, unknown share, and priority bands."""
    failed_at = datetime(2026, 8, 30, 10, 0, tzinfo=IST)
    nsf = diagnose(
        _context(
            _payment(created_at=failed_at, reason=FailureReason.INSUFFICIENT_FUNDS),
            customer=_customer(segment=CustomerSegment.AT_RISK),
        )
    )
    revoked = diagnose(
        _context(
            _payment(
                created_at=failed_at,
                reason=FailureReason.MANDATE_REVOKED,
                method=PaymentMethod.MANDATE,
            ),
            subscription=_subscription(mandate=MandateStatus.REVOKED),
        )
    )
    unknown = diagnose(
        _context(
            _payment(
                created_at=failed_at,
                reason=FailureReason.UNKNOWN,
                method=PaymentMethod.WALLET,
            ),
            customer=_customer(segment=CustomerSegment.NEW, salary_dependent=False),
        )
    )
    summary = summarize_results([nsf, revoked, unknown])
    assert summary.diagnosed_cases == 3
    assert summary.diagnosis_distribution[DiagnosisCategory.INSUFFICIENT_FUNDS] == 1
    assert summary.diagnosis_distribution[DiagnosisCategory.MANDATE_REVOKED] == 1
    assert summary.unknown_diagnoses == 1
    assert summary.average_confidence > 0
    assert summary.priority_distribution
    assert summary.top_failure_reasons
    assert nsf.diagnosis_model == "recovery_diagnosis_v1"
    assert nsf.diagnosis_version == "1.0.0"
    assert nsf.generated_at
    assert nsf.triggered_rules
    assert nsf.evidence
    assert nsf.evidence_items
    for item in nsf.evidence_items:
        assert item.code
        assert 0.0 <= item.weight <= 1.0
        assert item.message


def test_structured_evidence_objects_and_human_list() -> None:
    """NSF returns EvidenceItem rows while keeping the string evidence list."""
    failed_at = datetime(2026, 8, 30, 10, 0, tzinfo=IST)
    payment = _payment(
        created_at=failed_at,
        reason=FailureReason.INSUFFICIENT_FUNDS,
        method=PaymentMethod.UPI,
    )
    prior = _payment(
        created_at=datetime(2026, 8, 5, 10, 0, tzinfo=IST),
        status=PaymentStatus.CAPTURED,
        reason=None,
        paid_at=datetime(2026, 8, 5, 10, 5, tzinfo=IST),
        amount=payment.amount,
        subscription_id=payment.subscription_id,
    )
    result = diagnose(
        _context(
            payment,
            customer=_customer(segment=CustomerSegment.AT_RISK, salary_dependent=True),
            others=[prior],
        )
    )
    assert result.diagnosis == DiagnosisCategory.INSUFFICIENT_FUNDS
    assert isinstance(result.evidence, list)
    assert all(isinstance(line, str) and line for line in result.evidence)
    joined = " ".join(result.evidence)
    assert "Salary-dependent" in joined
    codes = {item.code for item in result.evidence_items}
    assert "SALARY_DEPENDENT" in codes
    assert "PRE_PAYDAY_WINDOW" in codes
    assert "DAYS_UNTIL_PAYDAY" in codes
    assert "PRIOR_SUCCESS" in codes
    for item in result.evidence_items:
        assert item.code
        assert 0.0 <= item.weight <= 1.0
        assert item.message
    human_messages = set(result.evidence)
    for item in result.evidence_items:
        if item.code != "RECORDED_INSUFFICIENT_FUNDS":
            assert item.message in human_messages


def test_confidence_output_includes_evidence_weights() -> None:
    """Confidence contributors expose evidence_weight and applied_weight."""
    failed_at = datetime(2026, 7, 15, 12, 0, tzinfo=IST)
    outage = OutageWindow(
        rail="UPI",
        failure_reason="UPI_FAILURE",
        started_at=failed_at - timedelta(hours=1),
        ended_at=failed_at + timedelta(hours=2),
        institution="NPCI",
        summary="NPCI UPI switch timeout",
    )
    result = diagnose(
        _context(
            _payment(
                created_at=failed_at,
                method=PaymentMethod.UPI,
                reason=FailureReason.UPI_FAILURE,
            ),
            outages=[outage],
        )
    )
    assert result.confidence_contributors
    assert any(item.label == "outage_match" for item in result.confidence_contributors)
    evidence_terms = [
        item
        for item in result.confidence_contributors
        if item.evidence_weight is not None and item.code not in {"BASE"}
    ]
    assert evidence_terms
    for item in evidence_terms:
        assert item.code
        assert item.evidence_weight is not None
        assert item.applied_weight is not None
        assert 0.0 <= item.evidence_weight <= 1.0
        assert 0.0 <= item.applied_weight <= 1.0
    rule_terms = [
        item
        for item in result.confidence_contributors
        if item.code == "OUTAGE_UPI_TIMEOUT"
    ]
    assert rule_terms
    assert rule_terms[0].evidence_weight == rule_terms[0].weight
    assert rule_terms[0].applied_weight == round(rule_terms[0].evidence_weight * 0.35, 4)
    outage_item = next(
        item for item in result.evidence_items if item.code == "OUTAGE_UPI_TIMEOUT"
    )
    assert outage_item.weight == rule_terms[0].evidence_weight
    assert outage_item.message in result.evidence
