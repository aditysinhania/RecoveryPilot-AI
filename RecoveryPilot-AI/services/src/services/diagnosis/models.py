"""Typed snapshots and diagnosis result models. No ORM, no I/O."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from shared.enums import (
    BillingFrequency,
    CustomerSegment,
    FailureReason,
    MandateStatus,
    PaymentMethod,
    PaymentStatus,
    PromiseStatus,
    RecoveryStatus,
    SubscriptionStatus,
)


class DiagnosisCategory(StrEnum):
    """Primary diagnosis labels returned by the rules engine."""

    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    BANK_TIMEOUT = "BANK_TIMEOUT"
    UPI_TIMEOUT = "UPI_TIMEOUT"
    CARD_EXPIRED = "CARD_EXPIRED"
    AUTHENTICATION_FAILED = "AUTHENTICATION_FAILED"
    MANDATE_REVOKED = "MANDATE_REVOKED"
    CUSTOMER_CANCELLED = "CUSTOMER_CANCELLED"
    DUPLICATE_PAYMENT = "DUPLICATE_PAYMENT"
    CHARGEBACK_ACTIVE = "CHARGEBACK_ACTIVE"
    ALREADY_PAID = "ALREADY_PAID"
    UNKNOWN = "UNKNOWN"


class PriorityBucket(StrEnum):
    """Queue band derived from the 0–100 priority score."""

    HIGH = "HIGH"
    MEDIUM = "MEDIUM"
    LOW = "LOW"


class PaymentSnapshot(BaseModel):
    """Payment fields the engine needs. No PAN/VPA."""

    id: UUID
    amount: int
    currency: str = "INR"
    status: PaymentStatus
    method: PaymentMethod | None = None
    failure_reason: FailureReason | None = None
    attempt_number: int = 1
    created_at: datetime
    paid_at: datetime | None = None
    due_date: date | None = None
    idempotency_key: str | None = None
    subscription_id: UUID | None = None
    customer_id: UUID | None = None


class CustomerSnapshot(BaseModel):
    """Customer profile used for segment and salary-cycle features."""

    id: UUID
    segment: CustomerSegment
    salary_dependent: bool = False


class SubscriptionSnapshot(BaseModel):
    """Subscription / mandate state for the failed invoice."""

    id: UUID
    name: str
    billing_amount: int
    mandate_status: MandateStatus
    subscription_status: SubscriptionStatus
    frequency: BillingFrequency = BillingFrequency.MONTHLY


class OutageWindow(BaseModel):
    """Rail incident used to detect BANK_TIMEOUT / UPI_TIMEOUT."""

    rail: str
    failure_reason: str
    started_at: datetime
    ended_at: datetime
    institution: str = ""
    summary: str = ""

    def contains(self, moment: datetime) -> bool:
        """Return True if ``moment`` falls inside ``[started_at, ended_at)``."""
        return self.started_at <= moment < self.ended_at


class PromiseSnapshot(BaseModel):
    """Promise-to-pay row used as a recovery-history feature."""

    status: PromiseStatus
    promised_date: date


class DiagnosisContext(BaseModel):
    """All inputs the engine needs. Built by the service layer or tests."""

    as_of: datetime
    timezone: str = "Asia/Kolkata"
    payment: PaymentSnapshot
    customer: CustomerSnapshot
    subscription: SubscriptionSnapshot | None = None
    customer_payments: list[PaymentSnapshot] = Field(default_factory=list)
    outages: list[OutageWindow] = Field(default_factory=list)
    promises: list[PromiseSnapshot] = Field(default_factory=list)
    recovery_action_count: int = 0
    recovery_status: RecoveryStatus | None = None


class DiagnosisFeatures(BaseModel):
    """Typed feature vector extracted from a diagnosis context."""

    days_since_failure: int
    days_until_payday: int
    days_overdue: int
    retry_count: int
    payment_method: PaymentMethod | None
    customer_segment: CustomerSegment
    mandate_status: MandateStatus | None
    subscription_plan: str | None
    subscription_tier: str
    payment_amount: int
    outage_detected: bool
    outage_rail: str | None
    outage_summary: str | None
    previous_success_rate: float
    previous_success_count: int
    previous_attempt_count: int
    promise_pending: bool
    weekend_payment: bool
    festival_period: bool
    festival_name: str | None
    salary_dependent: bool
    calendar_day: int
    pre_payday_window: bool
    payday_window: bool
    recorded_failure_reason: FailureReason | None
    already_paid_after_failure: bool
    duplicate_captured: bool
    dispute_signal: bool
    mandate_revoked: bool
    subscription_cancelled: bool
    card_method: bool
    upi_method: bool


class EvidenceItem(BaseModel):
    """One structured evidence row used for explainability and scoring.

    ``code`` is a stable identifier (not a diagnosis category). ``weight`` is
    the raw evidence weight in ``[0, 1]``. ``message`` is the human-readable
    sentence also copied onto ``DiagnosisResult.evidence``.
    """

    code: str
    weight: float = Field(ge=0.0, le=1.0)
    message: str


class RuleHit(BaseModel):
    """One independent rule that fired."""

    rule_id: str
    diagnosis: DiagnosisCategory
    weight: float = Field(ge=0.0, le=1.0)
    evidence: str
    evidence_items: list[EvidenceItem] = Field(default_factory=list)


class ConfidenceContributor(BaseModel):
    """One weighted term in the confidence score.

    ``weight`` is the term used in the raw sum (same as today). When the term
    came from structured evidence, ``code`` / ``message`` / ``evidence_weight``
    mirror the ``EvidenceItem``. ``applied_weight`` is the amount actually
    added to the pre-clamp confidence sum.
    """

    label: str
    weight: float
    code: str = ""
    message: str = ""
    evidence_weight: float | None = None
    applied_weight: float | None = None


class DiagnosisResult(BaseModel):
    """Structured diagnosis. Informational only — never executed."""

    diagnosis: DiagnosisCategory
    confidence: float = Field(ge=0.0, le=1.0)
    priority_score: float = Field(ge=0.0, le=100.0)
    priority_bucket: PriorityBucket
    evidence: list[str] = Field(default_factory=list)
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    triggered_rules: list[str] = Field(default_factory=list)
    confidence_contributors: list[ConfidenceContributor] = Field(default_factory=list)
    recommended_action_placeholder: str
    diagnosis_model: str
    diagnosis_version: str
    generated_at: datetime
    recovery_case_id: UUID | None = None
    payment_id: UUID | None = None
    features: dict[str, Any] = Field(default_factory=dict)


class BatchDiagnosisSummary(BaseModel):
    """Aggregate of many DiagnosisResult rows for dashboard analytics."""

    total_cases: int
    diagnosed_cases: int
    diagnosis_distribution: dict[str, int]
    average_confidence: float
    priority_distribution: dict[str, int]
    top_failure_reasons: list[dict[str, Any]]
    unknown_diagnoses: int


class BatchDiagnosisResult(BaseModel):
    """Per-case results plus a rollup summary."""

    results: list[DiagnosisResult]
    missing_case_ids: list[UUID] = Field(default_factory=list)
    summary: BatchDiagnosisSummary
