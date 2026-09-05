"""Generic HTTP envelopes used by every v1 endpoint."""

from __future__ import annotations

from typing import Any, Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class ApiResponse(BaseModel, Generic[T]):
    """Standard success envelope."""

    success: bool = True
    message: str = "ok"
    data: T | None = None
    request_id: str
    correlation_id: str
    timestamp: str


class PaginatedResponse(BaseModel, Generic[T]):
    """Success envelope for a page of rows."""

    success: bool = True
    message: str = "ok"
    data: list[T] = Field(default_factory=list)
    page: int
    page_size: int
    total: int
    total_records: int
    total_pages: int
    has_next: bool
    has_previous: bool
    request_id: str
    correlation_id: str
    timestamp: str


class ErrorResponse(BaseModel):
    """Standard failure envelope returned by exception handlers."""

    success: bool = False
    error: str
    message: str = ""
    code: str
    request_id: str
    correlation_id: str
    timestamp: str


class HealthData(BaseModel):
    """Liveness / readiness payload."""

    status: str
    environment: str
    version: str
    timestamp: str
    database: str = Field(description="connected | unavailable")


# Backward-compatible alias used by Phase 4A health helpers.
SuccessResponse = ApiResponse[Any]
