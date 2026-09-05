"""Persisted scheduler due-queue. No foreign keys onto recovery tables."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from sqlalchemy import DateTime, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin


class SchedulerJob(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One WAIT_FOR_PAYDAY, HONOUR_PROMISE_TO_PAY, cooldown, or backoff job.

    ``execution_id`` and ``recovery_case_id`` are UUIDs without ForeignKey so
    existing recovery_actions / recovery_cases relationships stay unchanged.
    """

    __tablename__ = "scheduler_jobs"
    __table_args__ = (
        Index("ix_scheduler_jobs_execution_id", "execution_id", unique=True),
        Index("ix_scheduler_jobs_recovery_case_id", "recovery_case_id"),
        Index("ix_scheduler_jobs_run_at", "run_at"),
        Index("ix_scheduler_jobs_status", "status"),
        Index("ix_scheduler_jobs_status_run_at", "status", "run_at"),
        {"comment": "Persisted action scheduler queue. No domain FKs."},
    )

    execution_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    recovery_case_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    reason: Mapped[str] = mapped_column(String(128), nullable=False)
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    status: Mapped[str] = mapped_column(String(32), nullable=False, default="pending")
