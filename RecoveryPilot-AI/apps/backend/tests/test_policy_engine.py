"""Deterministic policy engine tests. No database, Gemini, or Razorpay."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from services.diagnosis.models import (
    DiagnosisCategory,
    DiagnosisResult,
    EvidenceItem,
    PriorityBucket,
)
from services.policy.constants import DECISION_PRIORITY, POLICY_PRECEDENCE
from services.policy.models import (
    CustomerPolicySnapshot,
    PaymentPolicySnapshot,
    PolicyContext,
    PolicyDecision,
    PromisePolicySnapshot,
    RecoveryActionSnapshot,
    RuleVerdict,
    SubscriptionPolicySnapshot,
)
from services.policy.policy_engine import evaluate, evaluate_many, summarize_decisions
from shared.enums import (
    ConsentStatus,
    CustomerSegment,
    ExecutionStatus,
    MandateStatus,
    PaymentStatus,
    PromiseStatus,
    RecoveryActionType,
    SubscriptionStatus,
)

IST = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 9, 2, 12, 0, tzinfo=IST)
AS_OF_NIGHT = datetime(2026, 9, 2, 21, 0, tzinfo=IST)


def _diagnosis(
    category: DiagnosisCategory = DiagnosisCategory.INSUFFICIENT_FUNDS,
    *,
    priority_score: float = 50.0,
    payment_id=None,
    evidence_codes: list[str] | None = None,
) -> DiagnosisResult:
    """Minimal diagnosis result for policy tests."""
    pay_id = payment_id or uuid4()
    items = [
        EvidenceItem(code=code, weight=0.5, message=code.replace("_", " ").lower())
        for code in (evidence_codes or [])
    ]
    return DiagnosisResult(
        diagnosis=category,
        confidence=0.8,
        priority_score=priority_score,
        priority_bucket=PriorityBucket.MEDIUM,
        evidence=["synthetic evidence"],
        evidence_items=items,
        triggered_rules=[],
        recommended_action_placeholder="RETRY_PAYMENT",
        diagnosis_model="recovery_diagnosis_v1",
        diagnosis_version="1.0.0",
        generated_at=AS_OF,
        payment_id=pay_id,
    )


def _customer(
    *,
    segment: CustomerSegment = CustomerSegment.AT_RISK,
    consent: ConsentStatus = ConsentStatus.GRANTED,
    whatsapp: bool = True,
    sms: bool = True,
    voice: bool = True,
    email: bool = True,
    hardship: bool = False,
) -> CustomerPolicySnapshot:
    """Build a customer policy snapshot."""
    return CustomerPolicySnapshot(
        id=uuid4(),
        segment=segment,
        consent_status=consent,
        consent_whatsapp=whatsapp,
        consent_sms=sms,
        consent_voice=voice,
        consent_email=email,
        hardship=hardship,
        timezone="Asia/Kolkata",
    )


def _payment(*, amount: int = 99_900, created_at: datetime | None = None) -> PaymentPolicySnapshot:
    """Build a payment policy snapshot."""
    return PaymentPolicySnapshot(
        id=uuid4(),
        amount=amount,
        status=PaymentStatus.FAILED,
        created_at=created_at or AS_OF - timedelta(days=2),
        attempt_number=1,
    )


def _subscription(
    *,
    mandate: MandateStatus = MandateStatus.ACTIVE,
    status: SubscriptionStatus = SubscriptionStatus.ACTIVE,
) -> SubscriptionPolicySnapshot:
    """Build a subscription policy snapshot."""
    return SubscriptionPolicySnapshot(
        id=uuid4(),
        mandate_status=mandate,
        subscription_status=status,
    )


def _context(
    *,
    diagnosis: DiagnosisResult | None = None,
    customer: CustomerPolicySnapshot | None = None,
    payment: PaymentPolicySnapshot | None = None,
    subscription: SubscriptionPolicySnapshot | None = None,
    as_of: datetime = AS_OF,
    actions: list[RecoveryActionSnapshot] | None = None,
    promises: list[PromisePolicySnapshot] | None = None,
) -> PolicyContext:
    """Assemble a policy context around one failed payment."""
    pay = payment or _payment()
    diag = diagnosis or _diagnosis(payment_id=pay.id)
    if diag.payment_id is None:
        diag = diag.model_copy(update={"payment_id": pay.id})
    return PolicyContext(
        as_of=as_of,
        diagnosis=diag,
        customer=customer or _customer(),
        payment=pay,
        subscription=subscription or _subscription(),
        recovery_actions=actions or [],
        promises=promises or [],
        recovery_case_id=uuid4(),
    )


def test_consent_revoked_stops() -> None:
    """Withdrawn consent stops recovery and blocks every channel."""
    result = evaluate(
        _context(customer=_customer(consent=ConsentStatus.WITHDRAWN))
    )
    assert result.decision == PolicyDecision.STOP
    assert result.policy_name == "consent"
    assert "revoked" in result.reason.lower()
    assert result.allowed_channels == []
    assert set(result.blocked_channels) == {"WhatsApp", "SMS", "Voice", "Email"}
    assert "CONSENT_REVOKED" in result.evidence_codes
    assert "consent" in result.failed_policies


def test_dnd_hours_wait() -> None:
    """Outside 08:00–19:00 IST, contact is WAIT until the next window."""
    result = evaluate(_context(as_of=AS_OF_NIGHT))
    assert result.decision == PolicyDecision.WAIT
    assert result.policy_name == "dnd_contact"
    assert result.cooldown_until is not None
    assert result.cooldown_until.astimezone(IST).hour == 8
    assert result.allowed_channels == []
    assert "DND_CONTACT_WINDOW" in result.evidence_codes


def test_retry_cooldown_wait() -> None:
    """A retry six hours ago keeps a 24-hour gap WAIT of 18 hours."""
    last = AS_OF - timedelta(hours=6)
    action = RecoveryActionSnapshot(
        action_type=RecoveryActionType.RETRY_PAYMENT,
        execution_status=ExecutionStatus.SUCCEEDED,
        executed_time=last,
        created_at=last,
        retry_number=1,
    )
    result = evaluate(_context(actions=[action]))
    assert result.decision == PolicyDecision.WAIT
    assert result.policy_name == "retry_cooldown"
    assert result.cooldown_until == last + timedelta(hours=24)
    remaining = result.cooldown_until - AS_OF
    assert int(remaining.total_seconds() // 3600) == 18
    assert "18 hours" in result.reason
    assert "RETRY_COOLDOWN" in result.evidence_codes


def test_promise_active_wait() -> None:
    """An open promise waits until the promised date passes."""
    result = evaluate(
        _context(
            promises=[
                PromisePolicySnapshot(
                    status=PromiseStatus.OPEN,
                    promised_date=datetime(2026, 9, 5).date(),
                    promised_amount=99_900,
                )
            ]
        )
    )
    assert result.decision == PolicyDecision.WAIT
    assert result.policy_name == "promise_to_pay"
    assert "2026-09-05" in result.reason
    assert result.cooldown_until is not None
    assert result.allowed_channels == []
    assert "PROMISE_ACTIVE" in result.evidence_codes


def test_promise_broken_allows_escalation() -> None:
    """A lapsed or broken promise ALLOWs the planner to escalate."""
    result = evaluate(
        _context(
            promises=[
                PromisePolicySnapshot(
                    status=PromiseStatus.BROKEN,
                    promised_date=datetime(2026, 8, 30).date(),
                    promised_amount=99_900,
                )
            ]
        )
    )
    assert result.decision == PolicyDecision.ALLOW
    assert "broken" in result.reason.lower()
    assert result.manual_review_required is True
    assert result.priority_score > 50.0
    assert "PROMISE_BROKEN" in result.evidence_codes


def test_already_paid_stops() -> None:
    """A later capture stops recovery immediately."""
    result = evaluate(
        _context(diagnosis=_diagnosis(DiagnosisCategory.ALREADY_PAID))
    )
    assert result.decision == PolicyDecision.STOP
    assert result.policy_name == "already_paid"
    assert "Never retry" in result.reason
    assert result.allowed_channels == []
    assert "already_paid" in result.failed_policies


def test_mandate_revoked_stops() -> None:
    """A revoked mandate stops recovery."""
    result = evaluate(
        _context(
            diagnosis=_diagnosis(DiagnosisCategory.MANDATE_REVOKED),
            subscription=_subscription(mandate=MandateStatus.REVOKED),
        )
    )
    assert result.decision == PolicyDecision.STOP
    assert result.policy_name == "mandate"
    assert "MANDATE_REVOKED" in result.evidence_codes


def test_outage_timeout_wait() -> None:
    """BANK_TIMEOUT / UPI_TIMEOUT wait for a silent retry; no customer notify."""
    result = evaluate(
        _context(diagnosis=_diagnosis(DiagnosisCategory.UPI_TIMEOUT))
    )
    assert result.decision == PolicyDecision.WAIT
    assert result.policy_name == "outage"
    assert result.silent_retry_allowed is True
    assert result.allowed_channels == []
    assert "do not notify" in result.reason.lower()
    assert "OUTAGE_TIMEOUT" in result.evidence_codes


def test_chargeback_active_escalates() -> None:
    """An active dispute escalates and blocks retries."""
    result = evaluate(
        _context(diagnosis=_diagnosis(DiagnosisCategory.CHARGEBACK_ACTIVE))
    )
    assert result.decision == PolicyDecision.ESCALATE
    assert result.policy_name == "chargeback"
    assert result.manual_review_required is True
    assert result.allowed_channels == []
    assert "chargeback" in result.failed_policies


def test_batch_evaluation_summary() -> None:
    """Batch rollup counts STOP / WAIT / ALLOW / ESCALATE and blocked channels."""
    stopped = evaluate(_context(diagnosis=_diagnosis(DiagnosisCategory.ALREADY_PAID)))
    waiting = evaluate(_context(as_of=AS_OF_NIGHT))
    allowed = evaluate(_context())
    escalated = evaluate(
        _context(diagnosis=_diagnosis(DiagnosisCategory.CHARGEBACK_ACTIVE))
    )
    batch = evaluate_many(
        [
            _context(diagnosis=_diagnosis(DiagnosisCategory.ALREADY_PAID)),
            _context(as_of=AS_OF_NIGHT),
            _context(),
            _context(diagnosis=_diagnosis(DiagnosisCategory.CHARGEBACK_ACTIVE)),
        ]
    )
    summary = summarize_decisions([stopped, waiting, allowed, escalated])
    assert summary.total_cases == 4
    assert summary.stopped_cases == 1
    assert summary.waiting_cases == 1
    assert summary.allowed_cases == 1
    assert summary.escalated_cases == 1
    assert summary.decision_distribution[PolicyDecision.STOP] == 1
    assert summary.blocked_channel_counts
    assert batch.summary.total_cases == 4
    assert stopped.policy_version == "recovery_policy_v1"
    assert allowed.decision == PolicyDecision.ALLOW
    assert allowed.allowed_channels
    assert allowed.evaluated_rules
    assert allowed.decision_priority == DECISION_PRIORITY["ALLOW"]
    assert stopped.decision_priority == DECISION_PRIORITY["STOP"]
    assert waiting.decision_priority == DECISION_PRIORITY["WAIT"]
    assert escalated.decision_priority == DECISION_PRIORITY["ESCALATE"]


def test_evaluated_rules_trace_and_decision_priority() -> None:
    """Every decision lists all registry rules and a numeric decision_priority."""
    revoked = evaluate(
        _context(customer=_customer(consent=ConsentStatus.WITHDRAWN))
    )
    names = [row.policy_name for row in revoked.evaluated_rules]
    assert names == list(POLICY_PRECEDENCE)
    for row in revoked.evaluated_rules:
        assert row.policy_name
        assert row.result in RuleVerdict
        assert row.reason
    consent_row = next(row for row in revoked.evaluated_rules if row.policy_name == "consent")
    assert consent_row.result == RuleVerdict.STOP
    assert "revoked" in consent_row.reason.lower()
    assert revoked.decision_priority == 100
    allowed = evaluate(_context())
    waiting = evaluate(_context(as_of=AS_OF_NIGHT))
    assert allowed.decision_priority == 20
    assert waiting.decision_priority == 40
    assert revoked.decision_priority > waiting.decision_priority > allowed.decision_priority
    assert all(row.result == RuleVerdict.PASS for row in allowed.evaluated_rules)
