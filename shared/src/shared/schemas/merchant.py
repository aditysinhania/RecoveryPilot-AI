"""Merchant create, read, update, and response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class MerchantCreate(BaseModel):
    """Payload to register a merchant on RecoveryPilot."""

    merchant_name: str = Field(..., min_length=1, max_length=255)
    business_category: str = Field(..., min_length=1, max_length=128)
    email: EmailStr
    phone: str = Field(..., min_length=8, max_length=32)
    razorpay_account_id: str | None = Field(default=None, max_length=64)
    timezone: str = Field(default="Asia/Kolkata", max_length=64)


class MerchantUpdate(BaseModel):
    """Partial merchant update. Omitted fields are left unchanged."""

    merchant_name: str | None = Field(default=None, min_length=1, max_length=255)
    business_category: str | None = Field(default=None, min_length=1, max_length=128)
    email: EmailStr | None = None
    phone: str | None = Field(default=None, min_length=8, max_length=32)
    razorpay_account_id: str | None = Field(default=None, max_length=64)
    timezone: str | None = Field(default=None, max_length=64)


class MerchantRead(BaseModel):
    """Merchant row as stored in PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_name: str
    business_category: str
    email: str
    phone: str
    razorpay_account_id: str | None
    timezone: str
    created_at: datetime
    updated_at: datetime


class MerchantResponse(MerchantRead):
    """Public merchant DTO returned to the dashboard."""
