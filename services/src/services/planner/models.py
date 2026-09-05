"""Typed planner snapshots and RecoveryPlan models. No ORM, no I/O."""

from __future__ import annotations

from datetime import date, datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from services.diagnosis.models import DiagnosisResult
from services.policy.models import PolicyDecisionResult
from shared.enums import CustomerSegment, PaymentMethod


class PlannerStrategy(StrEnum):
    """Primary recovery strategy. The planner picks exactly one."""

    WAIT_FOR_PAYDAY = "WAIT_FOR_PAYDAY"
    RETRY_PAYMENT = "RETRY_PAYMENT"
    RETRY_SILENTLY = "RETRY_SILENTLY"
    SEND_PAYMENT_LINK = "SEND_PAYMENT_LINK"
    SWITCH_PAYMENT_METHOD = "SWITCH_PAYMENT_METHOD"
    REQUEST_NEW_MANDATE = "REQUEST_NEW_MANDATE"
    HONOUR_PROMISE_TO_PAY = "HONOUR_PROMISE_TO_PAY"
    ESCALATE_TO_HUMAN = "ESCALATE_TO_HUMAN"
    STOP_RECOVERY = "STOP_RECOVERY"


class MerchantPlannerSnapshot(BaseModel):
    """Merchant profile used for timezone and industry context."""

    name: str = "FitLife Gym"
    business_category: str = "Fitness & Wellness"
    timezone: str = "Asia/Kolkata"


class PlannerCustomerSnapshot(BaseModel):
    """Customer fields the planner needs. No PAN/VPA."""

    id: UUID
    segment: CustomerSegment
    salary_dependent: bool = False
    timezone: str = "Asia/Kolkata"


class CustomerBehaviourSnapshot(BaseModel):
    """Observed 90-day behaviour. Optional JSON overlay, else diagnosis features."""

    previous_success_rate: float = 0.5
    observed_reliability: float = 0.5
    max_fail_streak: int = 0
    salary_dependent: bool = False
    pays_within_hours_of_salary: int = 24


class RetryWindow(BaseModel):
    """Inclusive start / exclusive-end style window for a planned retry."""

    start: datetime
    end: datetime
    label: str


class StrategyChoice(BaseModel):
    """Primary strategy plus fallback and selection notes."""

    strategy: PlannerStrategy
    fallback: PlannerStrategy
    steps: list[str] = Field(default_factory=list)


class ScheduleResult(BaseModel):
    """Timing engine output for one plan."""

    scheduled_at: datetime
    retry_window: RetryWindow | None = None
    expires_at: datetime | None = None
    timing_reason: str


class ChannelPlan(BaseModel):
    """Ranked channels that survive the policy allow-list."""

    recommended: list[str] = Field(default_factory=list)
    cost_paise: int = 0
    channel_reason: str = ""


class PlannerContext(BaseModel):
    """All inputs the planner needs. Built by the service layer or tests."""

    as_of: datetime
    diagnosis: DiagnosisResult
    policy: PolicyDecisionResult
    customer: PlannerCustomerSnapshot
    payment_amount: int
    payment_method: PaymentMethod | None = None
    behaviour: CustomerBehaviourSnapshot = Field(default_factory=CustomerBehaviourSnapshot)
    merchant: MerchantPlannerSnapshot = Field(default_factory=MerchantPlannerSnapshot)
    promised_date: date | None = None
    outage_ended_at: datetime | None = None
    retry_count: int = 0
    subscription_age_days: int = 0
    recovery_case_id: UUID | None = None
    timezone: str = "Asia/Kolkata"


class RecoveryPlan(BaseModel):
    """Structured recovery plan. Informational only — never executed."""

    strategy: PlannerStrategy
    scheduled_at: datetime
    reasoning: str
    recommended_channels: list[str] = Field(default_factory=list)
    fallback_strategy: PlannerStrategy
    expected_outcome: str
    expected_recovery_probability: float = Field(ge=0.0, le=1.0)
    strategy_confidence: float = Field(default=0.0, ge=0.0, le=1.0)
    confidence_reasoning: str = ""
    estimated_recovery_value: int = 0
    estimated_cost: int = 0
    plan_version: str
    planner_version: str
    generated_at: datetime
    retry_window: RetryWindow | None = None
    expires_at: datetime | None = None
    reasoning_steps: list[str] = Field(default_factory=list)
    evidence_codes_used: list[str] = Field(default_factory=list)
    policy_rules_used: list[str] = Field(default_factory=list)
    timing_reason: str = ""
    channel_reason: str = ""
    recovery_case_id: UUID | None = None
    payment_id: UUID | None = None
    features: dict[str, Any] = Field(default_factory=dict)


class PlannerPair(BaseModel):
    """One diagnosis + policy pair for batch planning."""

    diagnosis: DiagnosisResult
    policy: PolicyDecisionResult


class BatchPlannerSummary(BaseModel):
    """Aggregate of many RecoveryPlan rows for dashboard analytics."""

    total_cases: int
    strategy_distribution: dict[str, int]
    scheduled_retries: int
    channel_usage: dict[str, int]
    estimated_recovery_value: int
    estimated_communication_cost: int
    expected_recovered_revenue: int


class BatchPlannerResult(BaseModel):
    """Per-case plans plus a rollup summary."""

    results: list[RecoveryPlan]
    missing_case_ids: list[UUID] = Field(default_factory=list)
    summary: BatchPlannerSummary
