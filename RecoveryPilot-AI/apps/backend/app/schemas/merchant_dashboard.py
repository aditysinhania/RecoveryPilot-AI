"""Dashboard-facing merchant DTOs. ORM models are not returned from routers."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from shared.enums import RecoveryStatus
from shared.schemas.merchant import MerchantRead
from shared.schemas.merchant_metric import MerchantMetricRead
from shared.schemas.payment import PaymentRead


class MerchantMetricsPayload(BaseModel):
    """Metrics snapshot. Zeros when no ``merchant_metrics`` row exists yet."""

    model_config = ConfigDict(from_attributes=True)

    merchant_id: UUID
    revenue_at_risk: int = 0
    recovered_revenue: int = 0
    suppressed_revenue: int = 0
    recovery_rate: float = 0.0
    escalation_count: int = 0
    policy_stop_count: int = 0
    updated_at: datetime | None = None


class MerchantSummary(BaseModel):
    """Merchant profile plus live ledger counts for the dashboard header."""

    merchant: MerchantRead
    customers: int = Field(ge=0)
    subscriptions: int = Field(ge=0)
    payments: int = Field(ge=0)
    failed_payments: int = Field(ge=0)
    recovery_cases: int = Field(ge=0)
    metrics: MerchantMetricsPayload


class PaymentListItem(PaymentRead):
    """Payment row on the merchant ledger."""


class FailureListItem(PaymentRead):
    """Failed payment row on the merchant failure queue."""

    recovery_status: RecoveryStatus | None = None


__all__ = [
    "FailureListItem",
    "MerchantMetricRead",
    "MerchantMetricsPayload",
    "MerchantSummary",
    "PaymentListItem",
]
