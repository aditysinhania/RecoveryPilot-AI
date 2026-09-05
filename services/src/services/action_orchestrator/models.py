"""Orchestrator DTOs. Persistence uses existing recovery_actions + audit_logs rows."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field

from services.communications.models import DeliveryResult
from services.planner.models import PlannerStrategy, RecoveryPlan
from services.policy.models import PolicyDecisionResult
from services.scheduler.models import SchedulerQueueMetrics
from shared.enums import ExecutionStatus, RecoveryActionType


class ActionCustomerSnapshot(BaseModel):
    """Customer fields needed to call Sandbox and mock comms. No PAN/VPA."""

    id: UUID
    full_name: str
    email: str
    phone: str
    consent_granted: bool
    merchant_id: UUID | None = None


class ActionPaymentSnapshot(BaseModel):
    """Payment amount and Razorpay ids for retry payloads."""

    id: UUID
    amount: int
    currency: str = "INR"
    razorpay_order_id: str | None = None
    razorpay_payment_id: str | None = None


class ActionRecord(BaseModel):
    """In-memory recovery_actions row. ``id`` is the execution_id."""

    id: UUID
    recovery_case_id: UUID
    action_type: RecoveryActionType
    scheduled_time: datetime | None = None
    executed_time: datetime | None = None
    execution_status: ExecutionStatus = ExecutionStatus.SCHEDULED
    razorpay_payment_link: str | None = None
    retry_number: int = 0
    response_code: str | None = None
    response_message: str | None = None
    action_metadata: dict[str, Any] = Field(default_factory=dict)
    created_at: datetime | None = None


class GateDecision(BaseModel):
    """Policy + cooldown gate evaluated immediately before an outbound action."""

    allow_now: bool
    defer: bool = False
    block: bool = False
    reason: str
    run_at: datetime | None = None
    blocked_channels: list[str] = Field(default_factory=list)


class ActionExecutionResult(BaseModel):
    """API/service result for execute, schedule, replay, or a scheduler tick."""

    status: str = "ok"
    execution_id: UUID
    recovery_case_id: UUID
    idempotency_key: str
    planner_strategy: str
    action_type: str
    display_status: str
    execution_status: str
    action_chip: str
    scheduled_time: datetime | None = None
    executed_time: datetime | None = None
    retry_attempts: int = 0
    payment_link: str | None = None
    delivery_status: str | None = None
    deliveries: list[DeliveryResult] = Field(default_factory=list)
    request_id: str
    correlation_id: str
    replayed: bool = False
    dead_lettered: bool = False
    policy_reason: str | None = None
    razorpay_resource_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionStatusResult(BaseModel):
    """Latest execution plus history for GET /actions/{case_id}/status."""

    recovery_case_id: UUID
    latest: ActionExecutionResult | None = None
    history: list[ActionExecutionResult] = Field(default_factory=list)
    active_scheduler_queue: int = 0
    scheduler_queue: SchedulerQueueMetrics = Field(default_factory=SchedulerQueueMetrics)


class ActionDashboardSummary(BaseModel):
    """Merchant-level orchestrator KPIs for the dashboard strip."""

    scheduled_actions_today: int = 0
    payment_links_sent: int = 0
    successful_retries: int = 0
    failed_deliveries: int = 0
    active_scheduler_queue: int = 0
    scheduler_queue: SchedulerQueueMetrics = Field(default_factory=SchedulerQueueMetrics)
    chips: dict[str, str] = Field(default_factory=dict)


class OrchestratorContext(BaseModel):
    """Inputs for one run. Plan and policy are produced by existing engines."""

    as_of: datetime
    plan: RecoveryPlan
    policy: PolicyDecisionResult
    customer: ActionCustomerSnapshot
    payment: ActionPaymentSnapshot
    request_id: str
    correlation_id: str
    merchant_name: str = "FitLife Gym"
