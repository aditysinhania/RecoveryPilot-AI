"""Action orchestrator tests. No live Razorpay, SMS, WhatsApp, or email."""

from __future__ import annotations

import random
from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from services.action_orchestrator.gates import evaluate_gates
from services.action_orchestrator.models import (
    ActionCustomerSnapshot,
    ActionPaymentSnapshot,
    OrchestratorContext,
)
from services.action_orchestrator.orchestrator import ActionNotFoundError, ActionOrchestrator
from services.action_orchestrator.persistence import InMemoryActionStore
from services.communications.rate_limit import RateLimiter
from services.communications.router import CommunicationRouter
from services.executor.idempotency import make_idempotency_key
from services.planner.models import PlannerStrategy, RecoveryPlan
from services.policy.models import PolicyDecision, PolicyDecisionResult
from services.razorpay_actions.errors import RazorpayActionTransientError
from services.razorpay_actions.models import RazorpayActionResult
from services.razorpay_actions.service import RazorpayActionService
from services.scheduler.backoff import BACKOFF_STEPS, JITTER_WINDOWS, MAX_RETRY_ATTEMPTS, next_backoff
from services.scheduler.service import ActionScheduler
from services.scheduler.store import SchedulerStore

IST = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 9, 5, 12, 0, tzinfo=IST)


class FakeRazorpayClient:
    """In-memory Sandbox double. Optional transient failures for backoff tests."""

    def __init__(self, *, fail_times: int = 0) -> None:
        self.calls: list[str] = []
        self._fail_times = fail_times
        self._failures = 0
        self._cache: dict[str, RazorpayActionResult] = {}

    def create_payment_link(self, payload: dict, *, idempotency_key: str) -> RazorpayActionResult:
        """Create or replay a mock payment link."""
        return self._result("payment_link", payload, idempotency_key, short_url=True)

    def create_order(self, payload: dict, *, idempotency_key: str) -> RazorpayActionResult:
        """Create or replay a mock retry order."""
        return self._result("retry_order", payload, idempotency_key, short_url=False)

    def create_mandate_session(self, payload: dict, *, idempotency_key: str) -> RazorpayActionResult:
        """Create or replay a mock mandate session."""
        return self._result("mandate_session", payload, idempotency_key, short_url=True)

    def _result(
        self,
        kind: str,
        payload: dict,
        idempotency_key: str,
        *,
        short_url: bool,
    ) -> RazorpayActionResult:
        self.calls.append(kind)
        if self._failures < self._fail_times:
            self._failures += 1
            raise RazorpayActionTransientError("sandbox timeout")
        cached = self._cache.get(idempotency_key)
        if cached is not None:
            return cached
        result = RazorpayActionResult(
            kind=kind,
            resource_id=f"{kind}_{idempotency_key[-8:]}",
            status="created",
            short_url=f"https://rzp.io/i/{kind}" if short_url else None,
            mock=True,
            payload={"amount": payload.get("amount"), "notes": payload.get("notes")},
        )
        self._cache[idempotency_key] = result
        return result


def _plan(
    strategy: PlannerStrategy,
    *,
    scheduled_at: datetime = AS_OF,
    case_id=None,
    channels: list[str] | None = None,
    fallback: PlannerStrategy = PlannerStrategy.SEND_PAYMENT_LINK,
) -> RecoveryPlan:
    """Minimal RecoveryPlan for orchestrator tests."""
    case = case_id if case_id is not None else uuid4()
    return RecoveryPlan(
        strategy=strategy,
        scheduled_at=scheduled_at,
        reasoning=f"plan {strategy.value}",
        recommended_channels=channels or ["WhatsApp", "SMS"],
        fallback_strategy=fallback,
        expected_outcome="sandbox",
        expected_recovery_probability=0.6,
        plan_version="recovery_planner_v1",
        planner_version="1.0.0",
        generated_at=AS_OF,
        recovery_case_id=case,
        payment_id=uuid4(),
        estimated_recovery_value=99_900,
        features={"diagnosis": "INSUFFICIENT_FUNDS", "policy_decision": "ALLOW"},
    )


def _policy(
    decision: PolicyDecision = PolicyDecision.ALLOW,
    *,
    cooldown_until: datetime | None = None,
    allowed: list[str] | None = None,
    blocked: list[str] | None = None,
) -> PolicyDecisionResult:
    """Minimal policy decision. Engine is not invoked."""
    return PolicyDecisionResult(
        policy_name="test_policy",
        decision=decision,
        reason=f"{decision.value} in test",
        evidence_codes=[],
        priority_score=50.0,
        decision_priority=20,
        evaluated_at=AS_OF,
        cooldown_until=cooldown_until,
        allowed_channels=allowed if allowed is not None else ["WhatsApp", "SMS", "Email"],
        blocked_channels=blocked if blocked is not None else ["Voice"],
        policy_version="recovery_policy_v1",
        triggered_policies=[],
    )


def _context(
    plan: RecoveryPlan,
    policy: PolicyDecisionResult | None = None,
    *,
    as_of: datetime = AS_OF,
    consent: bool = True,
) -> OrchestratorContext:
    """Assemble orchestrator snapshots around a plan."""
    return OrchestratorContext(
        as_of=as_of,
        plan=plan,
        policy=policy or _policy(),
        customer=ActionCustomerSnapshot(
            id=uuid4(),
            full_name="Test Member",
            email="member@example.com",
            phone="+919800000000",
            consent_granted=consent,
            merchant_id=uuid4(),
        ),
        payment=ActionPaymentSnapshot(id=uuid4(), amount=99_900, currency="INR"),
        request_id="req-test",
        correlation_id="corr-test",
        merchant_name="FitLife Gym",
    )


def _orchestrator(client: FakeRazorpayClient | None = None) -> tuple[ActionOrchestrator, FakeRazorpayClient, InMemoryActionStore]:
    """Wire orchestrator with in-memory store, mock Razorpay, and mock comms."""
    store = InMemoryActionStore()
    fake = client or FakeRazorpayClient()
    orch = ActionOrchestrator(
        store=store,
        razorpay=RazorpayActionService(fake),
        comms=CommunicationRouter(),
        scheduler=ActionScheduler(store=SchedulerStore()),
    )
    return orch, fake, store


def test_next_backoff_sequence() -> None:
    """Backoff stays 1m/5m/30m/2h with documented jitter, then dead-letter."""
    for attempt, (base, window) in enumerate(zip(BACKOFF_STEPS, JITTER_WINDOWS, strict=True)):
        delay = next_backoff(attempt, rng=random.Random(attempt + 7))
        assert delay is not None
        assert base - window <= delay <= base + window
    assert next_backoff(MAX_RETRY_ATTEMPTS) is None


def test_scheduler_queue_metrics() -> None:
    """Pending future jobs are scheduled; overdue pending jobs are delayed."""
    store = SchedulerStore()
    sched = ActionScheduler(store=store)
    future = AS_OF + timedelta(hours=2)
    past = AS_OF - timedelta(minutes=5)
    case_id = uuid4()
    sched.schedule(execution_id=uuid4(), recovery_case_id=case_id, run_at=future, reason="WAIT_FOR_PAYDAY")
    delayed_id = uuid4()
    sched.schedule(execution_id=delayed_id, recovery_case_id=case_id, run_at=past, reason="BACKOFF")
    running_id = uuid4()
    sched.schedule(execution_id=running_id, recovery_case_id=case_id, run_at=past, reason="COOLDOWN")
    store.mark_running(running_id)
    dead_id = uuid4()
    sched.schedule(execution_id=dead_id, recovery_case_id=case_id, run_at=past, reason="BACKOFF")
    store.complete(dead_id, status="dead_letter")
    metrics = sched.queue_metrics(AS_OF)
    assert metrics.scheduled == 1
    assert metrics.delayed == 1
    assert metrics.running == 1
    assert metrics.dead_letter == 1
    claimed = sched.claim_due(AS_OF)
    assert {job.execution_id for job in claimed} == {delayed_id}
    after = sched.queue_metrics(AS_OF)
    assert after.running == 2
    assert after.delayed == 0


def test_policy_deny_blocks_razorpay() -> None:
    """DENY skips Sandbox and records CANCELLED with an audit skip event."""
    orch, fake, store = _orchestrator()
    plan = _plan(PlannerStrategy.RETRY_PAYMENT)
    result = orch.run(_context(plan, _policy(PolicyDecision.DENY)))
    assert result.display_status == "CANCELLED"
    assert fake.calls == []
    assert any(item["event_type"].value == "ACTION_SKIPPED" for item in store.audits)


def test_cooldown_schedules_instead_of_charge() -> None:
    """Active cooldown defers execution and enqueues the scheduler."""
    orch, fake, store = _orchestrator()
    cooldown = AS_OF + timedelta(hours=2)
    plan = _plan(PlannerStrategy.RETRY_PAYMENT)
    result = orch.run(_context(plan, _policy(cooldown_until=cooldown)))
    assert result.display_status == "SCHEDULED"
    assert result.scheduled_time == cooldown
    assert fake.calls == []
    assert any(item["event_type"].value == "ACTION_SCHEDULED" for item in store.audits)


def test_wait_for_payday_schedules_at_plan_time() -> None:
    """WAIT_FOR_PAYDAY in the future is scheduled, not charged."""
    orch, fake, _store = _orchestrator()
    payday = AS_OF + timedelta(days=3)
    plan = _plan(PlannerStrategy.WAIT_FOR_PAYDAY, scheduled_at=payday)
    result = orch.run(_context(plan))
    assert result.display_status == "SCHEDULED"
    assert result.scheduled_time == payday
    assert fake.calls == []
    assert result.action_chip == "Scheduled"


def test_payment_link_and_mock_whatsapp() -> None:
    """SEND_PAYMENT_LINK creates a Sandbox link and a mock WhatsApp delivery."""
    orch, fake, store = _orchestrator()
    plan = _plan(PlannerStrategy.SEND_PAYMENT_LINK)
    result = orch.run(_context(plan))
    assert result.display_status == "SUCCESS"
    assert result.payment_link
    assert fake.calls == ["payment_link"]
    assert result.delivery_status == "DELIVERED"
    assert result.deliveries[0].channel == "WhatsApp"
    assert result.deliveries[0].provider == "sandbox_mock"
    assert any(item["payload"].get("request_id") == "req-test" for item in store.audits)
    assert any(item["payload"].get("correlation_id") == "corr-test" for item in store.audits)


def test_retry_silently_skips_comms() -> None:
    """RETRY_SILENTLY charges Sandbox but does not notify the customer."""
    orch, fake, _store = _orchestrator()
    result = orch.run(_context(_plan(PlannerStrategy.RETRY_SILENTLY)))
    assert result.display_status == "SUCCESS"
    assert fake.calls == ["retry_order"]
    assert result.delivery_status == "SKIPPED"
    assert result.deliveries[0].skipped_reason == "RETRY_SILENTLY"


def test_mandate_session_uses_card_update() -> None:
    """REQUEST_NEW_MANDATE opens a mandate/card-update session."""
    orch, fake, _store = _orchestrator()
    result = orch.run(_context(_plan(PlannerStrategy.REQUEST_NEW_MANDATE)))
    assert result.display_status == "SUCCESS"
    assert fake.calls == ["mandate_session"]
    assert result.payment_link


def test_blocked_channel_falls_back() -> None:
    """WhatsApp blocked → SMS mock provider is used instead."""
    orch, _fake, _store = _orchestrator()
    plan = _plan(PlannerStrategy.SEND_PAYMENT_LINK, channels=["WhatsApp", "SMS"])
    policy = _policy(allowed=["SMS", "Email"], blocked=["WhatsApp"])
    result = orch.run(_context(plan, policy))
    assert result.deliveries[0].channel == "SMS"


def test_idempotent_replay_does_not_double_charge() -> None:
    """Same case+strategy+time returns the stored execution without a second Razorpay call."""
    orch, fake, _store = _orchestrator()
    ctx = _context(_plan(PlannerStrategy.RETRY_PAYMENT))
    first = orch.run(ctx)
    second = orch.run(ctx)
    assert first.execution_id == second.execution_id
    assert second.replayed is True
    assert fake.calls == ["retry_order"]
    key = make_idempotency_key(ctx.plan.recovery_case_id, ctx.plan.strategy.value, ctx.plan.scheduled_at)
    assert first.idempotency_key == key


def test_transient_backoff_then_dead_letter() -> None:
    """Four backoffs then dead-letter. Razorpay is not called after the cap."""
    fake = FakeRazorpayClient(fail_times=99)
    orch, _client, store = _orchestrator(fake)
    ctx = _context(_plan(PlannerStrategy.RETRY_PAYMENT))
    statuses: list[str] = []
    for _ in range(MAX_RETRY_ATTEMPTS + 1):
        result = orch.run(ctx)
        statuses.append(result.display_status)
    assert statuses[-1] == "FAILED"
    assert result.dead_lettered is True
    assert all(row.action_metadata.get("dead_lettered") for row in store.actions.values() if row.id == result.execution_id)
    assert fake.calls.count("retry_order") == MAX_RETRY_ATTEMPTS + 1


def test_replay_unknown_execution_raises() -> None:
    """Replay of a missing id is a domain miss."""
    orch, _fake, _store = _orchestrator()
    try:
        orch.replay(uuid4(), _context(_plan(PlannerStrategy.RETRY_PAYMENT)))
        raise AssertionError("expected ActionNotFoundError")
    except ActionNotFoundError:
        pass


def test_force_schedule_skips_sandbox() -> None:
    """POST schedule persists SCHEDULED even for RETRY_PAYMENT."""
    orch, fake, _store = _orchestrator()
    result = orch.run(_context(_plan(PlannerStrategy.RETRY_PAYMENT)), force_schedule=True)
    assert result.display_status == "SCHEDULED"
    assert fake.calls == []


def test_rate_limiter_blocks_burst() -> None:
    """Second SMS in the same window is rate-limited when the cap is 1."""
    limiter = RateLimiter(limits={"SMS": 1, "WhatsApp": 1, "Email": 1})
    merchant = "m1"
    assert limiter.allow(merchant_key=merchant, channel="SMS") is True
    assert limiter.allow(merchant_key=merchant, channel="SMS") is False


def test_wait_due_runs_fallback_payment_link() -> None:
    """When payday arrives, the wait row completes and fallback hits Sandbox."""
    orch, fake, store = _orchestrator()
    payday = AS_OF + timedelta(days=1)
    plan = _plan(
        PlannerStrategy.WAIT_FOR_PAYDAY,
        scheduled_at=payday,
        fallback=PlannerStrategy.SEND_PAYMENT_LINK,
    )
    scheduled = orch.run(_context(plan, as_of=AS_OF))
    assert scheduled.display_status == "SCHEDULED"
    record = store.get(scheduled.execution_id)
    assert record is not None
    due = orch.run_due(record, _context(plan, as_of=payday))
    assert due.display_status == "SUCCESS"
    assert "payment_link" in fake.calls
    wait_row = store.get(scheduled.execution_id)
    assert wait_row is not None
    assert wait_row.action_metadata.get("display_status") == "SUCCESS"


def test_audit_payload_has_ids() -> None:
    """Every outbound action writes request_id and correlation_id onto audit."""
    orch, _fake, store = _orchestrator()
    orch.run(_context(_plan(PlannerStrategy.SEND_PAYMENT_LINK)))
    payloads = [item["payload"] for item in store.audits]
    assert payloads
    assert all(item.get("request_id") == "req-test" for item in payloads)
    assert all(item.get("correlation_id") == "corr-test" for item in payloads)


def test_evaluate_gates_stop() -> None:
    """STOP is a permanent block."""
    plan = _plan(PlannerStrategy.RETRY_PAYMENT)
    gate = evaluate_gates(plan, _policy(PolicyDecision.STOP), as_of=AS_OF)
    assert gate.block is True
    assert gate.allow_now is False
