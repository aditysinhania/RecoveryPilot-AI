"""Webhook event create, read, update, and response schemas."""

from __future__ import annotations

from datetime import datetime
from typing import Any
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field


class WebhookEventCreate(BaseModel):
    """Payload to persist one inbound Razorpay webhook."""

    razorpay_event_id: str = Field(..., min_length=1, max_length=128)
    event_type: str = Field(..., min_length=1, max_length=128)
    payload: dict[str, Any] = Field(default_factory=dict)
    signature_verified: bool = False
    processed_at: datetime | None = None


class WebhookEventUpdate(BaseModel):
    """Mark a webhook as processed or record signature verification."""

    signature_verified: bool | None = None
    processed_at: datetime | None = None


class WebhookEventRead(BaseModel):
    """Webhook inbox row as stored in PostgreSQL."""

    model_config = ConfigDict(from_attributes=True)

    id: UUID
    razorpay_event_id: str
    event_type: str
    payload: dict[str, Any]
    signature_verified: bool
    processed_at: datetime | None
    created_at: datetime


class WebhookEventResponse(WebhookEventRead):
    """Public webhook DTO used by ingestion and replay."""
