"""Schedule WAIT_FOR_PAYDAY / HONOUR_PROMISE_TO_PAY and transient backoff retries."""

from __future__ import annotations

import logging
from datetime import datetime
from uuid import UUID

from services.scheduler.backoff import next_backoff
from services.scheduler.constants import STATUS_DONE
from services.scheduler.models import ScheduledJob, SchedulerQueueMetrics
from services.scheduler.ports import SchedulerJobStore
from services.scheduler.store import process_scheduler_store

logger = logging.getLogger(__name__)


class ActionScheduler:
    """Enqueue due work. Does not call Razorpay; the orchestrator tick does."""

    def __init__(self, store: SchedulerJobStore | None = None) -> None:
        self._store = store or process_scheduler_store()

    def schedule(
        self,
        *,
        execution_id: UUID,
        recovery_case_id: UUID,
        run_at: datetime,
        reason: str,
        attempt: int = 0,
    ) -> ScheduledJob:
        """Record a future run. Idempotent on ``execution_id``.

        Args:
            execution_id: Recovery action id.
            recovery_case_id: Parent case.
            run_at: When the orchestrator may execute.
            reason: WAIT_FOR_PAYDAY, HONOUR_PROMISE_TO_PAY, COOLDOWN, or BACKOFF.
            attempt: Transient-failure count already consumed.

        Returns:
            The stored job.
        """
        job = ScheduledJob(
            execution_id=execution_id,
            recovery_case_id=recovery_case_id,
            run_at=run_at,
            reason=reason,
            attempt=attempt,
            status="pending",
        )
        stored = self._store.upsert(job)
        logger.info(
            "scheduler.enqueue",
            extra={
                "execution_id": str(execution_id),
                "recovery_case_id": str(recovery_case_id),
                "reason": reason,
            },
        )
        return stored

    def due(self, as_of: datetime) -> list[ScheduledJob]:
        """Jobs whose scheduled time has arrived (still pending)."""
        return self._store.due(as_of)

    def claim_due(self, as_of: datetime) -> list[ScheduledJob]:
        """Pending due jobs, marked running for this tick."""
        claimed: list[ScheduledJob] = []
        for job in self._store.due(as_of):
            self._store.mark_running(job.execution_id)
            updated = self._store.get(job.execution_id)
            claimed.append(updated or job)
            logger.info(
                "scheduler.claim",
                extra={"execution_id": str(job.execution_id), "recovery_case_id": str(job.recovery_case_id)},
            )
        return claimed

    def release(self, execution_id: UUID) -> None:
        """Return a claimed job to pending after a failed tick."""
        self._store.release(execution_id)

    def complete(self, execution_id: UUID, status: str = STATUS_DONE) -> None:
        """Remove a job from the active queue after execute/cancel/dead-letter."""
        self._store.complete(execution_id, status=status)

    def active_count(self) -> int:
        """Pending plus running jobs currently waiting."""
        return self._store.active_count()

    def queue_metrics(self, as_of: datetime) -> SchedulerQueueMetrics:
        """Dashboard Scheduler Queue counts."""
        return self._store.queue_metrics(as_of)

    def backoff_or_dead_letter(self, attempt: int) -> object:
        """Proxy to ``next_backoff`` so callers import one module."""
        return next_backoff(attempt)
