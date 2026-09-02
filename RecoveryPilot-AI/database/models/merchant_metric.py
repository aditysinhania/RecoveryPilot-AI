"""Precomputed merchant dashboard totals."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import DateTime, Float, ForeignKey, Integer, Uuid, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from database.models.merchant import Merchant


class MerchantMetric(UUIDPrimaryKeyMixin, Base):
    """One snapshot row per merchant. Amounts are paise; recovery_rate is 0..1."""

    __tablename__ = "merchant_metrics"
    __table_args__ = (
        {"comment": "Precomputed dashboard KPIs. Unique merchant_id keeps one live snapshot."},
    )

    merchant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    revenue_at_risk: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recovered_revenue: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    suppressed_revenue: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    recovery_rate: Mapped[float] = mapped_column(Float, nullable=False, default=0.0)
    escalation_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    policy_stop_count: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
        onupdate=lambda: datetime.now(UTC),
    )

    merchant: Mapped[Merchant] = relationship(back_populates="metrics")
