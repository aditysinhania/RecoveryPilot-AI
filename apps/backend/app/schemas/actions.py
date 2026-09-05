"""HTTP DTOs for the recovery action orchestrator."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class SchedulerQueueMetrics(BaseModel):
    """Scheduler Queue chips: scheduled, running, delayed, dead-letter."""

    scheduled: int = 0
    running: int = 0
    delayed: int = 0
    dead_letter: int = 0


class ActionDelivery(BaseModel):
    """One sandbox communication attempt."""

    channel: str
    status: str
    provider: str
    provider_message_id: str | None = None
    rate_limited: bool = False
    skipped_reason: str | None = None
    sent_at: datetime | None = None


class ActionExecutionResponse(BaseModel):
    """Execute / schedule / replay result."""

    model_config = ConfigDict(from_attributes=True)

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
    deliveries: list[ActionDelivery] = Field(default_factory=list)
    request_id: str
    correlation_id: str
    replayed: bool = False
    dead_lettered: bool = False
    policy_reason: str | None = None
    razorpay_resource_id: str | None = None
    metadata: dict[str, Any] = Field(default_factory=dict)


class ActionStatusResponse(BaseModel):
    """Latest execution plus history."""

    recovery_case_id: UUID
    latest: ActionExecutionResponse | None = None
    history: list[ActionExecutionResponse] = Field(default_factory=list)
    active_scheduler_queue: int = 0
    scheduler_queue: SchedulerQueueMetrics = Field(default_factory=SchedulerQueueMetrics)


class ActionDashboardResponse(BaseModel):
    """Merchant-level orchestrator KPIs."""

    scheduled_actions_today: int = 0
    payment_links_sent: int = 0
    successful_retries: int = 0
    failed_deliveries: int = 0
    active_scheduler_queue: int = 0
    scheduler_queue: SchedulerQueueMetrics = Field(default_factory=SchedulerQueueMetrics)
    chips: dict[str, str] = Field(default_factory=dict)
