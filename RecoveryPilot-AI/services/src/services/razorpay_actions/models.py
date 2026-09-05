"""Razorpay action DTOs used by the orchestrator. No HTTP client here."""

from __future__ import annotations

from typing import Any
from uuid import UUID

from pydantic import BaseModel, Field


class RazorpayActionRequest(BaseModel):
    """Inputs needed to call Sandbox for one RecoveryPlan step."""

    recovery_case_id: UUID
    payment_id: UUID | None = None
    amount: int
    currency: str = "INR"
    customer_name: str
    customer_email: str
    customer_phone: str
    description: str
    idempotency_key: str
    notes: dict[str, str] = Field(default_factory=dict)


class RazorpayActionResult(BaseModel):
    """Normalized Sandbox outcome for payment link, retry, or mandate session."""

    kind: str
    resource_id: str
    status: str
    short_url: str | None = None
    mock: bool = True
    payload: dict[str, Any] = Field(default_factory=dict)
