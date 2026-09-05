"""Razorpay payment attempts — the core ledger for recovery."""

from __future__ import annotations

from datetime import date, datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Date, DateTime, ForeignKey, Index, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from database.models.enums import (
    FailureReason,
    PaymentMethod,
    PaymentStatus,
    failure_reason_enum,
    payment_method_enum,
    payment_status_enum,
)

if TYPE_CHECKING:
    from database.models.customer import Customer
    from database.models.merchant import Merchant
    from database.models.recovery_case import RecoveryCase
    from database.models.subscription import Subscription


class Payment(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """One charge attempt. Status, failure reason, and amount drive diagnosis and metrics.

    Merchants with rows here cannot be deleted (ON DELETE RESTRICT).
    """

    __tablename__ = "payments"
    __table_args__ = (
        Index("ix_payments_payment_status", "payment_status"),
        Index("ix_payments_failure_reason", "failure_reason"),
        Index("ix_payments_payment_due_date", "payment_due_date"),
        Index("ix_payments_customer_id", "customer_id"),
        Index("ix_payments_merchant_id", "merchant_id"),
        Index("ix_payments_amount", "amount"),
        Index("ix_payments_subscription_id", "subscription_id"),
        Index("ix_payments_razorpay_payment_id", "razorpay_payment_id"),
        Index("ix_payments_idempotency_key", "idempotency_key", unique=True),
        Index(
            "ix_payments_merchant_status_created",
            "merchant_id",
            "payment_status",
            "created_at",
        ),
        Index("ix_payments_merchant_due", "merchant_id", "payment_due_date"),
        Index("ix_payments_customer_status", "customer_id", "payment_status"),
        Index(
            "ix_payments_merchant_failure_created",
            "merchant_id",
            "failure_reason",
            "created_at",
        ),
        Index("ix_payments_status_due", "payment_status", "payment_due_date"),
        {"comment": "Payment ledger. Composite indexes support merchant dashboard analytics."},
    )

    merchant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merchants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    customer_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("customers.id", ondelete="RESTRICT"),
        nullable=False,
    )
    subscription_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("subscriptions.id", ondelete="RESTRICT"),
        nullable=True,
    )
    razorpay_order_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    razorpay_payment_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    idempotency_key: Mapped[str | None] = mapped_column(String(128), nullable=True)
    payment_status: Mapped[PaymentStatus] = mapped_column(
        payment_status_enum,
        nullable=False,
        default=PaymentStatus.PENDING,
    )
    failure_reason: Mapped[FailureReason | None] = mapped_column(
        failure_reason_enum,
        nullable=True,
    )
    payment_method: Mapped[PaymentMethod | None] = mapped_column(
        payment_method_enum,
        nullable=True,
    )
    amount: Mapped[int] = mapped_column(Integer, nullable=False, doc="Amount in paise")
    currency: Mapped[str] = mapped_column(String(3), nullable=False, default="INR")
    attempt_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    payment_due_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    paid_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    merchant: Mapped[Merchant] = relationship(back_populates="payments")
    customer: Mapped[Customer] = relationship(back_populates="payments")
    subscription: Mapped[Subscription | None] = relationship(back_populates="payments")
    recovery_cases: Mapped[list[RecoveryCase]] = relationship(
        back_populates="payment",
        cascade="save-update",
        passive_deletes=True,
    )
