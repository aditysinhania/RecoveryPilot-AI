"""HTTP DTOs for compliance replay. ORM and raw JSONB are not returned."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from shared.enums import ActorType, RecoveryStatus


class AuditEventResponse(BaseModel):
    """One human-readable audit step on a recovery journey."""

    event_id: UUID | None = None
    recovery_case_id: UUID | None = None
    event_type: str
    actor: str
    actor_type: ActorType | None = None
    timestamp: datetime
    summary: str
    request_id: str
    correlation_id: str
    policy_decision: str | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class AuditTimelineResponse(BaseModel):
    """Chronological compliance timeline for one recovery case."""

    recovery_case_id: UUID
    recovery_status: RecoveryStatus | None = None
    event_count: int = 0
    events: list[AuditEventResponse] = Field(default_factory=list)


class CorrelationTraceResponse(BaseModel):
    """Every audit event sharing one correlation id, oldest first."""

    correlation_id: str
    event_count: int = 0
    events: list[AuditEventResponse] = Field(default_factory=list)


class PolicyDecisionResponse(BaseModel):
    """One policy-gate evaluation, mapped for reviewers."""

    recovery_case_id: UUID
    event_id: UUID | None = None
    policy_name: str
    decision: str = Field(description="ALLOW | DENY | ESCALATE | STOP")
    reason: str
    evaluated_at: datetime


__all__ = [
    "AuditEventResponse",
    "AuditTimelineResponse",
    "CorrelationTraceResponse",
    "PolicyDecisionResponse",
]
