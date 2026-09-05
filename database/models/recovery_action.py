"""Scheduled or executed recovery interventions."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
from uuid import UUID

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Uuid, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, UUIDPrimaryKeyMixin
from database.models.enums import (
    ExecutionStatus,
    RecoveryActionType,
    execution_status_enum,
    recovery_action_type_enum,
)

if TYPE_CHECKING:
    from database.models.recovery_case import RecoveryCase


class RecoveryAction(UUIDPrimaryKeyMixin, Base):
    """One bounded step: retry, pay-link, wait, promise, stop, or escalate."""

    __tablename__ = "recovery_actions"
    __table_args__ = (
        Index("ix_recovery_actions_scheduled_time", "scheduled_time"),
        Index("ix_recovery_actions_execution_status", "execution_status"),
        Index("ix_recovery_actions_action_type", "action_type"),
        Index("ix_recovery_actions_recovery_case_id", "recovery_case_id"),
        Index(
            "ix_recovery_actions_case_status_scheduled",
            "recovery_case_id",
            "execution_status",
            "scheduled_time",
        ),
        {"comment": "Recovery interventions. scheduled_time is the sequencer for retries and payday waits."},
    )

    recovery_case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    action_type: Mapped[RecoveryActionType] = mapped_column(
        recovery_action_type_enum,
        nullable=False,
    )
    scheduled_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    executed_time: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    execution_status: Mapped[ExecutionStatus] = mapped_column(
        execution_status_enum,
        nullable=False,
        default=ExecutionStatus.SCHEDULED,
    )
    razorpay_payment_link: Mapped[str | None] = mapped_column(String(512), nullable=True)
    retry_number: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    response_code: Mapped[str | None] = mapped_column(String(64), nullable=True)
    response_message: Mapped[str | None] = mapped_column(String(512), nullable=True)
    action_metadata: Mapped[dict[str, Any]] = mapped_column(
        "metadata",
        JSONB,
        nullable=False,
        default=dict,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )

    recovery_case: Mapped[RecoveryCase] = relationship(back_populates="actions")
