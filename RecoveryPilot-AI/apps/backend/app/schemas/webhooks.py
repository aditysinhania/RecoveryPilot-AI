"""HTTP DTOs for Razorpay webhook ingest and inbox summary."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel


class WebhookIngestResponse(BaseModel):
    """POST /webhooks/razorpay result."""

    razorpay_event_id: str
    event_type: str
    signature_verified: bool
    replayed: bool = False
    processed: bool = False
    failed: bool = False
    unknown_event: bool = False
    recovery_case_id: UUID | None = None
    received_at: datetime | None = None
    processed_at: datetime | None = None
    message: str = "ok"


class WebhookSummaryResponse(BaseModel):
    """GET /webhooks/summary inbox counts."""

    received: int = 0
    processed: int = 0
    replayed: int = 0
    failed: int = 0
