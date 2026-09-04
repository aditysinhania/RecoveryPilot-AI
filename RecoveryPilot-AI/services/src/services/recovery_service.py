"""Read-only recovery queue queries.

Routers must not run SQL. No AI diagnosis, policy evaluation, Razorpay
execution, or scheduler work lives here.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import UTC, date, datetime, time
from enum import Enum
from typing import Any, TypeVar
from uuid import UUID

from sqlalchemy import func, or_, select
from sqlalchemy.orm import Session, selectinload

from database.models import (
    AuditLog,
    Customer,
    Payment,
    PromiseToPay,
    RecoveryAction,
    RecoveryCase,
    Subscription,
    WebhookEvent,
)
from shared.enums import (
    CustomerSegment,
    ExecutionStatus,
    FailureReason,
    PaymentMethod,
    PromiseStatus,
    RecoveryStatus,
)

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Enum)

AT_RISK_STATUSES: frozenset[RecoveryStatus] = frozenset(
    {
        RecoveryStatus.OPEN,
        RecoveryStatus.DIAGNOSED,
        RecoveryStatus.WAITING_RETRY,
        RecoveryStatus.WAITING_PROMISE,
        RecoveryStatus.ESCALATED,
    }
)

_PRIORITY_BANDS: dict[str, tuple[float | None, float | None]] = {
    "HIGH": (0.8, None),
    "MEDIUM": (0.6, 0.8),
    "LOW": (None, 0.6),
}


class RecoveryCaseNotFoundError(Exception):
    """Raised when ``recovery_case_id`` does not match a recovery_cases row."""

    def __init__(self, recovery_case_id: UUID) -> None:
        self.recovery_case_id = recovery_case_id
        super().__init__(f"Recovery case not found: {recovery_case_id}")


class InvalidFilterError(Exception):
    """Raised when a queue filter cannot be interpreted."""


class InvalidDateRangeError(Exception):
    """Raised when ``date_from`` is after ``date_to``."""


@dataclass(frozen=True)
class QueueFilters:
    """Normalized queue filters after enum and date parsing."""

    merchant_id: UUID | None = None
    status: RecoveryStatus | None = None
    failure_reason: FailureReason | None = None
    customer_segment: CustomerSegment | None = None
    min_priority: float | None = None
    max_priority: float | None = None
    payment_method: PaymentMethod | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass(frozen=True)
class QueueRow:
    """One queue row: case plus the joined customer and payment."""

    case: RecoveryCase
    customer: Customer
    payment: Payment


@dataclass(frozen=True)
class QueuePageResult:
    """One page of queue rows and the matching total."""

    items: list[QueueRow]
    total: int


@dataclass(frozen=True)
class RecoveryCaseDetail:
    """Loaded graph for the case-detail endpoint."""

    case: RecoveryCase
    customer: Customer
    payment: Payment
    subscription: Subscription | None
    latest_action: RecoveryAction | None
    promise: PromiseToPay | None


@dataclass(frozen=True)
class TimelineEvent:
    """One journey event before HTTP mapping."""

    event_type: str
    occurred_at: datetime
    summary: str
    source: str
    reference_id: UUID | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class RecoverySummaryTotals:
    """Live aggregate counts and paise totals."""

    open_cases: int = 0
    recovered_cases: int = 0
    stopped_cases: int = 0
    escalated_cases: int = 0
    waiting_retry: int = 0
    waiting_promise: int = 0
    total_revenue_at_risk: int = 0
    recovered_revenue: int = 0
    recovery_rate: float = 0.0


def _parse_enum(raw: str | None, enum_cls: type[E], field_name: str) -> E | None:
    """Parse a StrEnum from a query string."""
    if raw is None or not str(raw).strip():
        return None
    value = str(raw).strip()
    try:
        return enum_cls(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_cls)
        raise InvalidFilterError(
            f"Invalid {field_name} '{value}'. Allowed: {allowed}"
        ) from exc


def _parse_datetime(raw: str | None, *, end_of_day: bool) -> datetime | None:
    """Parse an ISO date or datetime. Dates are UTC start/end of day."""
    if raw is None or not str(raw).strip():
        return None
    value = str(raw).strip()
    try:
        if "T" in value:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=UTC)
            return parsed
        day = date.fromisoformat(value)
        bound = time.max if end_of_day else time.min
        return datetime.combine(day, bound, tzinfo=UTC)
    except ValueError as exc:
        raise InvalidFilterError(
            f"Invalid date '{value}'. Use YYYY-MM-DD or ISO-8601 datetime."
        ) from exc


def _parse_priority(raw: str | None) -> tuple[float | None, float | None]:
    """Parse ``priority`` as HIGH/MEDIUM/LOW or a minimum score."""
    if raw is None or not str(raw).strip():
        return None, None
    key = str(raw).strip().upper()
    if key in _PRIORITY_BANDS:
        return _PRIORITY_BANDS[key]
    try:
        score = float(raw)
    except ValueError as exc:
        raise InvalidFilterError(
            "Invalid priority. Use HIGH, MEDIUM, LOW, or a number >= 0."
        ) from exc
    if score < 0:
        raise InvalidFilterError("Invalid priority. Score must be >= 0.")
    return score, None


def parse_queue_filters(
    *,
    merchant_id: UUID | None = None,
    status: str | None = None,
    failure_reason: str | None = None,
    customer_segment: str | None = None,
    priority: str | None = None,
    payment_method: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> QueueFilters:
    """Validate and normalize queue query parameters.

    Args:
        merchant_id: Optional tenant scope.
        status: RecoveryStatus value.
        failure_reason: Payment or diagnosed FailureReason.
        customer_segment: CustomerSegment value.
        priority: HIGH / MEDIUM / LOW or a minimum priority_score.
        payment_method: PaymentMethod value.
        date_from: Inclusive lower bound on payment.created_at.
        date_to: Inclusive upper bound on payment.created_at.

    Returns:
        Typed filters ready for SQL.

    Raises:
        InvalidFilterError: Unknown enum, band, or date format.
        InvalidDateRangeError: ``date_from`` is after ``date_to``.
    """
    start = _parse_datetime(date_from, end_of_day=False)
    end = _parse_datetime(date_to, end_of_day=True)
    if start is not None and end is not None and start > end:
        raise InvalidDateRangeError("date_from must be on or before date_to")
    min_priority, max_priority = _parse_priority(priority)
    return QueueFilters(
        merchant_id=merchant_id,
        status=_parse_enum(status, RecoveryStatus, "status"),
        failure_reason=_parse_enum(failure_reason, FailureReason, "failure_reason"),
        customer_segment=_parse_enum(
            customer_segment, CustomerSegment, "customer_segment"
        ),
        min_priority=min_priority,
        max_priority=max_priority,
        payment_method=_parse_enum(payment_method, PaymentMethod, "payment_method"),
        date_from=start,
        date_to=end,
    )


def _queue_clauses(filters: QueueFilters) -> list[Any]:
    """SQLAlchemy WHERE clauses for the recovery queue."""
    clauses: list[Any] = []
    if filters.merchant_id is not None:
        clauses.append(RecoveryCase.merchant_id == filters.merchant_id)
    if filters.status is not None:
        clauses.append(RecoveryCase.recovery_status == filters.status)
    if filters.failure_reason is not None:
        clauses.append(
            or_(
                Payment.failure_reason == filters.failure_reason,
                RecoveryCase.diagnosed_reason == filters.failure_reason,
            )
        )
    if filters.customer_segment is not None:
        clauses.append(Customer.customer_segment == filters.customer_segment)
    score = func.coalesce(RecoveryCase.priority_score, 0.0)
    if filters.min_priority is not None:
        clauses.append(score >= filters.min_priority)
    if filters.max_priority is not None:
        clauses.append(score < filters.max_priority)
    if filters.payment_method is not None:
        clauses.append(Payment.payment_method == filters.payment_method)
    if filters.date_from is not None:
        clauses.append(Payment.created_at >= filters.date_from)
    if filters.date_to is not None:
        clauses.append(Payment.created_at <= filters.date_to)
    return clauses


def get_recovery_queue(
    db: Session,
    filters: QueueFilters,
    *,
    offset: int,
    limit: int,
) -> QueuePageResult:
    """Return one page of the recovery queue.

    Default sort: priority_score descending (nulls last), then oldest
    failed payment first (``payments.created_at`` ascending).

    Args:
        db: Request-scoped SQLAlchemy session.
        filters: Already-validated queue filters.
        offset: SQL offset.
        limit: Page length.

    Returns:
        Page rows plus the total matching count.
    """
    clauses = _queue_clauses(filters)
    count_stmt = (
        select(func.count())
        .select_from(RecoveryCase)
        .join(Payment, Payment.id == RecoveryCase.payment_id)
        .join(Customer, Customer.id == RecoveryCase.customer_id)
    )
    list_stmt = (
        select(RecoveryCase, Customer, Payment)
        .join(Payment, Payment.id == RecoveryCase.payment_id)
        .join(Customer, Customer.id == RecoveryCase.customer_id)
    )
    if clauses:
        count_stmt = count_stmt.where(*clauses)
        list_stmt = list_stmt.where(*clauses)
    total = int(db.scalar(count_stmt) or 0)
    rows = db.execute(
        list_stmt.order_by(
            RecoveryCase.priority_score.desc().nulls_last(),
            Payment.created_at.asc(),
        )
        .offset(offset)
        .limit(limit)
    ).all()
    items = [
        QueueRow(case=case, customer=customer, payment=payment)
        for case, customer, payment in rows
    ]
    logger.info(
        "recovery.queue",
        extra={
            "offset": offset,
            "limit": limit,
            "total": total,
            "merchant_id": str(filters.merchant_id) if filters.merchant_id else None,
        },
    )
    return QueuePageResult(items=items, total=total)


def _latest_action(actions: list[RecoveryAction]) -> RecoveryAction | None:
    """Most recently created action, if any."""
    if not actions:
        return None
    return max(actions, key=lambda row: row.created_at)


def _current_promise(promises: list[PromiseToPay]) -> PromiseToPay | None:
    """Prefer an OPEN promise; otherwise the most recently created one."""
    if not promises:
        return None
    open_promises = [row for row in promises if row.promise_status == PromiseStatus.OPEN]
    pool = open_promises or promises
    return max(pool, key=lambda row: row.created_at)


def get_recovery_case(db: Session, recovery_case_id: UUID) -> RecoveryCaseDetail:
    """Load one recovery case with customer, payment, subscription, action, promise.

    Args:
        db: Request-scoped SQLAlchemy session.
        recovery_case_id: Primary key to look up.

    Returns:
        The case graph for the detail drawer.

    Raises:
        RecoveryCaseNotFoundError: When no row exists.
    """
    case = db.scalar(
        select(RecoveryCase)
        .options(
            selectinload(RecoveryCase.customer),
            selectinload(RecoveryCase.payment).selectinload(Payment.subscription),
            selectinload(RecoveryCase.actions),
            selectinload(RecoveryCase.promises),
        )
        .where(RecoveryCase.id == recovery_case_id)
    )
    if case is None:
        logger.info(
            "recovery.case.not_found",
            extra={"recovery_case_id": str(recovery_case_id)},
        )
        raise RecoveryCaseNotFoundError(recovery_case_id)
    logger.info(
        "recovery.case",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "recovery_status": str(case.recovery_status),
        },
    )
    return RecoveryCaseDetail(
        case=case,
        customer=case.customer,
        payment=case.payment,
        subscription=case.payment.subscription,
        latest_action=_latest_action(list(case.actions)),
        promise=_current_promise(list(case.promises)),
    )


def _webhook_events_for_payment(db: Session, payment: Payment) -> list[WebhookEvent]:
    """Match inbox rows whose JSON payload names this payment's Razorpay id."""
    if not payment.razorpay_payment_id:
        return []
    return list(
        db.scalars(
            select(WebhookEvent)
            .where(
                WebhookEvent.payload.contains(
                    {
                        "payload": {
                            "payment": {"entity": {"id": payment.razorpay_payment_id}}
                        }
                    }
                )
            )
            .order_by(WebhookEvent.created_at.asc())
        ).all()
    )


def get_recovery_timeline(
    db: Session,
    recovery_case_id: UUID,
) -> list[TimelineEvent]:
    """Build a chronological journey for one recovery case.

    Includes payment failure, diagnosis, scheduled/executed actions,
    matching webhook inbox rows, and audit summaries. Sorted ascending.

    Args:
        db: Request-scoped SQLAlchemy session.
        recovery_case_id: Case whose journey is requested.

    Returns:
        Events ordered by ``occurred_at`` ascending.

    Raises:
        RecoveryCaseNotFoundError: When no row exists.
    """
    detail = get_recovery_case(db, recovery_case_id)
    case = detail.case
    payment = detail.payment
    events: list[TimelineEvent] = []

    events.append(
        TimelineEvent(
            event_type="payment_failed",
            occurred_at=payment.created_at,
            summary=f"Payment {payment.payment_status} for {payment.amount} paise",
            source="payment",
            reference_id=payment.id,
            details={
                "payment_status": str(payment.payment_status),
                "failure_reason": (
                    str(payment.failure_reason) if payment.failure_reason else None
                ),
                "amount": payment.amount,
            },
        )
    )

    if case.diagnosed_reason is not None or case.diagnosis_model is not None:
        diagnosed_at = case.recovery_started_at or case.created_at
        events.append(
            TimelineEvent(
                event_type="diagnosis_created",
                occurred_at=diagnosed_at,
                summary=f"Diagnosed as {case.diagnosed_reason or 'UNKNOWN'}",
                source="diagnosis",
                reference_id=case.id,
                details={
                    "diagnosed_reason": (
                        str(case.diagnosed_reason) if case.diagnosed_reason else None
                    ),
                    "diagnosis_model": case.diagnosis_model,
                    "diagnosis_version": case.diagnosis_version,
                    "ai_confidence": case.ai_confidence,
                },
            )
        )

    for action in sorted(case.actions, key=lambda row: row.created_at):
        scheduled_at = action.scheduled_time or action.created_at
        events.append(
            TimelineEvent(
                event_type="action_scheduled",
                occurred_at=scheduled_at,
                summary=f"{action.action_type} scheduled ({action.execution_status})",
                source="action",
                reference_id=action.id,
                details={
                    "action_type": str(action.action_type),
                    "execution_status": str(action.execution_status),
                    "retry_number": action.retry_number,
                },
            )
        )
        executed_statuses = {
            ExecutionStatus.SUCCEEDED,
            ExecutionStatus.FAILED,
            ExecutionStatus.SKIPPED,
        }
        if action.executed_time is not None or action.execution_status in executed_statuses:
            executed_at = action.executed_time or action.created_at
            events.append(
                TimelineEvent(
                    event_type="action_executed",
                    occurred_at=executed_at,
                    summary=f"{action.action_type} {action.execution_status}",
                    source="action",
                    reference_id=action.id,
                    details={
                        "action_type": str(action.action_type),
                        "execution_status": str(action.execution_status),
                        "response_code": action.response_code,
                    },
                )
            )

    for hook in _webhook_events_for_payment(db, payment):
        events.append(
            TimelineEvent(
                event_type="webhook_update",
                occurred_at=hook.created_at,
                summary=f"Webhook {hook.event_type}",
                source="webhook",
                reference_id=hook.id,
                details={
                    "event_type": hook.event_type,
                    "signature_verified": hook.signature_verified,
                    "processed": hook.processed_at is not None,
                },
            )
        )

    audits = db.scalars(
        select(AuditLog)
        .where(AuditLog.recovery_case_id == recovery_case_id)
        .order_by(AuditLog.created_at.asc())
    ).all()
    for audit in audits:
        events.append(
            TimelineEvent(
                event_type="audit",
                occurred_at=audit.created_at,
                summary=audit.event_summary,
                source="audit",
                reference_id=audit.id,
                details={
                    "event_type": str(audit.event_type),
                    "actor_type": str(audit.actor_type),
                },
            )
        )

    events.sort(
        key=lambda item: (item.occurred_at, item.event_type, str(item.reference_id or ""))
    )
    logger.info(
        "recovery.timeline",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "event_count": len(events),
        },
    )
    return events


def _sum_amount(
    db: Session, statuses: set[RecoveryStatus], merchant_id: UUID | None
) -> int:
    """Sum payment.amount for cases in ``statuses``."""
    stmt = (
        select(func.coalesce(func.sum(Payment.amount), 0))
        .select_from(RecoveryCase)
        .join(Payment, Payment.id == RecoveryCase.payment_id)
        .where(RecoveryCase.recovery_status.in_(statuses))
    )
    if merchant_id is not None:
        stmt = stmt.where(RecoveryCase.merchant_id == merchant_id)
    return int(db.scalar(stmt) or 0)


def get_recovery_summary(
    db: Session,
    merchant_id: UUID | None = None,
) -> RecoverySummaryTotals:
    """Return live case counts and revenue totals.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Optional tenant scope.

    Returns:
        Counts by recovery_status plus paise at-risk / recovered and rate.
    """
    count_stmt = select(RecoveryCase.recovery_status, func.count()).group_by(
        RecoveryCase.recovery_status
    )
    if merchant_id is not None:
        count_stmt = count_stmt.where(RecoveryCase.merchant_id == merchant_id)
    counts = {status: 0 for status in RecoveryStatus}
    for status, count in db.execute(count_stmt).all():
        counts[status] = int(count)

    at_risk = _sum_amount(db, set(AT_RISK_STATUSES), merchant_id)
    recovered = _sum_amount(db, {RecoveryStatus.RECOVERED}, merchant_id)
    denominator = at_risk + recovered
    rate = round(recovered / denominator, 4) if denominator else 0.0
    result = RecoverySummaryTotals(
        open_cases=counts[RecoveryStatus.OPEN],
        recovered_cases=counts[RecoveryStatus.RECOVERED],
        stopped_cases=counts[RecoveryStatus.STOPPED],
        escalated_cases=counts[RecoveryStatus.ESCALATED],
        waiting_retry=counts[RecoveryStatus.WAITING_RETRY],
        waiting_promise=counts[RecoveryStatus.WAITING_PROMISE],
        total_revenue_at_risk=at_risk,
        recovered_revenue=recovered,
        recovery_rate=rate,
    )
    logger.info(
        "recovery.summary",
        extra={
            "merchant_id": str(merchant_id) if merchant_id else None,
            "open_cases": result.open_cases,
            "recovered_cases": result.recovered_cases,
            "total_revenue_at_risk": result.total_revenue_at_risk,
        },
    )
    return result
