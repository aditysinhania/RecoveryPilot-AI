"""In-memory execution and webhook log. No Postgres writes."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid4

from services.executor.constants import ACTOR
from services.executor.models import ExecutionAuditEvent, ExecutionResult


class ExecutionLogStore:
    """Process-local ledger used for idempotency and webhook replay.

    Does not INSERT into ``audit_logs`` or ``webhook_events`` (schema unchanged).
    """

    def __init__(self) -> None:
        self._executions: dict[str, ExecutionResult] = {}
        self._webhooks: set[str] = set()
        self._audits: list[ExecutionAuditEvent] = []

    def get(self, idempotency_key: str) -> ExecutionResult | None:
        """Return a prior result for this key, if any."""
        return self._executions.get(idempotency_key)

    def put(self, result: ExecutionResult) -> None:
        """Record an execution. Overwrites are ignored when the key exists."""
        if result.idempotency_key not in self._executions:
            self._executions[result.idempotency_key] = result
            if result.audit is not None:
                self._audits.append(result.audit)

    def seen_webhook(self, event_id: str) -> bool:
        """True when this Razorpay-shaped event id was already processed."""
        return event_id in self._webhooks

    def remember_webhook(self, event_id: str) -> None:
        """Mark a webhook event id as processed."""
        self._webhooks.add(event_id)

    def record_audit(self, event: ExecutionAuditEvent) -> None:
        """Append an audit event without creating a new execution row."""
        self._audits.append(event)

    def audits(self) -> list[ExecutionAuditEvent]:
        """Copy of in-memory audit events."""
        return list(self._audits)


def build_audit(
    *,
    action: str,
    outcome: str,
    request_id: str,
    correlation_id: str,
    idempotency_key: str,
    timestamp: datetime,
    audit_event_id: UUID | None = None,
) -> ExecutionAuditEvent:
    """Create one executor audit event. Actor is always EXECUTOR_ENGINE."""
    return ExecutionAuditEvent(
        audit_event_id=audit_event_id or uuid4(),
        actor=ACTOR,
        action=action,
        outcome=outcome,
        request_id=request_id,
        correlation_id=correlation_id,
        idempotency_key=idempotency_key,
        timestamp=timestamp,
    )
