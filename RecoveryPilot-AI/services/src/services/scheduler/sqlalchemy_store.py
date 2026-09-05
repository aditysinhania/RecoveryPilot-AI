"""PostgreSQL scheduler_jobs store. No FKs onto recovery_actions or recovery_cases."""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models.scheduler_job import SchedulerJob
from services.scheduler.constants import (
    STATUS_CANCELLED,
    STATUS_DEAD_LETTER,
    STATUS_DONE,
    STATUS_PENDING,
    STATUS_RUNNING,
)
from services.scheduler.models import ScheduledJob, SchedulerQueueMetrics
from services.scheduler.store import metrics_from_jobs

logger = logging.getLogger(__name__)

_TABLE_READY = False


def ensure_scheduler_jobs_table(session: Session) -> None:
    """Create ``scheduler_jobs`` if it is missing. Idempotent (checkfirst)."""
    global _TABLE_READY
    if _TABLE_READY:
        return
    bind = session.get_bind()
    SchedulerJob.__table__.create(bind, checkfirst=True)
    _TABLE_READY = True
    logger.info("scheduler.table.ready")


def _to_job(row: SchedulerJob) -> ScheduledJob:
    """Map an ORM row onto the scheduler DTO."""
    return ScheduledJob(
        execution_id=row.execution_id,
        recovery_case_id=row.recovery_case_id,
        run_at=row.run_at,
        reason=row.reason,
        attempt=row.attempt,
        status=row.status,
    )


class SqlAlchemySchedulerStore:
    """Persist due-work items in ``scheduler_jobs``. Request-scoped session."""

    def __init__(self, db: Session) -> None:
        self._db = db
        try:
            ensure_scheduler_jobs_table(db)
        except Exception as exc:  # noqa: BLE001 — Alembic or first-request race
            logger.info("scheduler.table.ensure_skipped", extra={"error_type": type(exc).__name__})

    def upsert(self, job: ScheduledJob) -> ScheduledJob:
        """Insert or replace a job keyed by ``execution_id``."""
        row = self._db.scalar(select(SchedulerJob).where(SchedulerJob.execution_id == job.execution_id))
        now = datetime.now(UTC)
        if row is None:
            row = SchedulerJob(
                execution_id=job.execution_id,
                recovery_case_id=job.recovery_case_id,
                run_at=job.run_at,
                reason=job.reason,
                attempt=job.attempt,
                status=job.status or STATUS_PENDING,
            )
            self._db.add(row)
            logger.info(
                "scheduler.job.insert",
                extra={
                    "execution_id": str(job.execution_id),
                    "recovery_case_id": str(job.recovery_case_id),
                    "reason": job.reason,
                },
            )
        else:
            row.recovery_case_id = job.recovery_case_id
            row.run_at = job.run_at
            row.reason = job.reason
            row.attempt = job.attempt
            row.status = job.status or STATUS_PENDING
            row.updated_at = now
            logger.info(
                "scheduler.job.update",
                extra={"execution_id": str(job.execution_id), "reason": job.reason},
            )
        self._db.flush()
        return _to_job(row)

    def due(self, as_of: datetime) -> list[ScheduledJob]:
        """Pending jobs whose ``run_at`` is at or before ``as_of``."""
        rows = self._db.scalars(
            select(SchedulerJob)
            .where(SchedulerJob.status == STATUS_PENDING, SchedulerJob.run_at <= as_of)
            .order_by(SchedulerJob.run_at.asc())
        ).all()
        return [_to_job(row) for row in rows]

    def complete(self, execution_id: UUID, status: str = STATUS_DONE) -> None:
        """Mark a job finished so it drops out of the active queue."""
        row = self._db.scalar(select(SchedulerJob).where(SchedulerJob.execution_id == execution_id))
        if row is None:
            return
        row.status = status
        row.updated_at = datetime.now(UTC)
        self._db.flush()
        logger.info(
            "scheduler.job.complete",
            extra={"execution_id": str(execution_id), "status": status},
        )

    def cancel(self, execution_id: UUID) -> None:
        """Drop a job from the active queue."""
        self.complete(execution_id, status=STATUS_CANCELLED)

    def mark_running(self, execution_id: UUID) -> None:
        """Claim a pending job for an in-flight tick."""
        row = self._db.scalar(select(SchedulerJob).where(SchedulerJob.execution_id == execution_id))
        if row is None or row.status != STATUS_PENDING:
            return
        row.status = STATUS_RUNNING
        row.updated_at = datetime.now(UTC)
        self._db.flush()

    def release(self, execution_id: UUID) -> None:
        """Return a running job to pending after a failed tick."""
        row = self._db.scalar(select(SchedulerJob).where(SchedulerJob.execution_id == execution_id))
        if row is None or row.status != STATUS_RUNNING:
            return
        row.status = STATUS_PENDING
        row.updated_at = datetime.now(UTC)
        self._db.flush()
        logger.info("scheduler.job.release", extra={"execution_id": str(execution_id)})

    def active_count(self) -> int:
        """Pending plus running jobs (dashboard Active Scheduler Queue)."""
        rows = self._db.scalars(
            select(SchedulerJob).where(SchedulerJob.status.in_((STATUS_PENDING, STATUS_RUNNING)))
        ).all()
        return len(rows)

    def get(self, execution_id: UUID) -> ScheduledJob | None:
        """Return one job, or ``None``."""
        row = self._db.scalar(select(SchedulerJob).where(SchedulerJob.execution_id == execution_id))
        if row is None:
            return None
        return _to_job(row)

    def queue_metrics(self, as_of: datetime) -> SchedulerQueueMetrics:
        """Scheduled / running / delayed / dead-letter counts at ``as_of``."""
        rows = self._db.scalars(
            select(SchedulerJob).where(
                SchedulerJob.status.in_((STATUS_PENDING, STATUS_RUNNING, STATUS_DEAD_LETTER, STATUS_DONE))
            )
        ).all()
        jobs = [_to_job(row) for row in rows]
        return metrics_from_jobs(jobs, as_of)
