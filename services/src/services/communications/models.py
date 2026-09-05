"""Outbound communication DTOs. Never hold full PAN/VPA secrets."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class OutboundMessage(BaseModel):
    """One customer-facing recovery notice. Contact values are already masked for logs."""

    channel: str
    recovery_case_id: UUID
    merchant_id: UUID | None = None
    to: str
    template: str
    body: str
    idempotency_key: str
    request_id: str
    correlation_id: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class DeliveryResult(BaseModel):
    """Sandbox delivery outcome. ``provider`` is always a mock in Phase 9B."""

    channel: str
    status: str
    provider: str
    provider_message_id: str | None = None
    rate_limited: bool = False
    skipped_reason: str | None = None
    sent_at: datetime | None = None
