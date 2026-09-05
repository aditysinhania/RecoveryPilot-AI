"""FastAPI adapter over the domain recovery service.

Maps ORM results onto dashboard Pydantic models and domain errors onto
HTTP exceptions. SQL stays in ``services.recovery_service``.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    InvalidDateRangeError,
    InvalidFilterError,
    RecoveryNotFoundError,
)
from app.schemas.recovery import (
    RecoveryCaseAuditEvent,
    RecoveryCaseResponse,
    RecoveryQueueItem,
    RecoverySummaryResponse,
    RecoveryTimelineEvent,
    TimelineEventType,
)
from services.audit_service import list_case_audit_events as load_case_audit
from services.recovery_service import InvalidDateRangeError as DomainDateRangeError
from services.recovery_service import InvalidFilterError as DomainFilterError
from services.recovery_service import RecoveryCaseNotFoundError as DomainCaseNotFound
from services.recovery_service import (
    get_recovery_case as load_case,
)
from services.recovery_service import (
    get_recovery_queue as load_queue,
)
from services.recovery_service import (
    get_recovery_summary as load_summary,
)
from services.recovery_service import (
    get_recovery_timeline as load_timeline,
)
from services.recovery_service import parse_queue_filters
from shared.schemas.customer import CustomerRead
from shared.schemas.payment import PaymentRead
from shared.schemas.promise_to_pay import PromiseToPayRead
from shared.schemas.recovery_action import RecoveryActionRead
from shared.schemas.subscription import SubscriptionRead


def _map_error(exc: Exception) -> Exception:
    """Convert a domain miss or filter error into an HTTP exception."""
    if isinstance(exc, DomainCaseNotFound):
        return RecoveryNotFoundError(f"Recovery case not found: {exc.recovery_case_id}")
    if isinstance(exc, DomainDateRangeError):
        return InvalidDateRangeError(str(exc))
    if isinstance(exc, DomainFilterError):
        return InvalidFilterError(str(exc))
    return exc


def get_recovery_queue(
    db: Session,
    *,
    offset: int,
    limit: int,
    merchant_id: UUID | None = None,
    status: str | None = None,
    failure_reason: str | None = None,
    customer_segment: str | None = None,
    priority: str | None = None,
    payment_method: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[list[RecoveryQueueItem], int]:
    """Return one page of queue DTOs and the matching total.

    Args:
        db: Request-scoped SQLAlchemy session.
        offset: SQL offset.
        limit: Page length.
        merchant_id: Optional tenant scope.
        status: RecoveryStatus filter.
        failure_reason: FailureReason filter.
        customer_segment: CustomerSegment filter.
        priority: HIGH / MEDIUM / LOW or a minimum score.
        payment_method: PaymentMethod filter.
        date_from: Inclusive lower bound on payment.created_at.
        date_to: Inclusive upper bound on payment.created_at.

    Returns:
        ``(items, total)`` ready for ``PaginatedResponse``.

    Raises:
        InvalidFilterError: Unknown filter value.
        InvalidDateRangeError: ``date_from`` is after ``date_to``.
    """
    try:
        filters = parse_queue_filters(
            merchant_id=merchant_id,
            status=status,
            failure_reason=failure_reason,
            customer_segment=customer_segment,
            priority=priority,
            payment_method=payment_method,
            date_from=date_from,
            date_to=date_to,
        )
        page = load_queue(db, filters, offset=offset, limit=limit)
    except (DomainCaseNotFound, DomainDateRangeError, DomainFilterError) as exc:
        raise _map_error(exc) from exc
    items = [
        RecoveryQueueItem(
            recovery_case_id=row.case.id,
            merchant_id=row.case.merchant_id,
            customer_id=row.customer.id,
            payment_id=row.payment.id,
            customer_name=row.customer.full_name,
            customer_segment=row.customer.customer_segment,
            amount=row.payment.amount,
            currency=row.payment.currency,
            payment_method=row.payment.payment_method,
            failure_reason=row.payment.failure_reason,
            diagnosed_reason=row.case.diagnosed_reason,
            recovery_status=row.case.recovery_status,
            priority_score=row.case.priority_score,
            ai_confidence=row.case.ai_confidence,
            payment_due_date=row.payment.payment_due_date,
            failed_at=row.payment.created_at,
            recovery_started_at=row.case.recovery_started_at,
        )
        for row in page.items
    ]
    return items, page.total


def get_recovery_case(db: Session, recovery_case_id: UUID) -> RecoveryCaseResponse:
    """Return the case-detail DTO.

    Args:
        db: Request-scoped SQLAlchemy session.
        recovery_case_id: Case to load.

    Returns:
        Customer, payment, subscription, diagnosis, latest action, promise.

    Raises:
        RecoveryNotFoundError: When the case does not exist.
    """
    try:
        detail = load_case(db, recovery_case_id)
    except DomainCaseNotFound as exc:
        raise _map_error(exc) from exc
    case = detail.case
    return RecoveryCaseResponse(
        recovery_case_id=case.id,
        merchant_id=case.merchant_id,
        recovery_status=case.recovery_status,
        diagnosed_reason=case.diagnosed_reason,
        diagnosis_model=case.diagnosis_model,
        diagnosis_version=case.diagnosis_version,
        ai_confidence=case.ai_confidence,
        priority_score=case.priority_score,
        recovery_started_at=case.recovery_started_at,
        recovery_completed_at=case.recovery_completed_at,
        created_at=case.created_at,
        updated_at=case.updated_at,
        customer=CustomerRead.model_validate(detail.customer),
        payment=PaymentRead.model_validate(detail.payment),
        subscription=(
            SubscriptionRead.model_validate(detail.subscription)
            if detail.subscription is not None
            else None
        ),
        latest_action=(
            RecoveryActionRead.model_validate(detail.latest_action)
            if detail.latest_action is not None
            else None
        ),
        promise_to_pay=(
            PromiseToPayRead.model_validate(detail.promise)
            if detail.promise is not None
            else None
        ),
        promise_status=detail.promise.promise_status if detail.promise is not None else None,
    )


def get_recovery_timeline(
    db: Session, recovery_case_id: UUID
) -> list[RecoveryTimelineEvent]:
    """Return chronological journey events for one case.

    Args:
        db: Request-scoped SQLAlchemy session.
        recovery_case_id: Case whose timeline is requested.

    Returns:
        Events sorted ascending by ``occurred_at``.

    Raises:
        RecoveryNotFoundError: When the case does not exist.
    """
    try:
        events = load_timeline(db, recovery_case_id)
    except DomainCaseNotFound as exc:
        raise _map_error(exc) from exc
    return [
        RecoveryTimelineEvent(
            event_type=TimelineEventType(item.event_type),
            occurred_at=item.occurred_at,
            summary=item.summary,
            source=item.source,
            reference_id=item.reference_id,
            details=item.details,
        )
        for item in events
    ]


def get_recovery_summary(
    db: Session, merchant_id: UUID | None = None
) -> RecoverySummaryResponse:
    """Return live recovery KPIs.

    Args:
        db: Request-scoped SQLAlchemy session.
        merchant_id: Optional tenant scope.

    Returns:
        Case counts, paise totals, and recovery rate.
    """
    totals = load_summary(db, merchant_id)
    return RecoverySummaryResponse(
        open_cases=totals.open_cases,
        recovered_cases=totals.recovered_cases,
        stopped_cases=totals.stopped_cases,
        escalated_cases=totals.escalated_cases,
        waiting_retry=totals.waiting_retry,
        waiting_promise=totals.waiting_promise,
        total_revenue_at_risk=totals.total_revenue_at_risk,
        recovered_revenue=totals.recovered_revenue,
        recovery_rate=totals.recovery_rate,
    )


def get_case_audit_events(
    db: Session, recovery_case_id: UUID
) -> list[RecoveryCaseAuditEvent]:
    """Return ``audit_logs`` for a case, newest first. Empty list if none exist.

    Args:
        db: Request-scoped SQLAlchemy session.
        recovery_case_id: Case whose trail is listed.

    Returns:
        Audit DTOs. Unknown ids yield ``[]``, not 404.
    """
    rows = load_case_audit(db, recovery_case_id)
    return [
        RecoveryCaseAuditEvent(
            event_id=row.event_id,
            event_type=row.event_type,
            actor=row.actor,
            status=row.status,
            request_id=row.request_id,
            correlation_id=row.correlation_id,
            metadata=row.metadata,
            created_at=row.created_at,
        )
        for row in rows
    ]
