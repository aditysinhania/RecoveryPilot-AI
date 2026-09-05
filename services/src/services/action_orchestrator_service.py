"""Public orchestrator service: load case, plan, policy, then execute Sandbox actions.

Does not modify diagnosis, policy, or planner engines. Writes recovery_actions
and audit_logs only.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from database.models import Payment, RecoveryCase
from services.action_orchestrator.models import (
    ActionCustomerSnapshot,
    ActionDashboardSummary,
    ActionExecutionResult,
    ActionPaymentSnapshot,
    ActionStatusResult,
    OrchestratorContext,
)
from services.action_orchestrator.orchestrator import ActionNotFoundError, ActionOrchestrator
from services.action_orchestrator.persistence import (
    ActionStore,
    SqlAlchemyActionStore,
    chips_for_rows,
    merchant_action_rows,
)
from services.communications.router import CommunicationRouter
from services.planner.models import RecoveryPlan
from services.planner_service import plan_case
from services.policy.models import PolicyDecisionResult
from services.policy_service import evaluate_case
from services.razorpay_actions.service import RazorpayActionService
from services.recovery_service import RecoveryCaseNotFoundError
from services.scheduler.service import ActionScheduler
from services.scheduler.sqlalchemy_store import SqlAlchemySchedulerStore
from shared.enums import ConsentStatus

logger = logging.getLogger(__name__)


def _load_case(db: Session, recovery_case_id: UUID) -> RecoveryCase:
    """Load the case graph needed to call Sandbox. Raises if missing."""
    case = db.scalar(
        select(RecoveryCase)
        .options(
            selectinload(RecoveryCase.payment).selectinload(Payment.customer),
            selectinload(RecoveryCase.payment).selectinload(Payment.subscription),
            selectinload(RecoveryCase.customer),
            selectinload(RecoveryCase.merchant),
            selectinload(RecoveryCase.actions),
        )
        .where(RecoveryCase.id == recovery_case_id)
    )
    if case is None:
        raise RecoveryCaseNotFoundError(recovery_case_id)
    return case


def _context_from_case(
    case: RecoveryCase,
    plan: RecoveryPlan,
    policy: PolicyDecisionResult,
    *,
    request_id: str,
    correlation_id: str,
    as_of: datetime,
) -> OrchestratorContext:
    """Build orchestrator snapshots from ORM rows. No secrets beyond contact for Sandbox."""
    customer = case.customer if case.customer is not None else case.payment.customer
    merchant_name = case.merchant.merchant_name if case.merchant is not None else "FitLife Gym"
    return OrchestratorContext(
        as_of=as_of,
        plan=plan,
        policy=policy,
        customer=ActionCustomerSnapshot(
            id=customer.id,
            full_name=customer.full_name,
            email=customer.email,
            phone=customer.phone,
            consent_granted=customer.consent_status == ConsentStatus.GRANTED,
            merchant_id=case.merchant_id,
        ),
        payment=ActionPaymentSnapshot(
            id=case.payment.id,
            amount=case.payment.amount,
            currency=case.payment.currency,
            razorpay_order_id=case.payment.razorpay_order_id,
            razorpay_payment_id=case.payment.razorpay_payment_id,
        ),
        request_id=request_id,
        correlation_id=correlation_id,
        merchant_name=merchant_name,
    )


def _scheduler_for(db: Session, scheduler: ActionScheduler | None, store: ActionStore | None) -> ActionScheduler:
    """Use the injected scheduler, or persist jobs when the request owns the session."""
    if scheduler is not None:
        return scheduler
    if store is not None:
        return ActionScheduler()
    return ActionScheduler(store=SqlAlchemySchedulerStore(db))


def build_orchestrator(
    store: ActionStore,
    razorpay: RazorpayActionService,
    comms: CommunicationRouter | None = None,
    scheduler: ActionScheduler | None = None,
) -> ActionOrchestrator:
    """Wire default sandbox comms and the injected or process scheduler store."""
    return ActionOrchestrator(
        store=store,
        razorpay=razorpay,
        comms=comms or CommunicationRouter(),
        scheduler=scheduler or ActionScheduler(),
    )


def execute_case(
    db: Session,
    recovery_case_id: UUID,
    razorpay: RazorpayActionService,
    *,
    request_id: str,
    correlation_id: str,
    as_of: datetime | None = None,
    force_schedule: bool = False,
    store: ActionStore | None = None,
    comms: CommunicationRouter | None = None,
    scheduler: ActionScheduler | None = None,
) -> ActionExecutionResult:
    """Plan, gate, and execute (or schedule) one case against Razorpay Sandbox.

    Args:
        db: Request-scoped session.
        recovery_case_id: Case to act on.
        razorpay: Injected Sandbox action service.
        request_id: HTTP request id stamped on audit.
        correlation_id: Workflow correlation id.
        as_of: Orchestrator clock.
        force_schedule: Persist SCHEDULED without calling Razorpay.
        store: Optional store (tests).
        comms: Optional communication router.
        scheduler: Optional scheduler.

    Returns:
        Execution result including display status and payment link.

    Raises:
        RecoveryCaseNotFoundError: Unknown case.
    """
    clock = as_of or datetime.now(UTC)
    logger.info(
        "orchestrator.case.start",
        extra={"recovery_case_id": str(recovery_case_id), "force_schedule": force_schedule},
    )
    case = _load_case(db, recovery_case_id)
    policy = evaluate_case(db, recovery_case_id, as_of=clock)
    plan = plan_case(db, recovery_case_id, policy=policy, as_of=clock)
    action_store = store or SqlAlchemyActionStore(db)
    orchestrator = build_orchestrator(
        action_store,
        razorpay,
        comms=comms,
        scheduler=_scheduler_for(db, scheduler, store),
    )
    context = _context_from_case(
        case, plan, policy, request_id=request_id, correlation_id=correlation_id, as_of=clock
    )
    result = orchestrator.run(context, force_schedule=force_schedule)
    logger.info(
        "orchestrator.case.ok",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "execution_id": str(result.execution_id),
            "display_status": result.display_status,
        },
    )
    return result


def schedule_case(
    db: Session,
    recovery_case_id: UUID,
    razorpay: RazorpayActionService,
    *,
    request_id: str,
    correlation_id: str,
    as_of: datetime | None = None,
    store: ActionStore | None = None,
    comms: CommunicationRouter | None = None,
    scheduler: ActionScheduler | None = None,
) -> ActionExecutionResult:
    """Schedule WAIT_FOR_PAYDAY / HONOUR_PROMISE_TO_PAY (or any plan) without executing now."""
    return execute_case(
        db,
        recovery_case_id,
        razorpay,
        request_id=request_id,
        correlation_id=correlation_id,
        as_of=as_of,
        force_schedule=True,
        store=store,
        comms=comms,
        scheduler=scheduler,
    )


def get_case_status(
    db: Session,
    recovery_case_id: UUID,
    *,
    store: ActionStore | None = None,
    request_id: str = "-",
    correlation_id: str = "-",
) -> ActionStatusResult:
    """Latest execution plus history for a case.

    Args:
        db: Session used when store is omitted.
        recovery_case_id: Case id.
        store: Optional store.
        request_id: Fallback request id for result mapping.
        correlation_id: Fallback correlation id.

    Returns:
        Status payload. ``latest`` is None when no orchestrator action exists.

    Raises:
        RecoveryCaseNotFoundError: Unknown case.
    """
    case = db.get(RecoveryCase, recovery_case_id)
    if case is None:
        raise RecoveryCaseNotFoundError(recovery_case_id)
    action_store = store or SqlAlchemyActionStore(db)
    history_rows = action_store.list_for_case(recovery_case_id)
    from services.action_orchestrator.orchestrator import _result_from_record

    history = [
        _result_from_record(row, request_id=request_id, correlation_id=correlation_id)
        for row in history_rows
    ]
    queue = _scheduler_for(db, None, store).queue_metrics(datetime.now(UTC))
    return ActionStatusResult(
        recovery_case_id=recovery_case_id,
        latest=history[0] if history else None,
        history=history,
        active_scheduler_queue=queue.scheduled + queue.running + queue.delayed,
        scheduler_queue=queue,
    )


def replay_execution(
    db: Session,
    execution_id: UUID,
    razorpay: RazorpayActionService,
    *,
    request_id: str,
    correlation_id: str,
    as_of: datetime | None = None,
    store: ActionStore | None = None,
    comms: CommunicationRouter | None = None,
    scheduler: ActionScheduler | None = None,
) -> ActionExecutionResult:
    """Idempotent replay of one execution (webhook replay / operator retry)."""
    clock = as_of or datetime.now(UTC)
    action_store = store or SqlAlchemyActionStore(db)
    record = action_store.get(execution_id)
    if record is None:
        raise ActionNotFoundError(execution_id)
    case = _load_case(db, record.recovery_case_id)
    policy = evaluate_case(db, record.recovery_case_id, as_of=clock)
    plan = plan_case(db, record.recovery_case_id, policy=policy, as_of=clock)
    orchestrator = build_orchestrator(
        action_store,
        razorpay,
        comms=comms,
        scheduler=_scheduler_for(db, scheduler, store),
    )
    context = _context_from_case(
        case, plan, policy, request_id=request_id, correlation_id=correlation_id, as_of=clock
    )
    logger.info("orchestrator.replay.service", extra={"execution_id": str(execution_id)})
    return orchestrator.replay(execution_id, context)


def get_dashboard_summary(
    db: Session,
    merchant_id: UUID | None = None,
    *,
    as_of: datetime | None = None,
    store: ActionStore | None = None,
) -> ActionDashboardSummary:
    """Merchant orchestrator KPIs plus latest action chips keyed by case id."""
    clock = as_of or datetime.now(UTC)
    action_store = store or SqlAlchemyActionStore(db)
    counts = action_store.dashboard_counts(merchant_id=merchant_id, as_of=clock)
    queue = _scheduler_for(db, None, store).queue_metrics(clock)
    active = queue.scheduled + queue.running + queue.delayed
    counts["active_scheduler_queue"] = max(counts.get("active_scheduler_queue", 0), active)
    rows = merchant_action_rows(action_store, merchant_id) if isinstance(action_store, SqlAlchemyActionStore) else []
    if not rows and hasattr(action_store, "actions"):
        rows = list(action_store.actions.values())
    return ActionDashboardSummary(
        scheduled_actions_today=counts.get("scheduled_actions_today", 0),
        payment_links_sent=counts.get("payment_links_sent", 0),
        successful_retries=counts.get("successful_retries", 0),
        failed_deliveries=counts.get("failed_deliveries", 0),
        active_scheduler_queue=counts.get("active_scheduler_queue", 0),
        scheduler_queue=queue,
        chips=chips_for_rows(rows),
    )


def tick_due(
    db: Session,
    razorpay: RazorpayActionService,
    *,
    as_of: datetime | None = None,
    store: ActionStore | None = None,
    comms: CommunicationRouter | None = None,
    scheduler: ActionScheduler | None = None,
    request_id: str = "scheduler",
    correlation_id: str = "scheduler",
) -> list[ActionExecutionResult]:
    """Execute due SCHEDULED rows. Called from the FastAPI lifespan loop."""
    clock = as_of or datetime.now(UTC)
    action_store = store or SqlAlchemyActionStore(db)
    sched = _scheduler_for(db, scheduler, store)
    due_records = action_store.list_due(clock)
    seen = {row.id for row in due_records}
    for job in sched.claim_due(clock):
        if job.execution_id in seen:
            continue
        loaded = action_store.get(job.execution_id)
        if loaded is not None:
            due_records.append(loaded)
    results: list[ActionExecutionResult] = []
    orchestrator = build_orchestrator(action_store, razorpay, comms=comms, scheduler=sched)
    for record in due_records:
        try:
            case = _load_case(db, record.recovery_case_id)
            policy = evaluate_case(db, record.recovery_case_id, as_of=clock)
            plan = plan_case(db, record.recovery_case_id, policy=policy, as_of=clock)
            context = _context_from_case(
                case, plan, policy, request_id=request_id, correlation_id=correlation_id, as_of=clock
            )
            results.append(orchestrator.run_due(record, context))
        except Exception as exc:  # noqa: BLE001 — tick must not kill the worker
            sched.release(record.id)
            logger.info(
                "orchestrator.tick.failed",
                extra={
                    "execution_id": str(record.id),
                    "recovery_case_id": str(record.recovery_case_id),
                    "error_type": type(exc).__name__,
                },
            )
    logger.info("orchestrator.tick.ok", extra={"count": len(results)})
    return results
