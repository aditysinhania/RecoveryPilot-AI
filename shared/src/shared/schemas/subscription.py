"""Subscription create, read, update, and response schemas."""

from __future__ import annotations

from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import BillingFrequency, MandateStatus, SubscriptionStatus


class SubscriptionCreate(BaseModel):
    """Payload to start a recurring billing relationship."""

    customer_id: UUID
    merchant_id: UUID
    subscription_name: str = Field(..., min_length=1, max_length=255)
    billing_amount: int = Field(..., ge=0, description="Amount in paise")
    billing_frequency: BillingFrequency
    next_billing_date: date
    mandate_status: MandateStatus = MandateStatus.PENDING
    subscription_status: SubscriptionStatus = SubscriptionStatus.ACTIVE


class SubscriptionUpdate(BaseModel):
    """Partial subscription update. Omitted fields are left unchanged."""

    subscription_name: str | None = Field(default=None, min_length=1, max_length=255)
    billing_amount: int | None = Field(default=None, ge=0)
    billing_frequency: BillingFrequency | None = None
    next_billing_date: date | None = None
    mandate_status: MandateStatus | None = None
    subscription_status: SubscriptionStatus | None = None


class SubscriptionRead(BaseModel):
    """Subscription row as stored in PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    customer_id: UUID
    merchant_id: UUID
    subscription_name: str
    billing_amount: int
    billing_frequency: BillingFrequency
    next_billing_date: date
    mandate_status: MandateStatus
    subscription_status: SubscriptionStatus
    created_at: datetime
    updated_at: datetime


class SubscriptionResponse(SubscriptionRead):
    """Public subscription DTO returned to the dashboard."""
