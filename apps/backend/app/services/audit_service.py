"""FastAPI adapter over the domain audit service.

Maps domain records onto compliance DTOs and domain misses onto HTTP
exceptions. SQL stays in ``services.audit_service``.
"""

from __future__ import annotations

from uuid import UUID

from sqlalchemy.orm import Session

from app.core.exceptions import (
    AuditEventNotFoundError,
    CorrelationNotFoundError,
    InvalidAuditFilterError,
)
from app.schemas.audit import (
    AuditEventResponse,
    AuditTimelineResponse,
    CorrelationTraceResponse,
    PolicyDecisionResponse,
)
from services.audit_service import AuditCaseNotFoundError as DomainCaseNotFound
from services.audit_service import AuditEventRecord
from services.audit_service import CorrelationNotFoundError as DomainCorrelationNotFound
from services.audit_service import InvalidAuditFilterError as DomainFilterError
from services.audit_service import get_audit_events as load_events
from services.audit_service import get_case_audit_timeline as load_timeline
from services.audit_service import get_correlation_trace as load_trace
from services.audit_service import get_policy_decisions as load_policy
from services.audit_service import parse_audit_filters


def _map_error(exc: Exception) -> Exception:
    """Convert a domain miss or filter error into an HTTP exception."""
    if isinstance(exc, DomainCaseNotFound):
        return AuditEventNotFoundError(
            f"Audit trail not found for case: {exc.recovery_case_id}"
        )
    if isinstance(exc, DomainCorrelationNotFound):
        return CorrelationNotFoundError(f"Correlation id not found: {exc.correlation_id}")
    if isinstance(exc, DomainFilterError):
        return InvalidAuditFilterError(str(exc))
    return exc


def _event_dto(record: AuditEventRecord) -> AuditEventResponse:
    """Map a domain event onto the HTTP DTO."""
    return AuditEventResponse(
        event_id=record.event_id,
        recovery_case_id=record.recovery_case_id,
        event_type=record.event_type,
        actor=record.actor,
        actor_type=record.actor_type,
        timestamp=record.timestamp,
        summary=record.summary,
        request_id=record.request_id,
        correlation_id=record.correlation_id,
        policy_decision=record.policy_decision,
        details=record.details,
    )


def get_case_audit_timeline(
    db: Session, recovery_case_id: UUID
) -> AuditTimelineResponse:
    """Return the chronological compliance timeline for one case.

    Args:
        db: Request-scoped SQLAlchemy session.
        recovery_case_id: Case to replay.

    Returns:
        Timeline DTO with mapped events.

    Raises:
        AuditEventNotFoundError: When the case does not exist.
    """
    try:
        timeline = load_timeline(db, recovery_case_id)
    except DomainCaseNotFound as exc:
        raise _map_error(exc) from exc
    events = [_event_dto(item) for item in timeline.events]
    return AuditTimelineResponse(
        recovery_case_id=timeline.recovery_case_id,
        recovery_status=timeline.recovery_status,
        event_count=len(events),
        events=events,
    )


def get_audit_events(
    db: Session,
    *,
    offset: int,
    limit: int,
    event_type: str | None = None,
    actor: str | None = None,
    recovery_case_id: UUID | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> tuple[list[AuditEventResponse], int]:
    """Return one page of explorer events, newest first.

    Args:
        db: Request-scoped SQLAlchemy session.
        offset: SQL offset.
        limit: Page length.
        event_type: AuditEventType filter.
        actor: ActorType or actor_name filter.
        recovery_case_id: Optional case scope.
        correlation_id: Payload or derived case id.
        request_id: Payload or audit row id.
        date_from: Inclusive created_at lower bound.
        date_to: Inclusive created_at upper bound.

    Returns:
        ``(items, total)`` ready for ``PaginatedResponse``.

    Raises:
        InvalidAuditFilterError: Unknown enum, date, or inverted range.
    """
    try:
        filters = parse_audit_filters(
            event_type=event_type,
            actor=actor,
            recovery_case_id=recovery_case_id,
            correlation_id=correlation_id,
            request_id=request_id,
            date_from=date_from,
            date_to=date_to,
        )
        page = load_events(db, filters, offset=offset, limit=limit)
    except DomainFilterError as exc:
        raise _map_error(exc) from exc
    return [_event_dto(item) for item in page.items], page.total


def get_correlation_trace(db: Session, correlation_id: str) -> CorrelationTraceResponse:
    """Return every event for one correlation id, oldest first.

    Args:
        db: Request-scoped SQLAlchemy session.
        correlation_id: Workflow correlation token.

    Returns:
        Ordered trace DTO.

    Raises:
        CorrelationNotFoundError: When nothing matches.
    """
    try:
        trace = load_trace(db, correlation_id)
    except DomainCorrelationNotFound as exc:
        raise _map_error(exc) from exc
    events = [_event_dto(item) for item in trace.events]
    return CorrelationTraceResponse(
        correlation_id=trace.correlation_id,
        event_count=len(events),
        events=events,
    )


def get_policy_decisions(
    db: Session, recovery_case_id: UUID
) -> list[PolicyDecisionResponse]:
    """Return mapped policy evaluations, or a placeholder ALLOW row.

    Args:
        db: Request-scoped SQLAlchemy session.
        recovery_case_id: Case whose gates are listed.

    Returns:
        Reviewer-facing policy rows.

    Raises:
        AuditEventNotFoundError: When the case does not exist.
    """
    try:
        rows = load_policy(db, recovery_case_id)
    except DomainCaseNotFound as exc:
        raise _map_error(exc) from exc
    return [
        PolicyDecisionResponse(
            recovery_case_id=row.recovery_case_id,
            event_id=row.event_id,
            policy_name=row.policy_name,
            decision=row.decision,
            reason=row.reason,
            evaluated_at=row.evaluated_at,
        )
        for row in rows
    ]
