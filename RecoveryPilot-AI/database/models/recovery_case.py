"""One recovery journey for a failed or at-risk payment."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from database.models.enums import (
    FailureReason,
    RecoveryStatus,
    failure_reason_enum,
    recovery_status_enum,
)

if TYPE_CHECKING:
    from database.models.audit_log import AuditLog
    from database.models.customer import Customer
    from database.models.merchant import Merchant
    from database.models.payment import Payment
    from database.models.promise_to_pay import PromiseToPay
    from database.models.recovery_action import RecoveryAction


class RecoveryCase(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Agent-owned workflow for a single payment. Actions, promises, and audit hang off it."""

    __tablename__ = "recovery_cases"
    __table_args__ = (
        Index("ix_recovery_cases_payment_id", "payment_id", unique=True),
        Index("ix_recovery_cases_customer_id", "customer_id"),
        Index("ix_recovery_cases_merchant_id", "merchant_id"),
        Index("ix_recovery_cases_recovery_status", "recovery_status"),
        Index("ix_recovery_cases_merchant_status", "merchant_id", "recovery_status"),
        {"comment": "One recovery journey per payment. Unique payment_id enforces a single open path."},
    )

    payment_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("payments.id", ondelete="RESTRICT"),
        nullable=False,
    )
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    merchant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merchants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    recovery_status: Mapped[RecoveryStatus] = mapped_column(
        recovery_status_enum,
        nullable=False,
        default=RecoveryStatus.OPEN,
    )
    diagnosed_reason: Mapped[FailureReason | None] = mapped_column(
        failure_reason_enum,
        nullable=True,
    )
    diagnosis_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    diagnosis_version: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ai_confidence: Mapped[float | None] = mapped_column(Float, nullable=True)
    priority_score: Mapped[float | None] = mapped_column(Float, nullable=True)
    recovery_started_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    recovery_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )

    payment: Mapped[Payment] = relationship(back_populates="recovery_cases")
    customer: Mapped[Customer] = relationship(back_populates="recovery_cases")
    merchant: Mapped[Merchant] = relationship(back_populates="recovery_cases")
    actions: Mapped[list[RecoveryAction]] = relationship(
        back_populates="recovery_case",
        cascade="all, delete-orphan",
    )
    promises: Mapped[list[PromiseToPay]] = relationship(
        back_populates="recovery_case",
        cascade="all, delete-orphan",
    )
    audit_logs: Mapped[list[AuditLog]] = relationship(
        back_populates="recovery_case",
        cascade="save-update",
        passive_deletes=True,
    )
