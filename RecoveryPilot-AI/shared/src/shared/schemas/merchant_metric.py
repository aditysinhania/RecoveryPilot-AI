"""Merchant metrics create, read, update, and response schemas."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class MerchantMetricCreate(BaseModel):
    """Payload to insert a precomputed dashboard snapshot for one merchant."""

    merchant_id: UUID
    revenue_at_risk: int = Field(default=0, ge=0, description="Paise")
    recovered_revenue: int = Field(default=0, ge=0, description="Paise")
    suppressed_revenue: int = Field(default=0, ge=0, description="Paise")
    recovery_rate: float = Field(default=0.0, ge=0.0, le=1.0)
    escalation_count: int = Field(default=0, ge=0)
    policy_stop_count: int = Field(default=0, ge=0)


class MerchantMetricUpdate(BaseModel):
    """Partial metrics refresh after a batch recovery run."""

    revenue_at_risk: int | None = Field(default=None, ge=0)
    recovered_revenue: int | None = Field(default=None, ge=0)
    suppressed_revenue: int | None = Field(default=None, ge=0)
    recovery_rate: float | None = Field(default=None, ge=0.0, le=1.0)
    escalation_count: int | None = Field(default=None, ge=0)
    policy_stop_count: int | None = Field(default=None, ge=0)


class MerchantMetricRead(BaseModel):
    """Merchant metrics row as stored in PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    merchant_id: UUID
    revenue_at_risk: int
    recovered_revenue: int
    suppressed_revenue: int
    recovery_rate: float
    escalation_count: int
    policy_stop_count: int
    updated_at: datetime


class MerchantMetricResponse(MerchantMetricRead):
    """Public metrics DTO for the merchant dashboard."""
