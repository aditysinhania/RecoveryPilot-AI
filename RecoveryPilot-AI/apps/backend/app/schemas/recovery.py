"""HTTP DTOs for the merchant recovery queue. ORM is not returned from routers."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import (
    CustomerSegment,
    FailureReason,
    PaymentMethod,
    PromiseStatus,
    RecoveryStatus,
)
from shared.schemas.customer import CustomerRead
from shared.schemas.payment import PaymentRead
from shared.schemas.promise_to_pay import PromiseToPayRead
from shared.schemas.recovery_action import RecoveryActionRead
from shared.schemas.subscription import SubscriptionRead


class TimelineEventType(StrEnum):
    """Kinds of events on a recovery journey timeline."""

    PAYMENT_FAILED = "payment_failed"
    DIAGNOSIS_CREATED = "diagnosis_created"
    ACTION_SCHEDULED = "action_scheduled"
    ACTION_EXECUTED = "action_executed"
    WEBHOOK_UPDATE = "webhook_update"
    AUDIT = "audit"


class RecoveryQueueItem(BaseModel):
    """One row on Payments Requiring Attention."""

    model_config = ConfigDict(from_attributes=True)

    recovery_case_id: UUID
    merchant_id: UUID
    customer_id: UUID
    payment_id: UUID
    customer_name: str
    customer_segment: CustomerSegment
    amount: int = Field(description="Amount in paise")
    currency: str
    payment_method: PaymentMethod | None = None
    failure_reason: FailureReason | None = None
    diagnosed_reason: FailureReason | None = None
    recovery_status: RecoveryStatus
    priority_score: float | None = None
    ai_confidence: float | None = None
    payment_due_date: date | None = None
    failed_at: datetime
    recovery_started_at: datetime | None = None


class RecoveryCaseResponse(BaseModel):
    """Full recovery case for the case-detail drawer."""

    recovery_case_id: UUID
    merchant_id: UUID
    recovery_status: RecoveryStatus
    diagnosed_reason: FailureReason | None = None
    diagnosis_model: str | None = None
    diagnosis_version: str | None = None
    ai_confidence: float | None = None
    priority_score: float | None = None
    recovery_started_at: datetime | None = None
    recovery_completed_at: datetime | None = None
    created_at: datetime
    updated_at: datetime
    customer: CustomerRead
    payment: PaymentRead
    subscription: SubscriptionRead | None = None
    latest_action: RecoveryActionRead | None = None
    promise_to_pay: PromiseToPayRead | None = None
    promise_status: PromiseStatus | None = None


class RecoveryTimelineEvent(BaseModel):
    """One chronological step in a recovery journey."""

    event_type: TimelineEventType
    occurred_at: datetime
    summary: str
    source: str
    reference_id: UUID | None = None
    details: dict[str, Any] = Field(default_factory=dict)


class RecoverySummaryResponse(BaseModel):
    """Aggregate recovery-queue KPIs. Amounts are paise."""

    open_cases: int = 0
    recovered_cases: int = 0
    stopped_cases: int = 0
    escalated_cases: int = 0
    waiting_retry: int = 0
    waiting_promise: int = 0
    total_revenue_at_risk: int = 0
    recovered_revenue: int = 0
    recovery_rate: float = 0.0


__all__ = [
    "RecoveryCaseResponse",
    "RecoveryQueueItem",
    "RecoverySummaryResponse",
    "RecoveryTimelineEvent",
    "TimelineEventType",
]
