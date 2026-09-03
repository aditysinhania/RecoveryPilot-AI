"""HTTP envelope schemas. Domain entities remain in ``shared.schemas``."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class SuccessResponse(BaseModel):
    """Standard success body returned by every healthy endpoint."""

    success: bool = True
    message: str
    data: Any = None
    request_id: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Standard failure body returned by exception handlers."""

    success: bool = False
    error: str
    code: str
    request_id: str
    timestamp: str


class HealthData(BaseModel):
    """Liveness payload."""

    status: str
    environment: str
    version: str
    timestamp: str
    database: str = Field(description="connected | unavailable")
