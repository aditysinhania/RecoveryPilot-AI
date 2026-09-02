"""End customer belonging to a merchant."""

from __future__ import annotations

from typing import TYPE_CHECKING

from uuid import UUID

from sqlalchemy import ForeignKey, Index, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin
from database.models.enums import (
    ConsentStatus,
    CustomerSegment,
    PaymentMethod,
    consent_status_enum,
    customer_segment_enum,
    payment_method_enum,
)

if TYPE_CHECKING:
    from database.models.merchant import Merchant
    from database.models.payment import Payment
    from database.models.recovery_case import RecoveryCase
    from database.models.subscription import Subscription


class Customer(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A payer under a merchant. Holds segment, channel preference, and consent."""

    __tablename__ = "customers"
    __table_args__ = (
        Index("ix_customers_merchant_id", "merchant_id"),
        Index("ix_customers_customer_segment", "customer_segment"),
        Index("ix_customers_email", "email"),
        Index("ix_customers_phone", "phone"),
        Index("ix_customers_merchant_email", "merchant_id", "email"),
        {"comment": "Merchant customers. Segment and consent drive recovery tone and stopping rules."},
    )

    merchant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merchants.id", ondelete="RESTRICT"),
        nullable=False,
    )
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(320), nullable=False)
    phone: Mapped[str] = mapped_column(String(32), nullable=False)
    customer_segment: Mapped[CustomerSegment] = mapped_column(
        customer_segment_enum,
        nullable=False,
        default=CustomerSegment.NEW,
    )
    preferred_payment_method: Mapped[PaymentMethod | None] = mapped_column(
        payment_method_enum,
        nullable=True,
    )
    preferred_language: Mapped[str] = mapped_column(String(16), nullable=False, default="en")
    consent_status: Mapped[ConsentStatus] = mapped_column(
        consent_status_enum,
        nullable=False,
        default=ConsentStatus.PENDING,
    )

    merchant: Mapped[Merchant] = relationship(back_populates="customers")
    subscriptions: Mapped[list[Subscription]] = relationship(
        back_populates="customer",
        cascade="save-update",
    )
    payments: Mapped[list[Payment]] = relationship(
        back_populates="customer",
        cascade="save-update",
        passive_deletes=True,
    )
    recovery_cases: Mapped[list[RecoveryCase]] = relationship(
        back_populates="customer",
        cascade="save-update",
        passive_deletes=True,
    )
