"""Deterministic executor orchestrator. Simulates Razorpay; never calls it."""

from __future__ import annotations

import logging
from collections import Counter
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from services.executor.constants import (
    EXECUTOR_VERSION,
    STRATEGY_TO_EXECUTION,
    TRACE_AUDIT,
    TRACE_CARD_UPDATE,
    TRACE_IDEMPOTENCY,
    TRACE_PAYMENT_LINK,
    TRACE_RETRY,
    TRACE_START,
    TRACE_TERMINAL,
    TRACE_WAIT,
    TRACE_WEBHOOK,
)
from services.executor.execution_log import ExecutionLogStore, build_audit
from services.executor.idempotency import execution_id_for, make_idempotency_key
from services.executor.models import (
    BatchExecutorResult,
    BatchExecutorSummary,
    ExecutionResult,
    ExecutionStatus,
    ExecutionTraceStep,
    ExecutorContext,
    RetryOutcome,
    SimulatedWebhookEvent,
)
from services.executor.payment_link_executor import (
    generate_card_update_session,
    generate_payment_link,
    link_is_expired,
)
from services.executor.retry_executor import simulate_retry
from services.executor.webhook_processor import (
    build_webhooks,
    process_webhooks,
    webhooks_for_retry,
)
from services.planner.models import RecoveryPlan
from shared.enums import PaymentMethod

logger = logging.getLogger(__name__)


def _append_trace(
    trace: list[ExecutionTraceStep],
    step: str,
    status: str,
    timestamp: datetime,
    detail: str = "",
) -> None:
    """Record one lifecycle step. Mutates ``trace`` in place."""
    trace.append(
        ExecutionTraceStep(
            step=step,
            timestamp=timestamp,
            status=status,
            detail=detail,
        )
    )


def _action_step_name(execution_type: str) -> str:
    """Map an execution type onto its creation-trace step name."""
    if execution_type == "EXECUTE_RETRY":
        return TRACE_RETRY
    if execution_type in {"GENERATE_PAYMENT_LINK", "SWITCH_TO_UPI"}:
        return TRACE_PAYMENT_LINK
    if execution_type == "REQUEST_CARD_UPDATE":
        return TRACE_CARD_UPDATE
    if execution_type == "WAIT_UNTIL_TIME":
        return TRACE_WAIT
    return TRACE_TERMINAL


def _correlation_id(context: ExecutorContext) -> str:
    """Stable correlation id from the recovery case."""
    if context.recovery_case_id is not None:
        return str(context.recovery_case_id)
    if context.plan.recovery_case_id is not None:
        return str(context.plan.recovery_case_id)
    return "no-case"


def _diagnosis(context: ExecutorContext) -> str | None:
    """Diagnosis label from context or plan features."""
    if context.diagnosis:
        return context.diagnosis
    raw = context.plan.features.get("diagnosis")
    return str(raw) if raw else None


def _policy(context: ExecutorContext) -> str | None:
    """Policy decision from context or plan features."""
    if context.policy_decision:
        return context.policy_decision
    raw = context.plan.features.get("policy_decision")
    return str(raw) if raw else None


def _duplicate_result(
    prior: ExecutionResult,
    as_of: datetime,
    store: ExecutionLogStore,
    trace: list[ExecutionTraceStep],
) -> ExecutionResult:
    """Return a DUPLICATE_SKIPPED clone that does not re-run side effects."""
    action_step = _action_step_name(prior.execution_type)
    _append_trace(trace, TRACE_START, "SKIPPED", as_of, "Duplicate; execution not started.")
    _append_trace(trace, action_step, "SKIPPED", as_of, "Duplicate; no retry or link created.")
    _append_trace(trace, TRACE_WEBHOOK, "SKIPPED", as_of, "Duplicate; webhooks not emitted.")
    skip_audit = build_audit(
        action="DUPLICATE_SKIPPED",
        outcome="DUPLICATE_SKIPPED",
        request_id=str(prior.execution_id),
        correlation_id=str(prior.audit.correlation_id) if prior.audit else "no-case",
        idempotency_key=prior.idempotency_key,
        timestamp=as_of,
    )
    store.record_audit(skip_audit)
    _append_trace(
        trace,
        TRACE_AUDIT,
        "SUCCEEDED",
        as_of,
        f"audit_event_id={skip_audit.audit_event_id}",
    )
    return prior.model_copy(
        update={
            "status": ExecutionStatus.DUPLICATE_SKIPPED,
            "success": False,
            "outcome": "DUPLICATE_SKIPPED",
            "executed_at": as_of,
            "idempotent": True,
            "execution_reason": "Idempotency key already used; execution skipped.",
            "human_summary": (
                f"Duplicate skipped for {prior.strategy} "
                f"(key {prior.idempotency_key})."
            ),
            "generated_at": datetime.now(UTC),
            "recovered_value": 0,
            "webhooks": [],
            "audit": skip_audit,
            "audit_event_id": skip_audit.audit_event_id,
            "execution_trace": list(trace),
        }
    )


def _finish(
    context: ExecutorContext,
    *,
    execution_id: UUID,
    idempotency_key: str,
    execution_type: str,
    status: ExecutionStatus,
    success: bool,
    outcome: str,
    executed_at: datetime | None,
    reason: str,
    summary: str,
    metadata: dict[str, Any],
    payment_link_id: str | None = None,
    webhook_event_id: str | None = None,
    webhooks: list[SimulatedWebhookEvent] | None = None,
    recovered_value: int = 0,
    store: ExecutionLogStore,
    trace: list[ExecutionTraceStep] | None = None,
) -> ExecutionResult:
    """Assemble result, audit event, and persist to the in-memory log."""
    now = datetime.now(UTC)
    clock = executed_at or context.as_of
    steps = list(trace or [])
    audit = build_audit(
        action=execution_type,
        outcome=outcome,
        request_id=str(execution_id),
        correlation_id=_correlation_id(context),
        idempotency_key=idempotency_key,
        timestamp=clock,
        audit_event_id=execution_id,
    )
    _append_trace(
        steps,
        TRACE_AUDIT,
        "SUCCEEDED",
        clock,
        f"audit_event_id={audit.audit_event_id}",
    )
    result = ExecutionResult(
        execution_id=execution_id,
        strategy=str(context.plan.strategy),
        status=status,
        scheduled_at=context.plan.scheduled_at,
        executed_at=executed_at,
        execution_type=execution_type,
        success=success,
        outcome=outcome,
        payment_link_id=payment_link_id,
        webhook_event_id=webhook_event_id,
        idempotency_key=idempotency_key,
        audit_event_id=audit.audit_event_id,
        metadata=metadata,
        executor_version=EXECUTOR_VERSION,
        generated_at=now,
        execution_reason=reason,
        planner_strategy=str(context.plan.strategy),
        policy_decision=_policy(context),
        diagnosis=_diagnosis(context),
        idempotent=False,
        human_summary=summary,
        recovered_value=recovered_value,
        webhooks=webhooks or [],
        audit=audit,
        execution_trace=steps,
    )
    store.put(result)
    return result


def _run_retry(
    context: ExecutorContext,
    execution_id: UUID,
    key: str,
    execution_type: str,
    store: ExecutionLogStore,
    trace: list[ExecutionTraceStep],
) -> ExecutionResult:
    """Simulate a charge retry and emit payment webhooks."""
    clock = context.as_of
    outcome = simulate_retry(context.plan, context)
    success = outcome == RetryOutcome.SUCCESS
    retry_status = "SUCCEEDED" if success else "FAILED"
    if outcome == RetryOutcome.BANK_TIMEOUT:
        retry_status = "TIMEOUT"
    _append_trace(trace, TRACE_RETRY, retry_status, clock, f"outcome={outcome.value}")
    events = process_webhooks(
        webhooks_for_retry(context, outcome, clock),
        store,
    )
    hook_status = "SUCCEEDED"
    if events and all(item.replay for item in events):
        hook_status = "WEBHOOK_REPLAY"
    elif not events:
        hook_status = "SKIPPED"
    _append_trace(
        trace,
        TRACE_WEBHOOK,
        hook_status,
        clock,
        f"events={len(events)} replay={hook_status == 'WEBHOOK_REPLAY'}",
    )
    hook_id = events[-1].event_id if events else None
    recovered = context.payment_amount if success else 0
    status = ExecutionStatus.SUCCEEDED if success else ExecutionStatus.FAILED
    result_outcome = outcome.value
    if outcome == RetryOutcome.BANK_TIMEOUT:
        status = ExecutionStatus.TIMEOUT
    if events and all(item.replay for item in events):
        status = ExecutionStatus.WEBHOOK_REPLAY
        success = False
        recovered = 0
        result_outcome = "WEBHOOK_REPLAY"
    strategy_label = str(context.plan.strategy)
    return _finish(
        context,
        execution_id=execution_id,
        idempotency_key=key,
        execution_type=execution_type,
        status=status,
        success=success,
        outcome=result_outcome,
        executed_at=clock,
        reason=f"Simulated Razorpay retry outcome {outcome.value}.",
        summary=(
            f"Retry {outcome.value} for {context.payment_amount} paise "
            f"on {strategy_label}."
        ),
        metadata={
            "retry_outcome": outcome.value,
            "silent": strategy_label == "RETRY_SILENTLY",
        },
        webhook_event_id=hook_id,
        webhooks=events,
        recovered_value=recovered,
        store=store,
        trace=trace,
    )


def _run_payment_link(
    context: ExecutorContext,
    execution_id: UUID,
    key: str,
    execution_type: str,
    store: ExecutionLogStore,
    trace: list[ExecutionTraceStep],
    *,
    method: PaymentMethod | None = None,
) -> ExecutionResult:
    """Generate a hosted link; mark EXPIRED if the clock is past TTL."""
    clock = context.as_of
    payload = generate_payment_link(context, method=method, as_of=context.plan.scheduled_at)
    expires_at = payload["expires_at"]
    link_id = str(payload["payment_link_id"])
    expired = link_is_expired(expires_at, clock)  # type: ignore[arg-type]
    if expired:
        _append_trace(trace, TRACE_PAYMENT_LINK, "EXPIRED", clock, f"payment_link_id={link_id}")
        _append_trace(trace, TRACE_WEBHOOK, "SKIPPED", clock, "Expired link; no webhooks.")
        return _finish(
            context,
            execution_id=execution_id,
            idempotency_key=key,
            execution_type=execution_type,
            status=ExecutionStatus.EXPIRED,
            success=False,
            outcome="EXPIRED",
            executed_at=clock,
            reason="Payment link TTL (48h) has elapsed.",
            summary=f"Payment link {link_id} expired.",
            metadata=payload,
            payment_link_id=link_id,
            store=store,
            trace=trace,
        )
    _append_trace(trace, TRACE_PAYMENT_LINK, "SUCCEEDED", clock, f"payment_link_id={link_id}")
    events = process_webhooks(
        build_webhooks(
            context,
            event_types=("payment_link.paid",) if context.plan.expected_recovery_probability >= 0.85 else (),
            created_at=clock,
            extra={"payment_link_id": link_id},
        ),
        store,
    )
    hook_status = "SUCCEEDED"
    if events and all(item.replay for item in events):
        hook_status = "WEBHOOK_REPLAY"
    elif not events:
        hook_status = "SKIPPED"
    _append_trace(
        trace,
        TRACE_WEBHOOK,
        hook_status,
        clock,
        f"events={len(events)}",
    )
    hook_id = events[-1].event_id if events else None
    recovered = (
        context.payment_amount if events and not events[0].replay else 0
    )
    status = ExecutionStatus.GENERATED
    outcome_label = "GENERATED"
    success = True
    if events and all(item.replay for item in events):
        status = ExecutionStatus.WEBHOOK_REPLAY
        outcome_label = "WEBHOOK_REPLAY"
        success = False
        recovered = 0
    return _finish(
        context,
        execution_id=execution_id,
        idempotency_key=key,
        execution_type=execution_type,
        status=status,
        success=success,
        outcome=outcome_label,
        executed_at=clock,
        reason="Deterministic payment link generated (no Razorpay HTTP).",
        summary=f"Generated {link_id} expiring {expires_at}.",
        metadata=payload,
        payment_link_id=link_id,
        webhook_event_id=hook_id,
        webhooks=events,
        recovered_value=recovered,
        store=store,
        trace=trace,
    )


def _run_card_update(
    context: ExecutorContext,
    execution_id: UUID,
    key: str,
    execution_type: str,
    store: ExecutionLogStore,
    trace: list[ExecutionTraceStep],
) -> ExecutionResult:
    """Generate a card-update session."""
    clock = context.as_of
    payload = generate_card_update_session(context, as_of=context.plan.scheduled_at)
    expires_at = payload["expires_at"]
    if link_is_expired(expires_at, clock):  # type: ignore[arg-type]
        payload = {**payload, "status": "EXPIRED"}
        _append_trace(
            trace,
            TRACE_CARD_UPDATE,
            "EXPIRED",
            clock,
            f"update_session_id={payload['update_session_id']}",
        )
        _append_trace(trace, TRACE_WEBHOOK, "SKIPPED", clock, "Expired session; no webhooks.")
        return _finish(
            context,
            execution_id=execution_id,
            idempotency_key=key,
            execution_type=execution_type,
            status=ExecutionStatus.EXPIRED,
            success=False,
            outcome="EXPIRED",
            executed_at=clock,
            reason="Card-update session TTL (24h) has elapsed.",
            summary=f"Card update session {payload['update_session_id']} expired.",
            metadata=payload,
            store=store,
            trace=trace,
        )
    _append_trace(
        trace,
        TRACE_CARD_UPDATE,
        "SUCCEEDED",
        clock,
        f"update_session_id={payload['update_session_id']}",
    )
    events = process_webhooks(
        build_webhooks(
            context,
            event_types=("subscription.pending",),
            created_at=clock,
            extra={"update_session_id": payload["update_session_id"]},
        ),
        store,
    )
    _append_trace(trace, TRACE_WEBHOOK, "SUCCEEDED", clock, f"events={len(events)}")
    return _finish(
        context,
        execution_id=execution_id,
        idempotency_key=key,
        execution_type=execution_type,
        status=ExecutionStatus.GENERATED,
        success=True,
        outcome=str(payload["status"]),
        executed_at=clock,
        reason="Card-update session created (no Razorpay checkout).",
        summary=f"Card update session {payload['update_session_id']}.",
        metadata=payload,
        webhook_event_id=events[-1].event_id if events else None,
        webhooks=events,
        store=store,
        trace=trace,
    )


def _run_wait(
    context: ExecutorContext,
    execution_id: UUID,
    key: str,
    execution_type: str,
    store: ExecutionLogStore,
    trace: list[ExecutionTraceStep],
) -> ExecutionResult:
    """Record a wait. SCHEDULED until scheduled_at, then SUCCEEDED."""
    clock = context.as_of
    due = clock >= context.plan.scheduled_at
    status = ExecutionStatus.SUCCEEDED if due else ExecutionStatus.SCHEDULED
    _append_trace(
        trace,
        TRACE_WAIT,
        "SUCCEEDED" if due else "SCHEDULED",
        clock,
        f"scheduled_at={context.plan.scheduled_at.isoformat()}",
    )
    _append_trace(trace, TRACE_WEBHOOK, "SKIPPED", clock, "Wait; no webhooks.")
    return _finish(
        context,
        execution_id=execution_id,
        idempotency_key=key,
        execution_type=execution_type,
        status=status,
        success=due,
        outcome="WAIT_ELAPSED" if due else "WAITING",
        executed_at=clock if due else None,
        reason="Wait-until-time; no charge attempted.",
        summary=(
            f"Wait until {context.plan.scheduled_at.isoformat()} "
            f"({'elapsed' if due else 'still waiting'})."
        ),
        metadata={"scheduled_at": context.plan.scheduled_at.isoformat()},
        store=store,
        trace=trace,
    )


def _run_terminal(
    context: ExecutorContext,
    execution_id: UUID,
    key: str,
    execution_type: str,
    store: ExecutionLogStore,
    trace: list[ExecutionTraceStep],
    *,
    escalate: bool,
) -> ExecutionResult:
    """Escalate or stop without charging."""
    clock = context.as_of
    outcome = "ESCALATED" if escalate else "STOPPED"
    _append_trace(trace, TRACE_TERMINAL, "SUCCEEDED", clock, outcome)
    events = process_webhooks(
        build_webhooks(
            context,
            event_types=("subscription.halted",) if not escalate else (),
            created_at=clock,
        ),
        store,
    )
    hook_status = "SUCCEEDED" if events else "SKIPPED"
    _append_trace(trace, TRACE_WEBHOOK, hook_status, clock, f"events={len(events)}")
    return _finish(
        context,
        execution_id=execution_id,
        idempotency_key=key,
        execution_type=execution_type,
        status=ExecutionStatus.SUCCEEDED,
        success=True,
        outcome=outcome,
        executed_at=clock,
        reason="Escalate to human." if escalate else "Stop recovery; no further charges.",
        summary=f"{outcome} for case {_correlation_id(context)}.",
        metadata={"terminal": True},
        webhook_event_id=events[-1].event_id if events else None,
        webhooks=events,
        store=store,
        trace=trace,
    )


def execute(
    context: ExecutorContext,
    store: ExecutionLogStore | None = None,
) -> ExecutionResult:
    """Simulate one plan. Never calls Razorpay, Gemini, or comms. Never raises.

    Args:
        context: Plan plus read-only case snapshots.
        store: Idempotency / webhook ledger. A new store is used when omitted.

    Returns:
        Structured ``ExecutionResult``. Duplicates return DUPLICATE_SKIPPED.
    """
    log = store or ExecutionLogStore()
    try:
        return _execute(context, log)
    except Exception as exc:  # noqa: BLE001 — failure handling must not raise
        logger.info(
            "executor.caught",
            extra={"error": type(exc).__name__, "message": str(exc)[:200]},
        )
        key = make_idempotency_key(
            context.recovery_case_id or context.plan.recovery_case_id,
            str(context.plan.strategy),
            context.plan.scheduled_at,
        )
        execution_id = execution_id_for(key)
        trace: list[ExecutionTraceStep] = []
        _append_trace(trace, TRACE_IDEMPOTENCY, "SUCCEEDED", context.as_of, key)
        _append_trace(
            trace,
            TRACE_START,
            "FAILED",
            context.as_of,
            f"caught {type(exc).__name__}",
        )
        _append_trace(trace, TRACE_TERMINAL, "SKIPPED", context.as_of, "Internal error.")
        _append_trace(trace, TRACE_WEBHOOK, "SKIPPED", context.as_of, "Internal error.")
        return _finish(
            context,
            execution_id=execution_id,
            idempotency_key=key,
            execution_type="STOP_EXECUTION",
            status=ExecutionStatus.FAILED,
            success=False,
            outcome="INTERNAL_ERROR",
            executed_at=context.as_of,
            reason=f"Executor caught {type(exc).__name__}.",
            summary="Execution failed internally; no charge was sent.",
            metadata={"error": type(exc).__name__},
            store=log,
            trace=trace,
        )


def _execute(context: ExecutorContext, store: ExecutionLogStore) -> ExecutionResult:
    """Inner execute after the catch-all wrapper."""
    strategy = str(context.plan.strategy)
    case_id = context.recovery_case_id or context.plan.recovery_case_id
    key = make_idempotency_key(case_id, strategy, context.plan.scheduled_at)
    execution_id = execution_id_for(key)
    clock = context.as_of
    trace: list[ExecutionTraceStep] = []
    logger.info(
        "executor.start",
        extra={"idempotency_key": key, "strategy": strategy},
    )
    prior = store.get(key)
    if prior is not None:
        logger.info("executor.duplicate", extra={"idempotency_key": key})
        _append_trace(trace, TRACE_IDEMPOTENCY, "DUPLICATE_SKIPPED", clock, key)
        return _duplicate_result(prior, clock, store, trace)

    _append_trace(trace, TRACE_IDEMPOTENCY, "SUCCEEDED", clock, f"new key {key}")
    execution_type = STRATEGY_TO_EXECUTION.get(strategy)
    if execution_type is None:
        _append_trace(trace, TRACE_START, "FAILED", clock, f"unknown strategy {strategy}")
        _append_trace(trace, TRACE_TERMINAL, "SKIPPED", clock, "No execution mapping.")
        _append_trace(trace, TRACE_WEBHOOK, "SKIPPED", clock, "Unknown strategy.")
        result = _finish(
            context,
            execution_id=execution_id,
            idempotency_key=key,
            execution_type="STOP_EXECUTION",
            status=ExecutionStatus.UNKNOWN_STRATEGY,
            success=False,
            outcome="UNKNOWN_STRATEGY",
            executed_at=clock,
            reason=f"No executor mapping for strategy {strategy}.",
            summary=f"Unknown strategy {strategy}; nothing was charged.",
            metadata={},
            store=store,
            trace=trace,
        )
        return result

    _append_trace(trace, TRACE_START, "SUCCEEDED", clock, execution_type)
    if execution_type == "EXECUTE_RETRY":
        result = _run_retry(context, execution_id, key, execution_type, store, trace)
    elif execution_type == "GENERATE_PAYMENT_LINK":
        result = _run_payment_link(context, execution_id, key, execution_type, store, trace)
    elif execution_type == "SWITCH_TO_UPI":
        result = _run_payment_link(
            context,
            execution_id,
            key,
            execution_type,
            store,
            trace,
            method=PaymentMethod.UPI,
        )
    elif execution_type == "REQUEST_CARD_UPDATE":
        result = _run_card_update(context, execution_id, key, execution_type, store, trace)
    elif execution_type == "WAIT_UNTIL_TIME":
        result = _run_wait(context, execution_id, key, execution_type, store, trace)
    elif execution_type == "ESCALATE_CASE":
        result = _run_terminal(
            context, execution_id, key, execution_type, store, trace, escalate=True
        )
    else:
        result = _run_terminal(
            context, execution_id, key, execution_type, store, trace, escalate=False
        )
    logger.info(
        "executor.ok",
        extra={
            "status": result.status.value,
            "outcome": result.outcome,
            "success": result.success,
        },
    )
    return result


def summarize_executions(results: list[ExecutionResult]) -> BatchExecutorSummary:
    """Roll up executed / success / duplicate / link / retry counts.

    Args:
        results: Per-plan executor outputs.

    Returns:
        Dashboard-oriented summary. No database.
    """
    statuses = Counter(item.status.value for item in results)
    executed = sum(
        1 for item in results if item.status != ExecutionStatus.DUPLICATE_SKIPPED
    )
    successes = sum(1 for item in results if item.success)
    failures = sum(
        1
        for item in results
        if item.status
        in {
            ExecutionStatus.FAILED,
            ExecutionStatus.TIMEOUT,
            ExecutionStatus.EXPIRED,
            ExecutionStatus.UNKNOWN_STRATEGY,
            ExecutionStatus.WEBHOOK_REPLAY,
        }
    )
    links = sum(
        1
        for item in results
        if item.payment_link_id and item.status == ExecutionStatus.GENERATED
    )
    retries_scheduled = sum(
        1
        for item in results
        if item.execution_type == "EXECUTE_RETRY"
        and item.status != ExecutionStatus.DUPLICATE_SKIPPED
    )
    recovered = sum(item.recovered_value for item in results)
    return BatchExecutorSummary(
        total_plans=len(results),
        executed=executed,
        successes=successes,
        failures=failures,
        duplicates=statuses.get(ExecutionStatus.DUPLICATE_SKIPPED, 0),
        payment_links_generated=links,
        retries_scheduled=retries_scheduled,
        estimated_recovered_value=recovered,
    )


def execute_many(
    contexts: list[ExecutorContext],
    store: ExecutionLogStore | None = None,
) -> BatchExecutorResult:
    """Execute many plans against a shared idempotency store."""
    log = store or ExecutionLogStore()
    logger.info("executor.many.start", extra={"count": len(contexts)})
    results = [execute(item, log) for item in contexts]
    summary = summarize_executions(results)
    logger.info(
        "executor.many.ok",
        extra={"executed": summary.executed, "duplicates": summary.duplicates},
    )
    return BatchExecutorResult(results=results, summary=summary)


def execute_plans(
    plans: list[RecoveryPlan],
    *,
    as_of: datetime,
    store: ExecutionLogStore | None = None,
) -> BatchExecutorResult:
    """Execute a list of RecoveryPlans using plan-embedded ids and features."""
    contexts = [
        ExecutorContext(
            as_of=as_of,
            plan=item,
            recovery_case_id=item.recovery_case_id,
            payment_id=item.payment_id,
            payment_amount=int(item.features.get("payment_amount") or item.estimated_recovery_value or 0),
            diagnosis=str(item.features["diagnosis"]) if item.features.get("diagnosis") else None,
            policy_decision=(
                str(item.features["policy_decision"])
                if item.features.get("policy_decision")
                else None
            ),
        )
        for item in plans
    ]
    return execute_many(contexts, store=store)


def execute_batch(
    plans: list[RecoveryPlan],
    *,
    as_of: datetime,
    store: ExecutionLogStore | None = None,
) -> BatchExecutorResult:
    """Execute a list of RecoveryPlans. Shared idempotency store across the batch.

    Args:
        plans: Planner outputs. Not modified.
        as_of: Simulation clock.
        store: Optional shared ledger.

    Returns:
        Per-plan results plus executed/success/duplicate/link/retry totals.
    """
    return execute_plans(plans, as_of=as_of, store=store)


def unavailable_case_result(
    plan: RecoveryPlan,
    *,
    as_of: datetime,
    store: ExecutionLogStore,
) -> ExecutionResult:
    """Structured failure when the recovery case cannot be loaded.

    Args:
        plan: Planner output that referenced a missing case.
        as_of: Simulation clock.
        store: Execution ledger.

    Returns:
        ``ExecutionResult`` with outcome ``CASE_NOT_FOUND``. Never raises.
    """
    context = ExecutorContext(
        as_of=as_of,
        plan=plan,
        recovery_case_id=plan.recovery_case_id,
        payment_id=plan.payment_id,
    )
    key = make_idempotency_key(plan.recovery_case_id, str(plan.strategy), plan.scheduled_at)
    trace: list[ExecutionTraceStep] = []
    _append_trace(trace, TRACE_IDEMPOTENCY, "SUCCEEDED", as_of, key)
    _append_trace(trace, TRACE_START, "FAILED", as_of, "CASE_NOT_FOUND")
    _append_trace(trace, TRACE_TERMINAL, "SKIPPED", as_of, "Case missing.")
    _append_trace(trace, TRACE_WEBHOOK, "SKIPPED", as_of, "Case missing.")
    return _finish(
        context,
        execution_id=execution_id_for(key),
        idempotency_key=key,
        execution_type="STOP_EXECUTION",
        status=ExecutionStatus.FAILED,
        success=False,
        outcome="CASE_NOT_FOUND",
        executed_at=as_of,
        reason="Recovery case was not found; nothing was charged.",
        summary=f"Case {plan.recovery_case_id} is missing.",
        metadata={"recovery_case_id": str(plan.recovery_case_id) if plan.recovery_case_id else None},
        store=store,
        trace=trace,
    )
