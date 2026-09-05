"""Payment create, read, update, and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import FailureReason, PaymentMethod, PaymentStatus


class PaymentCreate(BaseModel):
    """Payload to record a Razorpay payment attempt."""

    merchant_id: UUID
    customer_id: UUID
    subscription_id: UUID | None = None
    razorpay_order_id: str | None = Field(default=None, max_length=64)
    razorpay_payment_id: str | None = Field(default=None, max_length=64)
    idempotency_key: str | None = Field(default=None, max_length=128)
    payment_status: PaymentStatus = PaymentStatus.PENDING
    failure_reason: FailureReason | None = None
    payment_method: PaymentMethod | None = None
    amount: int = Field(..., ge=0, description="Amount in paise")
    currency: str = Field(default="INR", min_length=3, max_length=3)
    attempt_number: int = Field(default=1, ge=1)
    payment_due_date: date | None = None
    paid_at: datetime | None = None


class PaymentUpdate(BaseModel):
    """Partial payment update used when webhooks or recovery change state."""

    razorpay_order_id: str | None = Field(default=None, max_length=64)
    razorpay_payment_id: str | None = Field(default=None, max_length=64)
    idempotency_key: str | None = Field(default=None, max_length=128)
    payment_status: PaymentStatus | None = None
    failure_reason: FailureReason | None = None
    payment_method: PaymentMethod | None = None
    attempt_number: int | None = Field(default=None, ge=1)
    paid_at: datetime | None = None


class PaymentRead(BaseModel):
    """Payment row as stored in PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    customer_id: UUID
    subscription_id: UUID | None
    razorpay_order_id: str | None
    razorpay_payment_id: str | None
    idempotency_key: str | None
    payment_status: PaymentStatus
    failure_reason: FailureReason | None
    payment_method: PaymentMethod | None
    amount: int
    currency: str
    attempt_number: int
    payment_due_date: date | None
    paid_at: datetime | None
    created_at: datetime
    updated_at: datetime


class PaymentResponse(PaymentRead):
    """Public payment DTO returned to the dashboard and simulator."""
