"""Merchant operator accounts. Separate from the merchants tenant row."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, String, UniqueConstraint, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from database.models.auth_session import AuthSession
    from database.models.merchant import Merchant


class MerchantUser(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """A human operator who signs in to RecoveryPilot.

    ``merchant_id`` is null until onboarding creates the tenant.
    """

    __tablename__ = "merchant_users"
    __table_args__ = (
        UniqueConstraint("email", name="uq_merchant_users_email"),
        {"comment": "SaaS login identities. Password hashes only; never store plaintext."},
    )

    email: Mapped[str] = mapped_column(String(320), nullable=False)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    full_name: Mapped[str] = mapped_column(String(255), nullable=False)
    role: Mapped[str] = mapped_column(String(32), nullable=False, default="owner")
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    merchant_id: Mapped[UUID | None] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merchants.id", ondelete="SET NULL"),
        nullable=True,
        index=True,
    )
    last_login_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    merchant: Mapped[Merchant | None] = relationship()
    sessions: Mapped[list[AuthSession]] = relationship(
        back_populates="user",
        cascade="all, delete-orphan",
    )
