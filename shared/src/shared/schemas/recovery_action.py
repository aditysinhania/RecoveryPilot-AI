"""Recovery action create, read, update, and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import ExecutionStatus, RecoveryActionType


class RecoveryActionCreate(BaseModel):
    """Payload to schedule one bounded recovery intervention."""

    recovery_case_id: UUID
    action_type: RecoveryActionType
    scheduled_time: datetime | None = None
    execution_status: ExecutionStatus = ExecutionStatus.SCHEDULED
    razorpay_payment_link: str | None = Field(default=None, max_length=512)
    retry_number: int = Field(default=0, ge=0)
    response_code: str | None = Field(default=None, max_length=64)
    response_message: str | None = Field(default=None, max_length=512)
    action_metadata: dict[str, Any] = Field(
        default_factory=dict,
        description="JSONB execution payload stored in column metadata",
    )


class RecoveryActionUpdate(BaseModel):
    """Partial action update after execution or skip."""

    scheduled_time: datetime | None = None
    executed_time: datetime | None = None
    execution_status: ExecutionStatus | None = None
    razorpay_payment_link: str | None = Field(default=None, max_length=512)
    retry_number: int | None = Field(default=None, ge=0)
    response_code: str | None = Field(default=None, max_length=64)
    response_message: str | None = Field(default=None, max_length=512)
    action_metadata: dict[str, Any] | None = None


class RecoveryActionRead(BaseModel):
    """Recovery action row as stored in PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recovery_case_id: UUID
    action_type: RecoveryActionType
    scheduled_time: datetime | None
    executed_time: datetime | None
    execution_status: ExecutionStatus
    razorpay_payment_link: str | None
    retry_number: int
    response_code: str | None
    response_message: str | None
    action_metadata: dict[str, Any]
    created_at: datetime


class RecoveryActionResponse(RecoveryActionRead):
    """Public recovery-action DTO used in audit replay."""
