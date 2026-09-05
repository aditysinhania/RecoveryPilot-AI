"""Typed executor snapshots and ExecutionResult models. No ORM writes."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field, SkipValidation

from services.planner.models import RecoveryPlan
from shared.enums import CustomerSegment, PaymentMethod


class ExecutionType(StrEnum):
    """One simulated action per RecoveryPlan."""

    EXECUTE_RETRY = "EXECUTE_RETRY"
    GENERATE_PAYMENT_LINK = "GENERATE_PAYMENT_LINK"
    REQUEST_CARD_UPDATE = "REQUEST_CARD_UPDATE"
    SWITCH_TO_UPI = "SWITCH_TO_UPI"
    WAIT_UNTIL_TIME = "WAIT_UNTIL_TIME"
    ESCALATE_CASE = "ESCALATE_CASE"
    STOP_EXECUTION = "STOP_EXECUTION"


class ExecutionStatus(StrEnum):
    """Lifecycle of one simulated execution."""

    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SCHEDULED = "SCHEDULED"
    GENERATED = "GENERATED"
    DUPLICATE_SKIPPED = "DUPLICATE_SKIPPED"
    EXPIRED = "EXPIRED"
    WEBHOOK_REPLAY = "WEBHOOK_REPLAY"
    TIMEOUT = "TIMEOUT"
    UNKNOWN_STRATEGY = "UNKNOWN_STRATEGY"


class RetryOutcome(StrEnum):
    """Deterministic simulated charge result."""

    SUCCESS = "SUCCESS"
    FAILED = "FAILED"
    BANK_TIMEOUT = "BANK_TIMEOUT"
    NSF = "NSF"
    AUTH_FAILURE = "AUTH_FAILURE"


class SimulatedWebhookEvent(BaseModel):
    """Normalized Razorpay-shaped webhook. Not a DB row."""

    event_id: str
    event_type: str
    payload: dict[str, Any] = Field(default_factory=dict)
    replay: bool = False
    created_at: datetime


class ExecutionAuditEvent(BaseModel):
    """In-memory audit record. Not inserted into audit_logs."""

    audit_event_id: UUID
    actor: str
    action: str
    outcome: str
    request_id: str
    correlation_id: str
    idempotency_key: str
    timestamp: datetime


class ExecutionTraceStep(BaseModel):
    """One lifecycle step recorded on an ExecutionResult."""

    step: str
    timestamp: datetime
    status: str
    detail: str = ""


class ExecutorContext(BaseModel):
    """Read-only snapshots the executor needs. Built by the service or tests."""

    as_of: datetime
    plan: SkipValidation[RecoveryPlan]
    recovery_case_id: UUID | None = None
    payment_id: UUID | None = None
    payment_amount: int = 0
    payment_method: PaymentMethod | None = None
    customer_segment: CustomerSegment = CustomerSegment.ACTIVE
    salary_dependent: bool = False
    diagnosis: str | None = None
    policy_decision: str | None = None


class ExecutionResult(BaseModel):
    """Structured simulation result. Informational — no Razorpay, no comms."""

    execution_id: UUID
    strategy: str
    status: ExecutionStatus
    scheduled_at: datetime
    executed_at: datetime | None = None
    execution_type: str
    success: bool = False
    outcome: str
    payment_link_id: str | None = None
    webhook_event_id: str | None = None
    idempotency_key: str
    audit_event_id: UUID
    metadata: dict[str, Any] = Field(default_factory=dict)
    executor_version: str
    generated_at: datetime
    execution_reason: str = ""
    planner_strategy: str = ""
    policy_decision: str | None = None
    diagnosis: str | None = None
    idempotent: bool = False
    human_summary: str = ""
    recovered_value: int = 0
    webhooks: list[SimulatedWebhookEvent] = Field(default_factory=list)
    audit: ExecutionAuditEvent | None = None
    execution_trace: list[ExecutionTraceStep] = Field(default_factory=list)


class BatchExecutorSummary(BaseModel):
    """Aggregate of many ExecutionResult rows."""

    total_plans: int
    executed: int
    successes: int
    failures: int
    duplicates: int
    payment_links_generated: int
    retries_scheduled: int
    estimated_recovered_value: int


class BatchExecutorResult(BaseModel):
    """Per-plan results plus a rollup summary."""

    results: list[ExecutionResult]
    summary: BatchExecutorSummary
