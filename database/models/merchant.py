"""Merchant account that owns customers, subscriptions, and payments."""

from __future__ import annotations

from typing import TYPE_CHECKING

from sqlalchemy import String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from database.models.customer import Customer
    from database.models.merchant_metric import MerchantMetric
    from database.models.payment import Payment
    from database.models.recovery_case import RecoveryCase
    from database.models.subscription import Subscription


class Merchant(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A business using RecoveryPilot to recover at-risk Razorpay revenue.

    Payments reference this table with ON DELETE RESTRICT so a merchant
    with payment history cannot be removed.
    """

    __tablename__ = "merchants"
    __table_args__ = (
        UniqueConstraint("email", name="uq_merchants_email"),
        UniqueConstraint("razorpay_account_id", name="uq_merchants_razorpay_account_id"),
        {"comment": "Merchant tenants. Cannot be deleted while payments exist."},
    )

    merchant_name: Mapped[str] = mapped_column(String(255), nullable=False)
    business_category: Mapped[str] = mapped_column(String(128), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    razorpay_account_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), nullable=False, default="Asia/Kolkata")

    customers: Mapped[list[Customer]] = relationship(
        back_populates="merchant",
        cascade="save-update",
    )
    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="merchant",
        cascade="save-update",
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="merchant",
        cascade="save-update",
        passive_deletes=True,
    )
    recovery_cases: Mapped[list[RecoveryCase]] = relationship(
        back_populates="merchant",
        cascade="save-update",
        passive_deletes=True,
    )
    metrics: Mapped[MerchantMetric | None] = relationship(
        back_populates="merchant",
        cascade="all, delete-orphan",
        uselist=False,
    )
