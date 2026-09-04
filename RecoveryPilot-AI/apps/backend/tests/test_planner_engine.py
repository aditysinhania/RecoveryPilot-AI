"""Deterministic recovery planner tests. No database, Gemini, or Razorpay."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from services.diagnosis.models import DiagnosisCategory, DiagnosisResult, PriorityBucket
from services.planner.models import (
    CustomerBehaviourSnapshot,
    PlannerContext,
    PlannerCustomerSnapshot,
    PlannerStrategy,
)
from services.planner.planner_engine import plan, plan_many, summarize_plans
from services.policy.models import PolicyDecision, PolicyDecisionResult
from shared.enums import CustomerSegment

IST = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 9, 2, 12, 0, tzinfo=IST)


def _diagnosis(
    category: DiagnosisCategory,
    *,
    confidence: float = 0.8,
    payment_id=None,
    codes: list[str] | None = None,
) -> DiagnosisResult:
    """Minimal diagnosis result for planner tests."""
    from services.diagnosis.models import EvidenceItem

    pay_id = payment_id or uuid4()
    items = [
        EvidenceItem(code=code, weight=0.5, message=code)
        for code in (codes or [])
    ]
    return DiagnosisResult(
        diagnosis=category,
        confidence=confidence,
        priority_score=50.0,
        priority_bucket=PriorityBucket.MEDIUM,
        evidence=["synthetic"],
        evidence_items=items,
        triggered_rules=[],
        recommended_action_placeholder="RETRY_PAYMENT",
        diagnosis_model="recovery_diagnosis_v1",
        diagnosis_version="1.0.0",
        generated_at=AS_OF,
        payment_id=pay_id,
    )


def _policy(
    decision: PolicyDecision,
    *,
    policy_name: str = "default_allow",
    allowed: list[str] | None = None,
    blocked: list[str] | None = None,
    cooldown_until: datetime | None = None,
    evidence: list[str] | None = None,
    silent: bool = False,
    triggered: list[str] | None = None,
    evaluated_at: datetime | None = None,
) -> PolicyDecisionResult:
    """Minimal policy decision for planner tests."""
    return PolicyDecisionResult(
        policy_name=policy_name,
        decision=decision,
        reason=f"{decision.value} from {policy_name}",
        evidence_codes=evidence or [],
        priority_score=50.0,
        decision_priority=40 if decision == PolicyDecision.WAIT else 20,
        evaluated_at=evaluated_at or AS_OF,
        cooldown_until=cooldown_until,
        allowed_channels=allowed if allowed is not None else ["WhatsApp", "SMS", "Email"],
        blocked_channels=blocked if blocked is not None else ["Voice"],
        policy_version="recovery_policy_v1",
        triggered_policies=triggered or ([policy_name] if policy_name != "default_allow" else []),
        silent_retry_allowed=silent,
    )


def _context(
    diagnosis: DiagnosisResult,
    policy: PolicyDecisionResult,
    *,
    as_of: datetime = AS_OF,
    salary: bool = False,
    amount: int = 99_900,
    promised: date | None = None,
    outage_ended_at: datetime | None = None,
    segment: CustomerSegment = CustomerSegment.AT_RISK,
) -> PlannerContext:
    """Assemble a planner context."""
    return PlannerContext(
        as_of=as_of,
        diagnosis=diagnosis,
        policy=policy,
        customer=PlannerCustomerSnapshot(
            id=uuid4(),
            segment=segment,
            salary_dependent=salary,
            timezone="Asia/Kolkata",
        ),
        payment_amount=amount,
        behaviour=CustomerBehaviourSnapshot(
            previous_success_rate=0.7,
            salary_dependent=salary,
            pays_within_hours_of_salary=24,
        ),
        promised_date=promised,
        outage_ended_at=outage_ended_at,
        timezone="Asia/Kolkata",
        recovery_case_id=uuid4(),
    )


def test_salary_retry_timing() -> None:
    """Payday wait lands at 09:15 IST after cooldown, inside 09:00–11:00."""
    as_of = datetime(2026, 9, 1, 12, 0, tzinfo=IST)
    cooldown = datetime(2026, 9, 1, 21, 0, tzinfo=IST)
    result = plan(
        _context(
            _diagnosis(DiagnosisCategory.INSUFFICIENT_FUNDS),
            _policy(
                PolicyDecision.WAIT,
                policy_name="retry_cooldown",
                cooldown_until=cooldown,
                evidence=["RETRY_COOLDOWN"],
                evaluated_at=as_of,
            ),
            as_of=as_of,
            salary=True,
        )
    )
    assert result.strategy == PlannerStrategy.WAIT_FOR_PAYDAY
    local = result.scheduled_at.astimezone(IST)
    assert local.year == 2026 and local.month == 9 and local.day == 2
    assert local.hour == 9 and local.minute == 15
    assert 9 <= local.hour < 11
    assert "Sept 2" in result.timing_reason
    assert "21:00" in result.timing_reason
    assert result.retry_window is not None
    assert "09:00–11:00" in result.retry_window.label


def test_outage_retry_timing() -> None:
    """Silent outage retry is 30–90 minutes after the window ends."""
    as_of = datetime(2026, 9, 2, 10, 0, tzinfo=IST)
    ended = datetime(2026, 9, 2, 10, 0, tzinfo=IST)
    result = plan(
        _context(
            _diagnosis(DiagnosisCategory.UPI_TIMEOUT),
            _policy(
                PolicyDecision.WAIT,
                policy_name="outage",
                evidence=["OUTAGE_TIMEOUT"],
                silent=True,
                evaluated_at=as_of,
            ),
            as_of=as_of,
            outage_ended_at=ended,
        )
    )
    assert result.strategy == PlannerStrategy.RETRY_SILENTLY
    delay = result.scheduled_at - ended
    minutes = delay.total_seconds() / 60.0
    assert 30 <= minutes <= 90
    assert result.scheduled_at == ended + timedelta(minutes=60)


def test_promise_scheduling() -> None:
    """Promise plans fire on the promised calendar date."""
    promised = date(2026, 9, 5)
    result = plan(
        _context(
            _diagnosis(DiagnosisCategory.INSUFFICIENT_FUNDS),
            _policy(
                PolicyDecision.WAIT,
                policy_name="promise_to_pay",
                evidence=["PROMISE_ACTIVE"],
            ),
            promised=promised,
        )
    )
    assert result.strategy == PlannerStrategy.HONOUR_PROMISE_TO_PAY
    local = result.scheduled_at.astimezone(IST)
    assert local.date() == promised
    assert local.hour == 9 and local.minute == 15
    assert promised.isoformat() in result.timing_reason


def test_mandate_strategy() -> None:
    """Expired card + ALLOW requests a new mandate, with human fallback."""
    result = plan(
        _context(
            _diagnosis(DiagnosisCategory.CARD_EXPIRED),
            _policy(PolicyDecision.ALLOW, policy_name="default_allow"),
        )
    )
    assert result.strategy == PlannerStrategy.REQUEST_NEW_MANDATE
    assert result.fallback_strategy == PlannerStrategy.ESCALATE_TO_HUMAN


def test_already_paid_stop_strategy() -> None:
    """Already-paid STOP plans halt recovery."""
    result = plan(
        _context(
            _diagnosis(DiagnosisCategory.ALREADY_PAID, codes=["ALREADY_PAID"]),
            _policy(
                PolicyDecision.STOP,
                policy_name="already_paid",
                evidence=["ALREADY_PAID"],
                triggered=["already_paid"],
            ),
        )
    )
    assert result.strategy == PlannerStrategy.STOP_RECOVERY
    assert result.fallback_strategy == PlannerStrategy.STOP_RECOVERY
    assert result.expected_recovery_probability == 0.0
    assert result.recommended_channels == ["DASHBOARD_NOTIFICATION"]


def test_silent_retry() -> None:
    """Rail timeout WAIT uses RETRY_SILENTLY and does not notify the customer."""
    result = plan(
        _context(
            _diagnosis(DiagnosisCategory.BANK_TIMEOUT),
            _policy(
                PolicyDecision.WAIT,
                policy_name="outage",
                evidence=["OUTAGE_TIMEOUT"],
                silent=True,
            ),
            outage_ended_at=datetime(2026, 9, 2, 10, 0, tzinfo=IST),
        )
    )
    assert result.strategy == PlannerStrategy.RETRY_SILENTLY
    assert result.fallback_strategy == PlannerStrategy.SWITCH_PAYMENT_METHOD
    notify = {"SMS", "WhatsApp", "Voice", "Email"}
    assert notify.isdisjoint(set(result.recommended_channels))
    assert "DASHBOARD_NOTIFICATION" in result.recommended_channels


def test_channel_blocking() -> None:
    """Planner never recommends a policy-blocked channel."""
    result = plan(
        _context(
            _diagnosis(DiagnosisCategory.AUTHENTICATION_FAILED),
            _policy(
                PolicyDecision.ALLOW,
                allowed=["WhatsApp", "SMS", "Email"],
                blocked=["Voice"],
            ),
        )
    )
    assert result.strategy == PlannerStrategy.SWITCH_PAYMENT_METHOD
    assert "Voice" not in result.recommended_channels
    assert "Voice" in result.channel_reason or "Blocked" in result.channel_reason


def test_fallback_generation() -> None:
    """WAIT_FOR_PAYDAY always carries SEND_PAYMENT_LINK as fallback."""
    result = plan(
        _context(
            _diagnosis(DiagnosisCategory.INSUFFICIENT_FUNDS),
            _policy(PolicyDecision.WAIT, policy_name="retry_cooldown"),
            salary=True,
            as_of=datetime(2026, 8, 30, 12, 0, tzinfo=IST),
        )
    )
    assert result.strategy == PlannerStrategy.WAIT_FOR_PAYDAY
    assert result.fallback_strategy == PlannerStrategy.SEND_PAYMENT_LINK
    assert result.plan_version == "recovery_planner_v1"
    assert result.planner_version == "1.0.0"
    assert result.reasoning_steps
    assert result.reasoning
    assert 0.0 <= result.strategy_confidence <= 1.0
    assert result.confidence_reasoning
    assert "WAIT_FOR_PAYDAY" in result.confidence_reasoning
    assert "diagnosis" in result.confidence_reasoning.lower()


def test_strategy_confidence_uses_diagnosis_policy_history_timing() -> None:
    """Higher diagnosis confidence raises strategy_confidence; STOP stays certain."""
    low = plan(
        _context(
            _diagnosis(DiagnosisCategory.INSUFFICIENT_FUNDS, confidence=0.40),
            _policy(PolicyDecision.WAIT, policy_name="retry_cooldown"),
            salary=True,
            as_of=datetime(2026, 8, 30, 12, 0, tzinfo=IST),
        )
    )
    high = plan(
        _context(
            _diagnosis(DiagnosisCategory.INSUFFICIENT_FUNDS, confidence=0.95),
            _policy(
                PolicyDecision.WAIT,
                policy_name="retry_cooldown",
                cooldown_until=datetime(2026, 8, 30, 18, 0, tzinfo=IST),
            ),
            salary=True,
            as_of=datetime(2026, 8, 30, 12, 0, tzinfo=IST),
        )
    )
    stopped = plan(
        _context(
            _diagnosis(DiagnosisCategory.ALREADY_PAID, confidence=0.90, codes=["ALREADY_PAID"]),
            _policy(
                PolicyDecision.STOP,
                policy_name="already_paid",
                evidence=["ALREADY_PAID"],
                triggered=["already_paid"],
            ),
        )
    )
    assert high.strategy_confidence > low.strategy_confidence
    assert 0.05 <= low.strategy_confidence <= 0.99
    assert stopped.strategy == PlannerStrategy.STOP_RECOVERY
    assert stopped.strategy_confidence >= 0.7
    assert "STOP" in stopped.confidence_reasoning
    for text in (low.confidence_reasoning, high.confidence_reasoning):
        assert "diagnosis" in text.lower()
        assert "policy" in text.lower()
        assert "success rate" in text.lower()
        assert "timing" in text.lower()


def test_batch_planner_summary() -> None:
    """Batch rollup counts strategies, retries, channels, value, and cost."""
    payday = _context(
        _diagnosis(DiagnosisCategory.INSUFFICIENT_FUNDS),
        _policy(PolicyDecision.WAIT, policy_name="retry_cooldown"),
        salary=True,
        as_of=datetime(2026, 8, 30, 12, 0, tzinfo=IST),
    )
    silent = _context(
        _diagnosis(DiagnosisCategory.UPI_TIMEOUT),
        _policy(
            PolicyDecision.WAIT,
            policy_name="outage",
            silent=True,
            evidence=["OUTAGE_TIMEOUT"],
        ),
        outage_ended_at=datetime(2026, 9, 2, 10, 0, tzinfo=IST),
    )
    stopped = _context(
        _diagnosis(DiagnosisCategory.ALREADY_PAID),
        _policy(PolicyDecision.STOP, policy_name="already_paid"),
    )
    mandate = _context(
        _diagnosis(DiagnosisCategory.CARD_EXPIRED),
        _policy(PolicyDecision.ALLOW),
    )
    batch = plan_many([payday, silent, stopped, mandate])
    summary = summarize_plans(batch.results)
    assert summary.total_cases == 4
    assert summary.strategy_distribution[PlannerStrategy.WAIT_FOR_PAYDAY] == 1
    assert summary.strategy_distribution[PlannerStrategy.RETRY_SILENTLY] == 1
    assert summary.strategy_distribution[PlannerStrategy.STOP_RECOVERY] == 1
    assert summary.strategy_distribution[PlannerStrategy.REQUEST_NEW_MANDATE] == 1
    assert summary.scheduled_retries == 2
    assert summary.channel_usage
    assert summary.estimated_communication_cost >= 0
    assert summary.expected_recovered_revenue == summary.estimated_recovery_value
    assert batch.results[0].generated_at
