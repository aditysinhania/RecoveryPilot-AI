"""DTOs for Razorpay webhook ingest, dispatch, and dashboard counts."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class WebhookSummary(BaseModel):
    """Inbox KPIs for GET /webhooks/summary."""

    received: int = 0
    processed: int = 0
    replayed: int = 0
    failed: int = 0


class WebhookIngestResult(BaseModel):
    """Outcome of one POST /webhooks/razorpay delivery."""

    razorpay_event_id: str
    event_type: str
    signature_verified: bool
    replayed: bool = False
    processed: bool = False
    failed: bool = False
    unknown_event: bool = False
    recovery_case_id: UUID | None = None
    request_id: str
    correlation_id: str
    received_at: datetime | None = None
    processed_at: datetime | None = None
    message: str = "ok"
    metadata: dict[str, Any] = Field(default_factory=dict)
