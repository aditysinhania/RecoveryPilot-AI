"""Recurring subscription billed through Razorpay mandates."""

from __future__ import annotations

from datetime import date
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from database.models.enums import (
    BillingFrequency,
    MandateStatus,
    SubscriptionStatus,
    billing_frequency_enum,
    mandate_status_enum,
    subscription_status_enum,
)

if TYPE_CHECKING:
    from database.models.customer import Customer
    from database.models.merchant import Merchant
    from database.models.payment import Payment


class Subscription(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Recurring plan. Payment attempts hang off this row for dunning and Autopay."""

    __tablename__ = "subscriptions"
    __table_args__ = (
        Index("ix_subscriptions_next_billing_date", "next_billing_date"),
        Index("ix_subscriptions_subscription_status", "subscription_status"),
        Index("ix_subscriptions_customer_id", "customer_id"),
        Index("ix_subscriptions_merchant_id", "merchant_id"),
        Index("ix_subscriptions_status_next_bill", "subscription_status", "next_billing_date"),
        {"comment": "Recurring subscriptions. next_billing_date drives mandate retry sequencing."},
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
    subscription_name: Mapped[str] = mapped_column(String(255), nullable=False)
    billing_amount: Mapped[int] = mapped_column(Integer, nullable=False, doc="Amount in paise")
    billing_frequency: Mapped[BillingFrequency] = mapped_column(
        billing_frequency_enum,
        nullable=False,
    )
    next_billing_date: Mapped[date] = mapped_column(Date, nullable=False)
    mandate_status: Mapped[MandateStatus] = mapped_column(
        mandate_status_enum,
        nullable=False,
        default=MandateStatus.PENDING,
    )
    subscription_status: Mapped[SubscriptionStatus] = mapped_column(
        subscription_status_enum,
        nullable=False,
        default=SubscriptionStatus.ACTIVE,
    )

    customer: Mapped[Customer] = relationship(back_populates="subscriptions")
    merchant: Mapped[Merchant] = relationship(back_populates="subscriptions")
    payments: Mapped[list[Payment]] = relationship(
        back_populates="subscription",
        cascade="save-update",
        passive_deletes=True,
    )
