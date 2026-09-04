"""Typed snapshots and policy decision models. No ORM, no I/O."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from services.diagnosis.models import DiagnosisResult
from shared.enums import (
    ConsentStatus,
    CustomerSegment,
    ExecutionStatus,
    MandateStatus,
    PaymentStatus,
    PromiseStatus,
    RecoveryActionType,
    RecoveryStatus,
    SubscriptionStatus,
)


class PolicyDecision(StrEnum):
    """Final gate returned by the policy engine. Distinct from audit-log PolicyDecision."""

    ALLOW = "ALLOW"
    WAIT = "WAIT"
    DENY = "DENY"
    STOP = "STOP"
    ESCALATE = "ESCALATE"


class RuleVerdict(StrEnum):
    """Per-rule outcome. FAIL maps to a DENY decision."""

    PASS = "PASS"
    FAIL = "FAIL"
    WAIT = "WAIT"
    STOP = "STOP"
    ESCALATE = "ESCALATE"


class CustomerPolicySnapshot(BaseModel):
    """Customer consent, segment, and hardship. No PAN/VPA/phone secrets logged."""

    id: UUID
    segment: CustomerSegment
    consent_status: ConsentStatus = ConsentStatus.GRANTED
    consent_whatsapp: bool = True
    consent_sms: bool = True
    consent_voice: bool = True
    consent_email: bool = True
    hardship: bool = False
    timezone: str = "Asia/Kolkata"


class PaymentPolicySnapshot(BaseModel):
    """Payment fields the policy engine needs."""

    id: UUID
    amount: int
    status: PaymentStatus
    created_at: datetime
    attempt_number: int = 1


class SubscriptionPolicySnapshot(BaseModel):
    """Mandate and subscription state for stopping rules."""

    id: UUID
    mandate_status: MandateStatus
    subscription_status: SubscriptionStatus


class RecoveryActionSnapshot(BaseModel):
    """Prior recovery action used for retry cooldown."""

    action_type: RecoveryActionType
    execution_status: ExecutionStatus = ExecutionStatus.SUCCEEDED
    scheduled_time: datetime | None = None
    executed_time: datetime | None = None
    created_at: datetime
    retry_number: int = 0
    channel: str | None = None

    def event_time(self) -> datetime:
        """Best timestamp for cooldown math."""
        return self.executed_time or self.scheduled_time or self.created_at


class PromisePolicySnapshot(BaseModel):
    """Promise-to-pay row used as a waiting / stopping rule."""

    status: PromiseStatus
    promised_date: date
    promised_amount: int = 0


class CommunicationSnapshot(BaseModel):
    """One outbound recovery message. Optional; Postgres has no comms table."""

    channel: str
    sent_at: datetime


class PolicyContext(BaseModel):
    """All inputs the engine needs. Built by the service layer or tests."""

    as_of: datetime
    diagnosis: DiagnosisResult
    customer: CustomerPolicySnapshot
    payment: PaymentPolicySnapshot
    subscription: SubscriptionPolicySnapshot | None = None
    recovery_actions: list[RecoveryActionSnapshot] = Field(default_factory=list)
    promises: list[PromisePolicySnapshot] = Field(default_factory=list)
    communications: list[CommunicationSnapshot] = Field(default_factory=list)
    recovery_case_id: UUID | None = None
    recovery_status: RecoveryStatus | None = None


class PolicyRuleResult(BaseModel):
    """Outcome of one independent policy rule."""

    policy_name: str
    verdict: RuleVerdict
    reason: str
    evidence_codes: list[str] = Field(default_factory=list)
    cooldown_until: datetime | None = None
    allowed_channels: list[str] | None = None
    blocked_channels: list[str] | None = None
    manual_review_required: bool = False
    priority_boost: float = 0.0
    silent_retry_allowed: bool = False


class EvaluatedRule(BaseModel):
    """One row in the evaluation trace attached to every decision."""

    policy_name: str
    result: RuleVerdict
    reason: str


class PolicyDecisionResult(BaseModel):
    """Structured compliance gate. Informational only — never executed."""

    policy_name: str
    decision: PolicyDecision
    reason: str
    evidence_codes: list[str] = Field(default_factory=list)
    priority_score: float = Field(ge=0.0, le=100.0)
    decision_priority: int = 0
    evaluated_at: datetime
    cooldown_until: datetime | None = None
    allowed_channels: list[str] = Field(default_factory=list)
    blocked_channels: list[str] = Field(default_factory=list)
    manual_review_required: bool = False
    policy_version: str
    triggered_policies: list[str] = Field(default_factory=list)
    failed_policies: list[str] = Field(default_factory=list)
    evaluated_rules: list[EvaluatedRule] = Field(default_factory=list)
    silent_retry_allowed: bool = False
    recovery_case_id: UUID | None = None
    payment_id: UUID | None = None
    diagnosis: str | None = None
    features: dict[str, Any] = Field(default_factory=dict)


class BatchPolicySummary(BaseModel):
    """Aggregate of many PolicyDecisionResult rows for dashboard analytics."""

    total_cases: int
    decision_distribution: dict[str, int]
    stopped_cases: int
    escalated_cases: int
    waiting_cases: int
    allowed_cases: int
    denied_cases: int
    blocked_channel_counts: dict[str, int]


class BatchPolicyResult(BaseModel):
    """Per-case decisions plus a rollup summary."""

    results: list[PolicyDecisionResult]
    missing_case_ids: list[UUID] = Field(default_factory=list)
    summary: BatchPolicySummary
