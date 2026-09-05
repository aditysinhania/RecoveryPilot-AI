"""Typed Razorpay Sandbox payloads returned to ``services/razorpay_actions``."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class RazorpayResource(BaseModel):
    """One Sandbox resource created or fetched by the client."""

    resource_type: str
    resource_id: str
    status: str
    short_url: str | None = None
    amount: int | None = None
    currency: str = "INR"
    mock: bool = True
    raw: dict[str, Any] = Field(default_factory=dict)
