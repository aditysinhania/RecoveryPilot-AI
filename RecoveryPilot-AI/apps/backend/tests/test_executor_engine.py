"""Deterministic recovery executor tests. No database, Gemini, or Razorpay."""

from __future__ import annotations

from datetime import datetime, timedelta
from uuid import uuid4
from zoneinfo import ZoneInfo

from services.executor.constants import (
    EXECUTOR_VERSION,
    PAYMENT_LINK_TTL,
    TRACE_AUDIT,
    TRACE_IDEMPOTENCY,
    TRACE_PAYMENT_LINK,
    TRACE_RETRY,
    TRACE_START,
    TRACE_WEBHOOK,
)
from services.executor.execution_log import ExecutionLogStore
from services.executor.executor_engine import execute, execute_batch, summarize_executions
from services.executor.idempotency import make_idempotency_key
from services.executor.models import (
    ExecutionStatus,
    ExecutorContext,
    RetryOutcome,
)
from services.executor.webhook_processor import process_webhooks, webhooks_for_retry
from services.executor_service import execute_plan
from services.planner.models import PlannerStrategy, RecoveryPlan
from shared.enums import PaymentMethod

IST = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 9, 2, 12, 0, tzinfo=IST)


def _plan(
    strategy: PlannerStrategy | str,
    *,
    scheduled_at: datetime = AS_OF,
    probability: float = 0.5,
    case_id=None,
    payment_id=None,
    amount: int = 99_900,
    diagnosis: str = "INSUFFICIENT_FUNDS",
    policy: str = "ALLOW",
) -> RecoveryPlan:
    """Minimal RecoveryPlan for executor tests."""
    case = case_id if case_id is not None else uuid4()
    pay = payment_id if payment_id is not None else uuid4()
    kwargs = {
        "strategy": strategy,
        "scheduled_at": scheduled_at,
        "reasoning": f"plan {strategy}",
        "recommended_channels": ["WhatsApp"],
        "fallback_strategy": PlannerStrategy.SEND_PAYMENT_LINK,
        "expected_outcome": "simulated",
        "expected_recovery_probability": probability,
        "plan_version": "recovery_planner_v1",
        "planner_version": "1.0.0",
        "generated_at": AS_OF,
        "recovery_case_id": case,
        "payment_id": pay,
        "estimated_recovery_value": amount,
        "features": {
            "diagnosis": diagnosis,
            "policy_decision": policy,
            "payment_amount": amount,
        },
    }
    if isinstance(strategy, str) and strategy not in PlannerStrategy._value2member_map_:
        return RecoveryPlan.model_construct(**kwargs)
    return RecoveryPlan(**kwargs)


def _context(
    plan: RecoveryPlan,
    *,
    as_of: datetime = AS_OF,
    amount: int = 99_900,
    method: PaymentMethod = PaymentMethod.UPI,
) -> ExecutorContext:
    """Assemble executor snapshots around a plan."""
    return ExecutorContext(
        as_of=as_of,
        plan=plan,
        recovery_case_id=plan.recovery_case_id,
        payment_id=plan.payment_id,
        payment_amount=amount,
        payment_method=method,
        diagnosis=str(plan.features.get("diagnosis")) if plan.features else None,
        policy_decision=str(plan.features.get("policy_decision")) if plan.features else None,
    )


def test_duplicate_execution() -> None:
    """Same case + strategy + scheduled time is not executed twice."""
    store = ExecutionLogStore()
    ctx = _context(_plan(PlannerStrategy.RETRY_PAYMENT, probability=0.9))
    first = execute(ctx, store)
    second = execute(ctx, store)
    assert first.status != ExecutionStatus.DUPLICATE_SKIPPED
    assert second.status == ExecutionStatus.DUPLICATE_SKIPPED
    assert second.idempotent is True
    assert second.execution_id == first.execution_id
    assert second.idempotency_key == first.idempotency_key
    assert second.success is False
    assert second.recovered_value == 0
    assert second.audit is not None
    assert second.audit.actor == "EXECUTOR_ENGINE"
    skip_names = [step.step for step in second.execution_trace]
    assert skip_names == [
        TRACE_IDEMPOTENCY,
        TRACE_START,
        TRACE_RETRY,
        TRACE_WEBHOOK,
        TRACE_AUDIT,
    ]
    assert second.execution_trace[0].status == "DUPLICATE_SKIPPED"
    assert second.execution_trace[1].status == "SKIPPED"
    assert all(step.timestamp == AS_OF for step in second.execution_trace)


def test_retry_success() -> None:
    """High planner probability forces a successful simulated retry."""
    result = execute(_context(_plan(PlannerStrategy.RETRY_PAYMENT, probability=0.9)))
    assert result.execution_type == "EXECUTE_RETRY"
    assert result.success is True
    assert result.outcome == RetryOutcome.SUCCESS
    assert result.status == ExecutionStatus.SUCCEEDED
    assert result.recovered_value == 99_900
    assert result.webhook_event_id is not None
    types = {item.event_type for item in result.webhooks}
    assert "payment.authorized" in types
    assert "payment.captured" in types
    assert "subscription.charged" in types
    assert result.executor_version == EXECUTOR_VERSION
    assert result.idempotent is False
    assert result.planner_strategy == "RETRY_PAYMENT"
    assert result.diagnosis == "INSUFFICIENT_FUNDS"
    assert result.policy_decision == "ALLOW"
    assert result.human_summary


def test_retry_failure() -> None:
    """Very low planner probability never yields SUCCESS."""
    result = execute(_context(_plan(PlannerStrategy.RETRY_SILENTLY, probability=0.05)))
    assert result.execution_type == "EXECUTE_RETRY"
    assert result.success is False
    assert result.outcome != RetryOutcome.SUCCESS
    assert result.status in {
        ExecutionStatus.FAILED,
        ExecutionStatus.TIMEOUT,
    }
    assert result.recovered_value == 0
    assert any(item.event_type == "payment.failed" for item in result.webhooks)


def test_payment_link_generation() -> None:
    """SEND_PAYMENT_LINK yields a deterministic 48h hosted link."""
    plan = _plan(PlannerStrategy.SEND_PAYMENT_LINK, probability=0.4)
    result = execute(_context(plan))
    assert result.execution_type == "GENERATE_PAYMENT_LINK"
    assert result.status == ExecutionStatus.GENERATED
    assert result.success is True
    assert result.outcome == "GENERATED"
    assert result.payment_link_id is not None
    assert result.payment_link_id.startswith("plink_")
    assert result.metadata["status"] == "GENERATED"
    assert result.metadata["payment_method"]
    assert result.metadata["merchant_reference"]
    expires = result.metadata["expires_at"]
    assert expires - plan.scheduled_at == PAYMENT_LINK_TTL


def test_webhook_replay() -> None:
    """The same Razorpay-shaped event id is marked replay on second delivery."""
    store = ExecutionLogStore()
    ctx = _context(_plan(PlannerStrategy.RETRY_PAYMENT, probability=0.9))
    events = webhooks_for_retry(ctx, RetryOutcome.SUCCESS, AS_OF)
    first = process_webhooks(events, store)
    second = process_webhooks(events, store)
    assert first and all(not item.replay for item in first)
    assert second and all(item.replay for item in second)
    replayed = execute(ctx, store)
    assert replayed.status == ExecutionStatus.WEBHOOK_REPLAY
    assert replayed.success is False
    assert replayed.recovered_value == 0
    assert replayed.webhooks
    assert all(item.replay for item in replayed.webhooks)


def test_card_update_session() -> None:
    """REQUEST_NEW_MANDATE generates a card-update session without Razorpay."""
    result = execute(_context(_plan(PlannerStrategy.REQUEST_NEW_MANDATE)))
    assert result.execution_type == "REQUEST_CARD_UPDATE"
    assert result.status == ExecutionStatus.GENERATED
    assert result.metadata["update_session_id"].startswith("cs_")
    assert result.metadata["status"] == "CREATED"
    assert result.metadata["expires_at"]
    assert any(item.event_type == "subscription.pending" for item in result.webhooks)


def test_unknown_strategy() -> None:
    """Unmapped planner strategy returns UNKNOWN_STRATEGY and does not raise."""
    plan = _plan("NOT_A_STRATEGY")
    result = execute(_context(plan))
    assert result.status == ExecutionStatus.UNKNOWN_STRATEGY
    assert result.success is False
    assert result.outcome == "UNKNOWN_STRATEGY"
    assert result.recovered_value == 0


def test_batch_execution_summary() -> None:
    """Batch rollup counts executed, successes, duplicates, links, and retries."""
    retry = _plan(PlannerStrategy.RETRY_PAYMENT, probability=0.9)
    link = _plan(PlannerStrategy.SEND_PAYMENT_LINK, probability=0.4)
    unknown = _plan("NOT_A_STRATEGY")
    batch = execute_batch(
        [retry, link, retry, unknown],
        as_of=AS_OF,
    )
    summary = batch.summary
    assert summary.total_plans == 4
    assert summary.executed == 3
    assert summary.duplicates == 1
    assert summary.successes == 2
    assert summary.failures >= 1
    assert summary.payment_links_generated == 1
    assert summary.retries_scheduled == 1
    assert summary.estimated_recovered_value == 99_900
    rolled = summarize_executions(batch.results)
    assert rolled.duplicates == summary.duplicates


def test_idempotency_key_stability() -> None:
    """Same case + strategy + scheduled time always hashes to the same key."""
    case_id = uuid4()
    stamp = datetime(2026, 9, 2, 9, 15, tzinfo=IST)
    first = make_idempotency_key(case_id, "RETRY_PAYMENT", stamp)
    second = make_idempotency_key(case_id, "RETRY_PAYMENT", stamp)
    assert first == second
    assert first.startswith("exec:")
    plan = _plan(
        PlannerStrategy.RETRY_PAYMENT,
        scheduled_at=stamp,
        probability=0.9,
        case_id=case_id,
    )
    store = ExecutionLogStore()
    a = execute(_context(plan), store)
    b = execute(_context(plan), store)
    assert a.idempotency_key == first
    assert b.idempotency_key == first
    assert a.execution_id == b.execution_id


def test_expired_payment_link() -> None:
    """A link whose 48h TTL has elapsed returns EXPIRED."""
    scheduled = AS_OF
    plan = _plan(PlannerStrategy.SEND_PAYMENT_LINK, scheduled_at=scheduled)
    result = execute(_context(plan, as_of=scheduled + timedelta(hours=49)))
    assert result.status == ExecutionStatus.EXPIRED
    assert result.success is False
    assert result.payment_link_id is not None


def test_execute_plan_without_db() -> None:
    """Service path with no session still returns a structured result."""
    plan = _plan(PlannerStrategy.STOP_RECOVERY)
    result = execute_plan(None, plan, as_of=AS_OF)
    assert result.execution_type == "STOP_EXECUTION"
    assert result.success is True
    assert result.outcome == "STOPPED"
    assert result.audit is not None
    assert result.audit.actor == "EXECUTOR_ENGINE"
    assert result.executor_version == EXECUTOR_VERSION


def test_execution_trace_lifecycle() -> None:
    """Retry and payment-link results record the ordered lifecycle steps."""
    retry = execute(_context(_plan(PlannerStrategy.RETRY_PAYMENT, probability=0.9)))
    names = [step.step for step in retry.execution_trace]
    assert names == [
        TRACE_IDEMPOTENCY,
        TRACE_START,
        TRACE_RETRY,
        TRACE_WEBHOOK,
        TRACE_AUDIT,
    ]
    assert all(step.timestamp == AS_OF for step in retry.execution_trace)
    assert retry.execution_trace[0].status == "SUCCEEDED"
    assert retry.execution_trace[1].status == "SUCCEEDED"
    assert retry.execution_trace[2].status == "SUCCEEDED"
    assert retry.execution_trace[3].status == "SUCCEEDED"
    assert retry.execution_trace[4].status == "SUCCEEDED"
    assert retry.execution_trace[2].detail.startswith("outcome=")

    link = execute(_context(_plan(PlannerStrategy.SEND_PAYMENT_LINK, probability=0.4)))
    link_names = [step.step for step in link.execution_trace]
    assert link_names == [
        TRACE_IDEMPOTENCY,
        TRACE_START,
        TRACE_PAYMENT_LINK,
        TRACE_WEBHOOK,
        TRACE_AUDIT,
    ]
    assert link.execution_trace[2].status == "SUCCEEDED"
    assert "plink_" in link.execution_trace[2].detail
    assert link.execution_trace[3].status == "SKIPPED"
