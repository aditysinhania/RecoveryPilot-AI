"""Per-merchant SaaS settings. Secrets are stored hashed-at-rest only via app policy."""

from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING
from uuid import UUID

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from database.models.base import Base, TimestampMixin, UUIDPrimaryKeyMixin

if TYPE_CHECKING:
    from database.models.merchant import Merchant


class MerchantSettings(UUIDPrimaryKeyMixin, TimestampMixin, Base):
    """Onboarding progress plus Razorpay/Gemini/notification preferences.

    Recovery engines keep reading process env; this table is the merchant UI source.
    """

    __tablename__ = "merchant_settings"
    __table_args__ = ({"comment": "Merchant onboarding and Settings-page preferences."},)

    merchant_id: Mapped[UUID] = mapped_column(
        Uuid(as_uuid=True),
        ForeignKey("merchants.id", ondelete="CASCADE"),
        nullable=False,
        unique=True,
    )
    onboarding_step: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    onboarding_completed: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    onboarding_completed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        nullable=True,
    )
    workspace_kind: Mapped[str] = mapped_column(String(16), nullable=False, default="none")
    razorpay_key_id: Mapped[str | None] = mapped_column(String(128), nullable=True)
    razorpay_key_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    razorpay_webhook_secret: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gemini_api_key: Mapped[str | None] = mapped_column(String(255), nullable=True)
    gemini_model: Mapped[str | None] = mapped_column(String(128), nullable=True)
    notify_email_recovery: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_email_digest: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    notify_webhook_failures: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)

    merchant: Mapped[Merchant] = relationship()
