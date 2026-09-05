"""Scheduler store port. Implementations may be in-memory or SQLAlchemy."""

from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from services.scheduler.models import ScheduledJob, SchedulerQueueMetrics


class SchedulerJobStore(Protocol):
    """Persist due-work items. Does not call Razorpay or change recovery_actions."""

    def upsert(self, job: ScheduledJob) -> ScheduledJob:
        """Insert or replace a job keyed by ``execution_id``."""
        ...

    def due(self, as_of: datetime) -> list[ScheduledJob]:
        """Pending jobs whose ``run_at`` is at or before ``as_of``."""
        ...

    def complete(self, execution_id: UUID, status: str = "done") -> None:
        """Mark a job finished so it drops out of the active queue."""
        ...

    def cancel(self, execution_id: UUID) -> None:
        """Drop a job from the active queue."""
        ...

    def mark_running(self, execution_id: UUID) -> None:
        """Claim a pending job for an in-flight tick."""
        ...

    def release(self, execution_id: UUID) -> None:
        """Return a running job to pending after a failed tick."""
        ...

    def active_count(self) -> int:
        """Pending plus running jobs (dashboard Active Scheduler Queue)."""
        ...

    def get(self, execution_id: UUID) -> ScheduledJob | None:
        """Return one job, or ``None``."""
        ...

    def queue_metrics(self, as_of: datetime) -> SchedulerQueueMetrics:
        """Scheduled / running / delayed / dead-letter counts at ``as_of``."""
        ...
