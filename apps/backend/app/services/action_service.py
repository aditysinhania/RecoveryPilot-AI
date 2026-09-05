"""FastAPI adapter over the action orchestrator. Routers stay thin."""

from __future__ import annotations

from uuid import UUID

from integrations.razorpay import RazorpaySandboxClient
from services.action_orchestrator.models import (
    ActionDashboardSummary,
    ActionExecutionResult,
    ActionStatusResult,
)
from services.action_orchestrator.orchestrator import ActionNotFoundError as DomainActionNotFound
from services.action_orchestrator_service import (
    execute_case,
    get_case_status,
    get_dashboard_summary,
    replay_execution,
    schedule_case,
)
from services.razorpay_actions.service import RazorpayActionService
from services.recovery_service import RecoveryCaseNotFoundError as DomainCaseNotFound
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.core.exceptions import ActionNotFoundError, RecoveryNotFoundError
from app.core.metrics import record_action_execution
from app.schemas.actions import (
    ActionDashboardResponse,
    ActionDelivery,
    ActionExecutionResponse,
    ActionStatusResponse,
    SchedulerQueueMetrics,
)
from app.utils.request_id import set_execution_id, set_recovery_case_id


def _razorpay(settings: Settings) -> RazorpayActionService:
    """Sandbox client from settings. Placeholder keys stay in mock mode."""
    client = RazorpaySandboxClient(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
    )
    return RazorpayActionService(client)


def _map_error(exc: Exception) -> Exception:
    """Convert domain misses into HTTP exceptions."""
    if isinstance(exc, DomainCaseNotFound):
        return RecoveryNotFoundError(f"Recovery case not found: {exc.recovery_case_id}")
    if isinstance(exc, DomainActionNotFound):
        return ActionNotFoundError(f"Action execution not found: {exc.execution_id}")
    return exc


def _delivery(item: object) -> ActionDelivery:
    """Map a delivery DTO onto the HTTP model."""
    dump = item.model_dump() if hasattr(item, "model_dump") else dict(item)  # type: ignore[arg-type]
    return ActionDelivery.model_validate(dump)


def _execution(result: ActionExecutionResult) -> ActionExecutionResponse:
    """Map a domain execution onto the HTTP model."""
    set_recovery_case_id(str(result.recovery_case_id))
    set_execution_id(str(result.execution_id))
    return ActionExecutionResponse(
        execution_id=result.execution_id,
        recovery_case_id=result.recovery_case_id,
        idempotency_key=result.idempotency_key,
        planner_strategy=result.planner_strategy,
        action_type=result.action_type,
        display_status=result.display_status,
        execution_status=result.execution_status,
        action_chip=result.action_chip,
        scheduled_time=result.scheduled_time,
        executed_time=result.executed_time,
        retry_attempts=result.retry_attempts,
        payment_link=result.payment_link,
        delivery_status=result.delivery_status,
        deliveries=[_delivery(item) for item in result.deliveries],
        request_id=result.request_id,
        correlation_id=result.correlation_id,
        replayed=result.replayed,
        dead_lettered=result.dead_lettered,
        policy_reason=result.policy_reason,
        razorpay_resource_id=result.razorpay_resource_id,
        metadata=result.metadata,
    )


def _queue(result: object) -> SchedulerQueueMetrics:
    """Map nested scheduler queue metrics."""
    raw = getattr(result, "scheduler_queue", None)
    if raw is None:
        return SchedulerQueueMetrics()
    return SchedulerQueueMetrics(
        scheduled=getattr(raw, "scheduled", 0),
        running=getattr(raw, "running", 0),
        delayed=getattr(raw, "delayed", 0),
        dead_letter=getattr(raw, "dead_letter", 0),
    )


def _status(result: ActionStatusResult) -> ActionStatusResponse:
    """Map case status."""
    return ActionStatusResponse(
        recovery_case_id=result.recovery_case_id,
        latest=_execution(result.latest) if result.latest else None,
        history=[_execution(item) for item in result.history],
        active_scheduler_queue=result.active_scheduler_queue,
        scheduler_queue=_queue(result),
    )


def _dashboard(result: ActionDashboardSummary) -> ActionDashboardResponse:
    """Map dashboard KPIs."""
    return ActionDashboardResponse(
        scheduled_actions_today=result.scheduled_actions_today,
        payment_links_sent=result.payment_links_sent,
        successful_retries=result.successful_retries,
        failed_deliveries=result.failed_deliveries,
        active_scheduler_queue=result.active_scheduler_queue,
        scheduler_queue=_queue(result),
        chips=result.chips,
    )


def execute(
    db: Session,
    settings: Settings,
    recovery_case_id: UUID,
    *,
    request_id: str,
    correlation_id: str,
) -> ActionExecutionResponse:
    """Execute the current RecoveryPlan for a case."""
    try:
        result = execute_case(
            db,
            recovery_case_id,
            _razorpay(settings),
            request_id=request_id,
            correlation_id=correlation_id,
        )
        db.commit()
        record_action_execution(
            payment_link=result.payment_link,
            retry_attempts=result.retry_attempts,
        )
        return _execution(result)
    except Exception as exc:
        db.rollback()
        raise _map_error(exc) from exc


def schedule(
    db: Session,
    settings: Settings,
    recovery_case_id: UUID,
    *,
    request_id: str,
    correlation_id: str,
) -> ActionExecutionResponse:
    """Schedule WAIT_FOR_PAYDAY / HONOUR_PROMISE_TO_PAY (or any plan) without executing now."""
    try:
        result = schedule_case(
            db,
            recovery_case_id,
            _razorpay(settings),
            request_id=request_id,
            correlation_id=correlation_id,
        )
        db.commit()
        record_action_execution(
            payment_link=result.payment_link,
            retry_attempts=result.retry_attempts,
        )
        return _execution(result)
    except Exception as exc:
        db.rollback()
        raise _map_error(exc) from exc


def status(
    db: Session,
    recovery_case_id: UUID,
    *,
    request_id: str,
    correlation_id: str,
) -> ActionStatusResponse:
    """Latest execution status for a case."""
    try:
        result = get_case_status(
            db,
            recovery_case_id,
            request_id=request_id,
            correlation_id=correlation_id,
        )
        return _status(result)
    except Exception as exc:
        raise _map_error(exc) from exc


def replay(
    db: Session,
    settings: Settings,
    execution_id: UUID,
    *,
    request_id: str,
    correlation_id: str,
) -> ActionExecutionResponse:
    """Idempotent replay of one execution."""
    try:
        result = replay_execution(
            db,
            execution_id,
            _razorpay(settings),
            request_id=request_id,
            correlation_id=correlation_id,
        )
        db.commit()
        record_action_execution(
            payment_link=result.payment_link,
            retry_attempts=result.retry_attempts,
        )
        return _execution(result)
    except Exception as exc:
        db.rollback()
        raise _map_error(exc) from exc


def dashboard(
    db: Session,
    merchant_id: UUID | None,
) -> ActionDashboardResponse:
    """Merchant orchestrator KPIs."""
    result = get_dashboard_summary(db, merchant_id)
    return _dashboard(result)
