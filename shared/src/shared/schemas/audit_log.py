"""Audit log create, read, update, and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import ActorType, AuditEventType, PolicyDecision


class AuditLogCreate(BaseModel):
    """Payload to append one replayable compliance event."""

    recovery_case_id: UUID | None = None
    actor_type: ActorType
    actor_name: str = Field(..., min_length=1, max_length=128)
    event_type: AuditEventType
    event_summary: str = Field(..., min_length=1, max_length=1024)
    structured_payload: dict[str, Any] = Field(default_factory=dict)
    policy_decision: PolicyDecision | None = None


class AuditLogUpdate(BaseModel):
    """Audit rows are append-only. This schema exists for completeness only."""

    event_summary: str | None = Field(default=None, min_length=1, max_length=1024)
    structured_payload: dict[str, Any] | None = None


class AuditLogRead(BaseModel):
    """Audit log row as stored in PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recovery_case_id: UUID | None
    actor_type: ActorType
    actor_name: str
    event_type: AuditEventType
    event_summary: str
    structured_payload: dict[str, Any]
    policy_decision: PolicyDecision | None
    created_at: datetime


class AuditLogResponse(AuditLogRead):
    """Public audit DTO used for replay and compliance export."""
