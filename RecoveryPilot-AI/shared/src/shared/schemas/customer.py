"""Customer create, read, update, and response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from shared.enums import ConsentStatus, CustomerSegment, PaymentMethod


class CustomerCreate(BaseModel):
    """Payload to add a customer under a merchant."""

    merchant_id: UUID
    full_name: str = Field(..., min_length=1, max_length=255)
    email: EmailStr
    phone: str = Field(..., min_length=8, max_length=32)
    customer_segment: CustomerSegment = CustomerSegment.NEW
    preferred_payment_method: PaymentMethod | None = None
    preferred_language: str = Field(default="en", max_length=16)
    consent_status: ConsentStatus = ConsentStatus.PENDING


class CustomerUpdate(BaseModel):
    """Partial customer update. Omitted fields are left unchanged."""

    full_name: str | None = Field(default=None, min_length=1, max_length=255)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=8, max_length=32)
    customer_segment: CustomerSegment | None = None
    preferred_payment_method: PaymentMethod | None = None
    preferred_language: str | None = Field(default=None, max_length=16)
    consent_status: ConsentStatus | None = None


class CustomerRead(BaseModel):
    """Customer row as stored in PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    full_name: str
    email: str
    phone: str
    customer_segment: CustomerSegment
    preferred_payment_method: PaymentMethod | None
    preferred_language: str
    consent_status: ConsentStatus
    created_at: datetime
    updated_at: datetime


class CustomerResponse(CustomerRead):
    """Public customer DTO returned to the dashboard."""
