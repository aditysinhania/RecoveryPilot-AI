"""Recovery case create, read, update, and response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import FailureReason, RecoveryStatus


class RecoveryCaseCreate(BaseModel):
    """Payload to open a recovery journey for one payment."""

    payment_id: UUID
    customer_id: UUID
    merchant_id: UUID
    recovery_status: RecoveryStatus = RecoveryStatus.OPEN
    diagnosed_reason: FailureReason | None = None
    diagnosis_model: str | None = Field(default=None, max_length=128)
    diagnosis_version: str | None = Field(default=None, max_length=64)
    ai_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    priority_score: float | None = Field(default=None, ge=0.0)
    recovery_started_at: datetime | None = None


class RecoveryCaseUpdate(BaseModel):
    """Partial recovery-case update after diagnosis, wait, or close."""

    recovery_status: RecoveryStatus | None = None
    diagnosed_reason: FailureReason | None = None
    diagnosis_model: str | None = Field(default=None, max_length=128)
    diagnosis_version: str | None = Field(default=None, max_length=64)
    ai_confidence: float | None = Field(default=None, ge=0.0, le=1.0)
    priority_score: float | None = Field(default=None, ge=0.0)
    recovery_started_at: datetime | None = None
    recovery_completed_at: datetime | None = None


class RecoveryCaseRead(BaseModel):
    """Recovery case row as stored in PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    payment_id: UUID
    customer_id: UUID
    merchant_id: UUID
    recovery_status: RecoveryStatus
    diagnosed_reason: FailureReason | None
    diagnosis_model: str | None
    diagnosis_version: str | None
    ai_confidence: float | None
    priority_score: float | None
    recovery_started_at: datetime | None
    recovery_completed_at: datetime | None
    created_at: datetime
    updated_at: datetime


class RecoveryCaseResponse(RecoveryCaseRead):
    """Public recovery-case DTO returned to the dashboard."""
