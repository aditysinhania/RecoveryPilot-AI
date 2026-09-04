"""Read-only audit and compliance replay queries.

Routers must not run SQL. Stored ``structured_payload`` JSON is never mutated.
No AI, Razorpay, or scheduler work lives here.
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
    Payment,
    RecoveryAction,
    RecoveryCase,
    WebhookEvent,
)
from shared.enums import (
    ActorType,
    AuditEventType,
    ExecutionStatus,
    PolicyDecision,
    RecoveryStatus,
)

logger = logging.getLogger(__name__)

E = TypeVar("E", bound=Enum)

PLACEHOLDER_POLICY_NAME = "recovery_policy_v1"
PLACEHOLDER_POLICY_REASON = "No policy engine evaluation recorded for this case."
_SAFE_PAYLOAD_KEYS = (
    "reason",
    "failure_reason",
    "diagnosed_reason",
    "model",
    "version",
    "confidence",
    "payment_id",
    "event",
    "action_type",
    "policy_name",
    "retry_number",
)


class AuditCaseNotFoundError(Exception):
    """Raised when a recovery case has no audit timeline to replay."""

    def __init__(self, recovery_case_id: UUID) -> None:
        self.recovery_case_id = recovery_case_id
        super().__init__(f"Audit trail not found for case: {recovery_case_id}")


class CorrelationNotFoundError(Exception):
    """Raised when no events share the given correlation id."""

    def __init__(self, correlation_id: str) -> None:
        self.correlation_id = correlation_id
        super().__init__(f"Correlation id not found: {correlation_id}")


class InvalidAuditFilterError(Exception):
    """Raised when an explorer filter cannot be interpreted."""


@dataclass(frozen=True)
class AuditEventFilters:
    """Normalized explorer filters."""

    event_type: AuditEventType | None = None
    actor_type: ActorType | None = None
    actor_name: str | None = None
    recovery_case_id: UUID | None = None
    correlation_id: str | None = None
    request_id: str | None = None
    date_from: datetime | None = None
    date_to: datetime | None = None


@dataclass(frozen=True)
class AuditEventRecord:
    """One replayable event after human-readable mapping."""

    event_id: UUID | None
    recovery_case_id: UUID | None
    event_type: str
    actor: str
    actor_type: ActorType | None
    timestamp: datetime
    summary: str
    request_id: str
    correlation_id: str
    policy_decision: str | None = None
    details: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AuditEventPage:
    """One page of explorer rows plus the matching total."""

    items: list[AuditEventRecord]
    total: int


@dataclass(frozen=True)
class CaseAuditTimeline:
    """Case-scoped chronological trail."""

    recovery_case_id: UUID
    recovery_status: RecoveryStatus | None
    events: list[AuditEventRecord]


@dataclass(frozen=True)
class CorrelationTrace:
    """All events sharing one correlation id, oldest first."""

    correlation_id: str
    events: list[AuditEventRecord]


@dataclass(frozen=True)
class PolicyDecisionRecord:
    """One mapped policy evaluation."""

    recovery_case_id: UUID
    event_id: UUID | None
    policy_name: str
    decision: str
    reason: str
    evaluated_at: datetime


def _parse_enum(raw: str | None, enum_cls: type[E], field_name: str) -> E | None:
    """Parse a StrEnum from a query string."""
    if raw is None or not str(raw).strip():
        return None
    value = str(raw).strip()
    try:
        return enum_cls(value)
    except ValueError as exc:
        allowed = ", ".join(item.value for item in enum_cls)
        raise InvalidAuditFilterError(
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
        raise InvalidAuditFilterError(
            f"Invalid date '{value}'. Use YYYY-MM-DD or ISO-8601 datetime."
        ) from exc


def parse_audit_filters(
    *,
    event_type: str | None = None,
    actor: str | None = None,
    recovery_case_id: UUID | None = None,
    correlation_id: str | None = None,
    request_id: str | None = None,
    date_from: str | None = None,
    date_to: str | None = None,
) -> AuditEventFilters:
    """Validate explorer query parameters.

    Args:
        event_type: AuditEventType value.
        actor: ActorType value or an actor_name substring.
        recovery_case_id: Optional case scope.
        correlation_id: Payload key or derived case id.
        request_id: Payload key or audit row id.
        date_from: Inclusive lower bound on created_at.
        date_to: Inclusive upper bound on created_at.

    Returns:
        Typed filters ready for SQL.

    Raises:
        InvalidAuditFilterError: Unknown enum, date format, or inverted range.
    """
    start = _parse_datetime(date_from, end_of_day=False)
    end = _parse_datetime(date_to, end_of_day=True)
    if start is not None and end is not None and start > end:
        raise InvalidAuditFilterError("date_from must be on or before date_to")
    actor_type: ActorType | None = None
    actor_name: str | None = None
    if actor is not None and str(actor).strip():
        token = str(actor).strip()
        try:
            actor_type = ActorType(token)
        except ValueError:
            actor_name = token
    return AuditEventFilters(
        event_type=_parse_enum(event_type, AuditEventType, "event_type"),
        actor_type=actor_type,
        actor_name=actor_name,
        recovery_case_id=recovery_case_id,
        correlation_id=correlation_id.strip() if correlation_id and correlation_id.strip() else None,
        request_id=request_id.strip() if request_id and request_id.strip() else None,
        date_from=start,
        date_to=end,
    )


def _payload_dict(raw: Any) -> dict[str, Any]:
    """Return a dict view of structured_payload without mutating storage."""
    if isinstance(raw, dict):
        return raw
    return {}


def _human_details(payload: dict[str, Any]) -> dict[str, Any]:
    """Copy a small safe subset of payload keys for reviewers."""
    return {key: payload[key] for key in _SAFE_PAYLOAD_KEYS if key in payload}


def _present_decision(
    stored: PolicyDecision | None,
    event_type: AuditEventType | str | None,
) -> str | None:
    """Map stored ALLOW/BLOCK/ESCALATE onto reviewer ALLOW/DENY/ESCALATE/STOP."""
    event_name = str(event_type) if event_type is not None else ""
    if event_name == AuditEventType.RECOVERY_STOPPED:
        return "STOP"
    if stored == PolicyDecision.BLOCK:
        return "DENY"
    if stored == PolicyDecision.ALLOW:
        return "ALLOW"
    if stored == PolicyDecision.ESCALATE or event_name == AuditEventType.ESCALATED:
        return "ESCALATE"
    return None


def _ids_for_log(log: AuditLog) -> tuple[str, str]:
    """Derive request_id and correlation_id from payload, then stable fallbacks.

    Simulator rows do not store those keys. Correlation falls back to the
    recovery case id (one workflow). Request id falls back to the audit row id.
    """
    payload = _payload_dict(log.structured_payload)
    request_id = str(payload.get("request_id") or payload.get("requestId") or log.id)
    correlation_id = str(
        payload.get("correlation_id")
        or payload.get("correlationId")
        or log.recovery_case_id
        or log.id
    )
    return request_id, correlation_id


def _record_from_log(log: AuditLog) -> AuditEventRecord:
    """Map one audit_logs row to a human-readable event. JSONB is not rewritten."""
    payload = _payload_dict(log.structured_payload)
    request_id, correlation_id = _ids_for_log(log)
    return AuditEventRecord(
        event_id=log.id,
        recovery_case_id=log.recovery_case_id,
        event_type=str(log.event_type),
        actor=log.actor_name,
        actor_type=log.actor_type,
        timestamp=log.created_at,
        summary=log.event_summary,
        request_id=request_id,
        correlation_id=correlation_id,
        policy_decision=_present_decision(log.policy_decision, log.event_type),
        details=_human_details(payload),
    )


def _synthetic_event(
    *,
    event_type: str,
    actor: str,
    actor_type: ActorType,
    timestamp: datetime,
    summary: str,
    recovery_case_id: UUID,
    request_id: str,
    details: dict[str, Any] | None = None,
    policy_decision: str | None = None,
    event_id: UUID | None = None,
) -> AuditEventRecord:
    """Build a gap-fill event when audit_logs does not cover a journey step."""
    return AuditEventRecord(
        event_id=event_id,
        recovery_case_id=recovery_case_id,
        event_type=event_type,
        actor=actor,
        actor_type=actor_type,
        timestamp=timestamp,
        summary=summary,
        request_id=request_id,
        correlation_id=str(recovery_case_id),
        policy_decision=policy_decision,
        details=details or {},
    )


def _try_uuid(value: str) -> UUID | None:
    """Return a UUID if ``value`` parses, else None."""
    try:
        return UUID(value)
    except ValueError:
        return None


def _correlation_clauses(correlation_id: str) -> list[Any]:
    """Match payload correlation_id or a recovery-case / row UUID fallback."""
    clauses: list[Any] = [
        AuditLog.structured_payload["correlation_id"].as_string() == correlation_id,
        AuditLog.structured_payload["correlationId"].as_string() == correlation_id,
    ]
    as_uuid = _try_uuid(correlation_id)
    if as_uuid is not None:
        clauses.append(AuditLog.recovery_case_id == as_uuid)
        clauses.append(AuditLog.id == as_uuid)
    return clauses


def _request_id_clauses(request_id: str) -> list[Any]:
    """Match payload request_id or the audit row UUID."""
    clauses: list[Any] = [
        AuditLog.structured_payload["request_id"].as_string() == request_id,
        AuditLog.structured_payload["requestId"].as_string() == request_id,
    ]
    as_uuid = _try_uuid(request_id)
    if as_uuid is not None:
        clauses.append(AuditLog.id == as_uuid)
    return clauses


def _explorer_clauses(filters: AuditEventFilters) -> list[Any]:
    """WHERE clauses for the events explorer."""
    clauses: list[Any] = []
    if filters.event_type is not None:
        clauses.append(AuditLog.event_type == filters.event_type)
    if filters.actor_type is not None:
        clauses.append(AuditLog.actor_type == filters.actor_type)
    if filters.actor_name is not None:
        clauses.append(AuditLog.actor_name.ilike(f"%{filters.actor_name}%"))
    if filters.recovery_case_id is not None:
        clauses.append(AuditLog.recovery_case_id == filters.recovery_case_id)
    if filters.correlation_id is not None:
        clauses.append(or_(*_correlation_clauses(filters.correlation_id)))
    if filters.request_id is not None:
        clauses.append(or_(*_request_id_clauses(filters.request_id)))
    if filters.date_from is not None:
        clauses.append(AuditLog.created_at >= filters.date_from)
    if filters.date_to is not None:
        clauses.append(AuditLog.created_at <= filters.date_to)
    return clauses


def get_audit_events(
    db: Session,
    filters: AuditEventFilters,
    *,
    offset: int,
    limit: int,
) -> AuditEventPage:
    """Return one page of audit_logs, newest first.

    Args:
        db: Request-scoped SQLAlchemy session.
        filters: Already-validated explorer filters.
        offset: SQL offset.
        limit: Page length.

    Returns:
        Mapped events plus the total matching count.
    """
    clauses = _explorer_clauses(filters)
    count_stmt = select(func.count()).select_from(AuditLog)
    list_stmt = select(AuditLog)
    if clauses:
        count_stmt = count_stmt.where(*clauses)
        list_stmt = list_stmt.where(*clauses)
    total = int(db.scalar(count_stmt) or 0)
    rows = db.scalars(
        list_stmt.order_by(AuditLog.created_at.desc()).offset(offset).limit(limit)
    ).all()
    logger.info(
        "audit.events",
        extra={"offset": offset, "limit": limit, "total": total},
    )
    return AuditEventPage(items=[_record_from_log(row) for row in rows], total=total)


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


def _require_case(db: Session, recovery_case_id: UUID) -> RecoveryCase:
    """Load a recovery case or raise ``AuditCaseNotFoundError``."""
    case = db.scalar(
        select(RecoveryCase)
        .options(
            selectinload(RecoveryCase.payment),
            selectinload(RecoveryCase.actions),
            selectinload(RecoveryCase.audit_logs),
        )
        .where(RecoveryCase.id == recovery_case_id)
    )
    if case is None:
        logger.info(
            "audit.case.not_found",
            extra={"recovery_case_id": str(recovery_case_id)},
        )
        raise AuditCaseNotFoundError(recovery_case_id)
    return case


def get_case_audit_timeline(db: Session, recovery_case_id: UUID) -> CaseAuditTimeline:
    """Build a chronological compliance timeline for one case.

    Prefers ``audit_logs`` rows, then fills gaps from the payment, actions,
    webhooks, and terminal case status. Timestamps are sorted ascending.

    Args:
        db: Request-scoped SQLAlchemy session.
        recovery_case_id: Case whose journey is replayed.

    Returns:
        Mapped events plus current recovery_status.

    Raises:
        AuditCaseNotFoundError: When the case does not exist.
    """
    case = _require_case(db, recovery_case_id)
    payment = case.payment
    logs = sorted(case.audit_logs, key=lambda row: row.created_at)
    present_types = {str(row.event_type) for row in logs}
    events = [_record_from_log(row) for row in logs]

    if AuditEventType.CASE_OPENED not in present_types and payment is not None:
        events.append(
            _synthetic_event(
                event_type="payment_failed",
                actor="Razorpay Webhook",
                actor_type=ActorType.SYSTEM,
                timestamp=payment.created_at,
                summary=f"Payment {payment.payment_status} for {payment.amount} paise",
                recovery_case_id=recovery_case_id,
                request_id=str(payment.id),
                details={
                    "payment_status": str(payment.payment_status),
                    "failure_reason": (
                        str(payment.failure_reason) if payment.failure_reason else None
                    ),
                    "amount": payment.amount,
                },
            )
        )

    if (
        AuditEventType.DIAGNOSIS_COMPLETED not in present_types
        and (case.diagnosed_reason is not None or case.diagnosis_model is not None)
    ):
        events.append(
            _synthetic_event(
                event_type="diagnosis_created",
                actor="Diagnosis Agent",
                actor_type=ActorType.AI_AGENT,
                timestamp=case.recovery_started_at or case.created_at,
                summary=f"Diagnosed as {case.diagnosed_reason or 'UNKNOWN'}",
                recovery_case_id=recovery_case_id,
                request_id=str(case.id),
                details={
                    "diagnosed_reason": (
                        str(case.diagnosed_reason) if case.diagnosed_reason else None
                    ),
                    "model": case.diagnosis_model,
                    "version": case.diagnosis_version,
                    "confidence": case.ai_confidence,
                },
            )
        )

    if AuditEventType.ACTION_SCHEDULED not in present_types:
        for action in sorted(case.actions, key=lambda row: row.created_at):
            scheduled_at = action.scheduled_time or action.created_at
            events.append(
                _synthetic_event(
                    event_type="action_scheduled",
                    actor="Recovery Agent",
                    actor_type=ActorType.AI_AGENT,
                    timestamp=scheduled_at,
                    summary=f"{action.action_type} scheduled ({action.execution_status})",
                    recovery_case_id=recovery_case_id,
                    request_id=str(action.id),
                    event_id=action.id,
                    details={
                        "action_type": str(action.action_type),
                        "execution_status": str(action.execution_status),
                    },
                )
            )
            if action.executed_time is not None or action.execution_status in {
                ExecutionStatus.SUCCEEDED,
                ExecutionStatus.FAILED,
                ExecutionStatus.SKIPPED,
            }:
                events.append(
                    _synthetic_event(
                        event_type="action_executed",
                        actor="Recovery Agent",
                        actor_type=ActorType.AI_AGENT,
                        timestamp=action.executed_time or action.created_at,
                        summary=f"{action.action_type} {action.execution_status}",
                        recovery_case_id=recovery_case_id,
                        request_id=str(action.id),
                        event_id=action.id,
                        details={
                            "action_type": str(action.action_type),
                            "execution_status": str(action.execution_status),
                        },
                    )
                )

    if payment is not None:
        for hook in _webhook_events_for_payment(db, payment):
            events.append(
                _synthetic_event(
                    event_type="webhook_update",
                    actor="Razorpay Webhook",
                    actor_type=ActorType.SYSTEM,
                    timestamp=hook.created_at,
                    summary=f"Webhook {hook.event_type}",
                    recovery_case_id=recovery_case_id,
                    request_id=str(hook.id),
                    event_id=hook.id,
                    details={
                        "event_type": hook.event_type,
                        "signature_verified": hook.signature_verified,
                    },
                )
            )

    terminal = {
        AuditEventType.CASE_CLOSED,
        AuditEventType.PAYMENT_CAPTURED,
        AuditEventType.RECOVERY_STOPPED,
        AuditEventType.ESCALATED,
    }
    if not (present_types & {str(item) for item in terminal}):
        if case.recovery_status in {
            RecoveryStatus.RECOVERED,
            RecoveryStatus.STOPPED,
            RecoveryStatus.ESCALATED,
            RecoveryStatus.CLOSED,
        }:
            outcome_at = case.recovery_completed_at or case.updated_at
            events.append(
                _synthetic_event(
                    event_type="final_outcome",
                    actor="System",
                    actor_type=ActorType.SYSTEM,
                    timestamp=outcome_at,
                    summary=f"Recovery outcome: {case.recovery_status}",
                    recovery_case_id=recovery_case_id,
                    request_id=str(case.id),
                    details={"recovery_status": str(case.recovery_status)},
                )
            )

    events.sort(key=lambda item: (item.timestamp, item.event_type, str(item.event_id or "")))
    logger.info(
        "audit.timeline",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "event_count": len(events),
        },
    )
    return CaseAuditTimeline(
        recovery_case_id=recovery_case_id,
        recovery_status=case.recovery_status,
        events=events,
    )


def get_correlation_trace(db: Session, correlation_id: str) -> CorrelationTrace:
    """Replay every audit event for one workflow correlation id.

    Matches ``structured_payload.correlation_id`` when present. Simulator
    rows omit that key, so a UUID equal to ``recovery_case_id`` also matches.

    Args:
        db: Request-scoped SQLAlchemy session.
        correlation_id: Workflow correlation token.

    Returns:
        Events ordered by timestamp ascending.

    Raises:
        CorrelationNotFoundError: When nothing matches.
    """
    token = correlation_id.strip()
    if not token:
        raise CorrelationNotFoundError(correlation_id)
    rows = list(
        db.scalars(
            select(AuditLog)
            .where(or_(*_correlation_clauses(token)))
            .order_by(AuditLog.created_at.asc())
        ).all()
    )
    events = [_record_from_log(row) for row in rows]
    as_uuid = _try_uuid(token)
    if not events and as_uuid is not None:
        try:
            timeline = get_case_audit_timeline(db, as_uuid)
            events = timeline.events
        except AuditCaseNotFoundError as exc:
            raise CorrelationNotFoundError(token) from exc
    if not events:
        logger.info("audit.correlation.not_found", extra={"correlation_id": token})
        raise CorrelationNotFoundError(token)
    logger.info(
        "audit.correlation",
        extra={"correlation_id": token, "event_count": len(events)},
    )
    return CorrelationTrace(correlation_id=token, events=events)


def get_policy_decisions(
    db: Session, recovery_case_id: UUID
) -> list[PolicyDecisionRecord]:
    """Return every policy evaluation for a case.

    Uses ``POLICY_EVALUATED`` rows and any other audit row that stored a
    ``policy_decision``. If none exist, returns a single ALLOW placeholder.

    Args:
        db: Request-scoped SQLAlchemy session.
        recovery_case_id: Case whose gates are listed.

    Returns:
        Mapped decisions, oldest first.

    Raises:
        AuditCaseNotFoundError: When the case does not exist.
    """
    case = _require_case(db, recovery_case_id)
    rows = db.scalars(
        select(AuditLog)
        .where(AuditLog.recovery_case_id == recovery_case_id)
        .where(
            or_(
                AuditLog.event_type == AuditEventType.POLICY_EVALUATED,
                AuditLog.policy_decision.is_not(None),
            )
        )
        .order_by(AuditLog.created_at.asc())
    ).all()
    records: list[PolicyDecisionRecord] = []
    for log in rows:
        payload = _payload_dict(log.structured_payload)
        decision = _present_decision(log.policy_decision, log.event_type)
        if decision is None:
            continue
        records.append(
            PolicyDecisionRecord(
                recovery_case_id=recovery_case_id,
                event_id=log.id,
                policy_name=str(payload.get("policy_name") or PLACEHOLDER_POLICY_NAME),
                decision=decision,
                reason=str(payload.get("reason") or log.event_summary),
                evaluated_at=log.created_at,
            )
        )
    if not records:
        records.append(
            PolicyDecisionRecord(
                recovery_case_id=recovery_case_id,
                event_id=None,
                policy_name=PLACEHOLDER_POLICY_NAME,
                decision="ALLOW",
                reason=PLACEHOLDER_POLICY_REASON,
                evaluated_at=case.created_at,
            )
        )
    logger.info(
        "audit.policy",
        extra={
            "recovery_case_id": str(recovery_case_id),
            "decision_count": len(records),
        },
    )
    return records
