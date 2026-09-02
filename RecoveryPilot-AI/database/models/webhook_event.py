"""Inbound Razorpay webhook inbox. Deduped by provider event id; no domain FKs."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Boolean, DateTime, Index, String, func
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database.models.base import Base, UUIDPrimaryKeyMixin


class WebhookEvent(UUIDPrimaryKeyMixin, Base):
    """Raw Razorpay webhook before it is mapped onto payments or recovery cases.

    `razorpay_event_id` is unique so retries from the provider are idempotent.
    """

    __tablename__ = "webhook_events"
    __table_args__ = (
        Index("ix_webhook_events_razorpay_event_id", "razorpay_event_id", unique=True),
        Index("ix_webhook_events_event_type", "event_type"),
        Index("ix_webhook_events_created_at", "created_at"),
        Index("ix_webhook_events_processed_at", "processed_at"),
        {"comment": "Razorpay webhook inbox. Unique event id prevents double processing."},
    )

    razorpay_event_id: Mapped[str] = mapped_column(String(128), nullable=False)
    event_type: Mapped[str] = mapped_column(String(128), nullable=False)
    payload: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, default=dict)
    signature_verified: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    processed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        nullable=False,
        server_default=func.now(),
        default=lambda: datetime.now(UTC),
    )
