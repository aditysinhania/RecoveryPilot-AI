"""Customer promise-to-pay commitments on a recovery case."""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, UUIDPrimaryKeyMixin
from database.models.enums import PromiseStatus, promise_status_enum

if TYPE_CHECKING:
    from database.models.recovery_case import RecoveryCase


class PromiseToPay(UUIDPrimaryKeyMixin, Base):
    """Structured commitment. Recovery should stay silent until promised_date."""

    __tablename__ = "promises_to_pay"
    __table_args__ = (
        Index("ix_promises_to_pay_recovery_case_id", "recovery_case_id"),
        Index("ix_promises_to_pay_promised_date", "promised_date"),
        Index("ix_promises_to_pay_promise_status", "promise_status"),
        {"comment": "Promise-to-pay contracts. Multiple promises per case are allowed."},
    )

    recovery_case_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("recovery_cases.id", ondelete="CASCADE"),
        nullable=False,
    )
    promised_amount: Mapped[int] = mapped_column(Integer, nullable=False, doc="Amount in paise")
    promised_date: Mapped[date] = mapped_column(Date, nullable=False)
    promise_status: Mapped[PromiseStatus] = mapped_column(
        promise_status_enum,
        nullable=False,
        default=PromiseStatus.OPEN,
    )
    fulfilled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )

    recovery_case: Mapped[RecoveryCase] = relationship(back_populates="promises")
