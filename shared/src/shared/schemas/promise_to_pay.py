"""Promise-to-pay create, read, update, and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import PromiseStatus


class PromiseToPayCreate(BaseModel):
    """Payload to record a customer payment commitment."""

    recovery_case_id: UUID
    promised_amount: int = Field(..., ge=0, description="Amount in paise")
    promised_date: date
    promise_status: PromiseStatus = PromiseStatus.OPEN


class PromiseToPayUpdate(BaseModel):
    """Partial promise update when fulfilled, broken, or cancelled."""

    promised_amount: int | None = Field(default=None, ge=0)
    promised_date: date | None = None
    promise_status: PromiseStatus | None = None
    fulfilled_at: datetime | None = None


class PromiseToPayRead(BaseModel):
    """Promise-to-pay row as stored in PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    recovery_case_id: UUID
    promised_amount: int
    promised_date: date
    promise_status: PromiseStatus
    fulfilled_at: datetime | None
    created_at: datetime


class PromiseToPayResponse(PromiseToPayRead):
    """Public promise DTO returned to the dashboard."""
