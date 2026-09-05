"""Scheduler job records and dashboard queue metrics."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class ScheduledJob(BaseModel):
    """One due-work item for WAIT_FOR_PAYDAY, HONOUR_PROMISE_TO_PAY, or backoff."""

    execution_id: UUID
    recovery_case_id: UUID
    run_at: datetime
    reason: str
    attempt: int = 0
    status: str = "pending"


class SchedulerQueueMetrics(BaseModel):
    """Dashboard Scheduler Queue chips. Delayed means pending and overdue."""

    scheduled: int = 0
    running: int = 0
    delayed: int = 0
    dead_letter: int = 0
