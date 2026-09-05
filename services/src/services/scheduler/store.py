"""In-memory due queue used by unit tests. Production uses SqlAlchemySchedulerStore."""

from __future__ import annotations

from datetime import UTC, datetime
from threading import Lock
from uuid import UUID

from services.scheduler.constants import (
    STATUS_CANCELLED,
    STATUS_DEAD_LETTER,
    STATUS_DONE,
    STATUS_PENDING,
    STATUS_RUNNING,
)
from services.scheduler.models import ScheduledJob, SchedulerQueueMetrics


def _aware(value: datetime) -> datetime:
    """Treat naive datetimes as UTC so queue comparisons stay consistent."""
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value


def metrics_from_jobs(jobs: list[ScheduledJob], as_of: datetime) -> SchedulerQueueMetrics:
    """Count scheduled / running / delayed / dead-letter from a job list."""
    clock = _aware(as_of)
    scheduled = 0
    running = 0
    delayed = 0
    dead_letter = 0
    for job in jobs:
        if job.status == STATUS_RUNNING:
            running += 1
        elif job.status == STATUS_DEAD_LETTER:
            dead_letter += 1
        elif job.status == STATUS_PENDING:
            if _aware(job.run_at) > clock:
                scheduled += 1
            else:
                delayed += 1
    return SchedulerQueueMetrics(
        scheduled=scheduled,
        running=running,
        delayed=delayed,
        dead_letter=dead_letter,
    )


class SchedulerStore:
    """Process-local due set. Tests inject a fresh instance; production does not."""

    def __init__(self) -> None:
        self._lock = Lock()
        self._jobs: dict[UUID, ScheduledJob] = {}

    def upsert(self, job: ScheduledJob) -> ScheduledJob:
        """Insert or replace a pending job."""
        with self._lock:
            self._jobs[job.execution_id] = job
            return job

    def due(self, as_of: datetime) -> list[ScheduledJob]:
        """Pending jobs whose ``run_at`` is at or before ``as_of``."""
        clock = _aware(as_of)
        with self._lock:
            return [
                job
                for job in self._jobs.values()
                if job.status == STATUS_PENDING and _aware(job.run_at) <= clock
            ]

    def complete(self, execution_id: UUID, status: str = STATUS_DONE) -> None:
        """Mark a job finished so it drops out of the active queue."""
        with self._lock:
            job = self._jobs.get(execution_id)
            if job is None:
                return
            self._jobs[execution_id] = job.model_copy(update={"status": status})

    def cancel(self, execution_id: UUID) -> None:
        """Drop a job from the active queue."""
        self.complete(execution_id, status=STATUS_CANCELLED)

    def mark_running(self, execution_id: UUID) -> None:
        """Claim a pending job for an in-flight tick."""
        with self._lock:
            job = self._jobs.get(execution_id)
            if job is None or job.status != STATUS_PENDING:
                return
            self._jobs[execution_id] = job.model_copy(update={"status": STATUS_RUNNING})

    def release(self, execution_id: UUID) -> None:
        """Return a running job to pending after a failed tick."""
        with self._lock:
            job = self._jobs.get(execution_id)
            if job is None or job.status != STATUS_RUNNING:
                return
            self._jobs[execution_id] = job.model_copy(update={"status": STATUS_PENDING})

    def active_count(self) -> int:
        """Number of pending or running jobs (dashboard Active Scheduler Queue)."""
        with self._lock:
            return sum(
                1
                for job in self._jobs.values()
                if job.status in {STATUS_PENDING, STATUS_RUNNING}
            )

    def get(self, execution_id: UUID) -> ScheduledJob | None:
        """Return one job, or ``None``."""
        with self._lock:
            return self._jobs.get(execution_id)

    def queue_metrics(self, as_of: datetime) -> SchedulerQueueMetrics:
        """Scheduled / running / delayed / dead-letter counts at ``as_of``."""
        with self._lock:
            return metrics_from_jobs(list(self._jobs.values()), as_of)


_PROCESS_STORE = SchedulerStore()


def process_scheduler_store() -> SchedulerStore:
    """Return the process-wide in-memory scheduler store (tests / fallback)."""
    return _PROCESS_STORE
