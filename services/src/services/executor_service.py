"""Read-only executor service: load snapshots, simulate execution, never write.

Does not call Razorpay, Gemini, SMS, WhatsApp, Email, or Voice.
Does not modify planner, policy, or diagnosis outputs.
Does not INSERT into audit_logs or webhook_events.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Payment, RecoveryCase
from services.diagnosis.constants import SALARY_DEPENDENT_SEGMENTS
from services.executor.execution_log import ExecutionLogStore
from services.executor.executor_engine import (
    execute,
    execute_many,
    execute_batch as execute_plans_batch,
    summarize_executions,
    unavailable_case_result,
)
from services.executor.models import (
    BatchExecutorResult,
    ExecutionResult,
    ExecutorContext,
)
from services.planner.models import RecoveryPlan

logger = logging.getLogger(__name__)


def _load_case(db: Session, recovery_case_id: UUID) -> RecoveryCase | None:
    """Load a recovery case graph, or ``None`` when missing."""
    return db.scalar(
        select(RecoveryCase)
        .options(
            selectinload(RecoveryCase.payment).selectinload(Payment.customer),
            selectinload(RecoveryCase.payment).selectinload(Payment.subscription),
            selectinload(RecoveryCase.customer),
        )
        .where(RecoveryCase.id == recovery_case_id)
    )


def _context_from_case(
    case: RecoveryCase,
    plan: RecoveryPlan,
    *,
    as_of: datetime,
) -> ExecutorContext:
    """Build executor snapshots from ORM rows. Plan is not mutated."""
    customer = case.customer if case.customer is not None else case.payment.customer
    salary = customer.customer_segment.value in SALARY_DEPENDENT_SEGMENTS
    diagnosis = None
    if plan.features.get("diagnosis"):
        diagnosis = str(plan.features["diagnosis"])
    policy = None
    if plan.features.get("policy_decision"):
        policy = str(plan.features["policy_decision"])
    return ExecutorContext(
        as_of=as_of,
        plan=plan,
        recovery_case_id=case.id,
        payment_id=case.payment_id,
        payment_amount=case.payment.amount,
        payment_method=case.payment.payment_method,
        customer_segment=customer.customer_segment,
        salary_dependent=salary,
        diagnosis=diagnosis,
        policy_decision=policy,
    )


def _context_from_plan(plan: RecoveryPlan, *, as_of: datetime) -> ExecutorContext:
    """Execute using only ids and features already on the plan."""
    return ExecutorContext(
        as_of=as_of,
        plan=plan,
        recovery_case_id=plan.recovery_case_id,
        payment_id=plan.payment_id,
        payment_amount=int(
            plan.features.get("payment_amount") or plan.estimated_recovery_value or 0
        ),
        diagnosis=str(plan.features["diagnosis"]) if plan.features.get("diagnosis") else None,
        policy_decision=(
            str(plan.features["policy_decision"])
            if plan.features.get("policy_decision")
            else None
        ),
    )


def execute_plan(
    db: Session | None,
    plan: RecoveryPlan,
    *,
    as_of: datetime | None = None,
    store: ExecutionLogStore | None = None,
) -> ExecutionResult:
    """Simulate one RecoveryPlan. Read-only. Never raises raw exceptions.

    Args:
        db: Optional SQLAlchemy session used only to load snapshots.
        plan: Planner output. Not modified.
        as_of: Simulation clock. Defaults to UTC now.
        store: Shared idempotency / webhook ledger.

    Returns:
        Structured ``ExecutionResult``. Missing cases return ``CASE_NOT_FOUND``.
    """
    clock = as_of or datetime.now(UTC)
    log = store or ExecutionLogStore()
    case_id = plan.recovery_case_id
    logger.info(
        "executor.plan.start",
        extra={
            "recovery_case_id": str(case_id) if case_id else None,
            "strategy": str(plan.strategy),
        },
    )
    try:
        if db is None or case_id is None:
            result = execute(_context_from_plan(plan, as_of=clock), log)
        else:
            case = _load_case(db, case_id)
            if case is None:
                logger.info("executor.plan.missing", extra={"recovery_case_id": str(case_id)})
                result = unavailable_case_result(plan, as_of=clock, store=log)
            else:
                result = execute(_context_from_case(case, plan, as_of=clock), log)
    except Exception as exc:  # noqa: BLE001 — service must not raise
        logger.info(
            "executor.plan.caught",
            extra={"error": type(exc).__name__, "message": str(exc)[:200]},
        )
        result = execute(_context_from_plan(plan, as_of=clock), log)
    logger.info(
        "executor.plan.ok",
        extra={
            "status": result.status.value,
            "outcome": result.outcome,
            "success": result.success,
        },
    )
    return result


def execute_case(
    db: Session,
    recovery_case_id: UUID,
    plan: RecoveryPlan,
    *,
    as_of: datetime | None = None,
    store: ExecutionLogStore | None = None,
) -> ExecutionResult:
    """Load one case and simulate ``plan``. Does not write.

    Args:
        db: Request-scoped SQLAlchemy session (read only).
        recovery_case_id: Case whose payment/customer/subscription are loaded.
        plan: Planner output. Not modified.
        as_of: Simulation clock.
        store: Shared ledger.

    Returns:
        Structured ``ExecutionResult``. Missing cases return ``CASE_NOT_FOUND``.
    """
    log = store or ExecutionLogStore()
    clock = as_of or datetime.now(UTC)
    logger.info(
        "executor.case.start",
        extra={"recovery_case_id": str(recovery_case_id), "strategy": str(plan.strategy)},
    )
    try:
        case = _load_case(db, recovery_case_id)
    except Exception as exc:  # noqa: BLE001
        logger.info(
            "executor.case.caught",
            extra={"error": type(exc).__name__, "message": str(exc)[:200]},
        )
        return execute(_context_from_plan(plan, as_of=clock), log)
    if case is None:
        logger.info("executor.case.missing", extra={"recovery_case_id": str(recovery_case_id)})
        return unavailable_case_result(plan, as_of=clock, store=log)
    return execute(_context_from_case(case, plan, as_of=clock), log)


def execute_batch(
    db: Session | None,
    plans: list[RecoveryPlan],
    *,
    as_of: datetime | None = None,
    store: ExecutionLogStore | None = None,
) -> BatchExecutorResult:
    """Simulate many RecoveryPlans against one idempotency store.

    Args:
        db: Optional session for snapshot loads. ``None`` uses plan features.
        plans: Planner outputs. Not modified.
        as_of: Shared simulation clock.
        store: Optional shared ledger.

    Returns:
        Per-plan results plus executed / success / duplicate / link totals.
    """
    clock = as_of or datetime.now(UTC)
    log = store or ExecutionLogStore()
    logger.info("executor.batch.start", extra={"count": len(plans)})
    if db is None:
        batch = execute_plans_batch(plans, as_of=clock, store=log)
        logger.info(
            "executor.batch.ok",
            extra={"executed": batch.summary.executed, "duplicates": batch.summary.duplicates},
        )
        return batch

    contexts: list[ExecutorContext] = []
    extras: list[ExecutionResult] = []
    for plan in plans:
        case_id = plan.recovery_case_id
        if case_id is None:
            contexts.append(_context_from_plan(plan, as_of=clock))
            continue
        try:
            case = _load_case(db, case_id)
        except Exception as exc:  # noqa: BLE001
            logger.info(
                "executor.batch.caught",
                extra={"error": type(exc).__name__, "recovery_case_id": str(case_id)},
            )
            contexts.append(_context_from_plan(plan, as_of=clock))
            continue
        if case is None:
            extras.append(unavailable_case_result(plan, as_of=clock, store=log))
            continue
        contexts.append(_context_from_case(case, plan, as_of=clock))
    batch = execute_many(contexts, store=log)
    results = extras + batch.results
    summary = summarize_executions(results)
    logger.info(
        "executor.batch.ok",
        extra={"executed": summary.executed, "duplicates": summary.duplicates},
    )
    return BatchExecutorResult(results=results, summary=summary)


__all__ = [
    "execute_batch",
    "execute_case",
    "execute_plan",
    "summarize_executions",
]
