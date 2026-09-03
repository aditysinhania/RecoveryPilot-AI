"""Standard success and error envelopes for every endpoint."""

from __future__ import annotations

from typing import Any

from fastapi.responses import JSONResponse

from app.utils.request_id import get_request_id
from app.utils.time import isoformat_now


def success_body(
    data: Any = None,
    message: str = "ok",
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build the success envelope.

    Args:
        data: Payload placed under ``data``.
        message: Short human summary.
        request_id: Override; defaults to the request contextvar.
    """
    return {
        "success": True,
        "message": message,
        "data": data,
        "request_id": request_id or get_request_id(),
        "timestamp": isoformat_now(),
    }


def error_body(
    error: str,
    code: str,
    request_id: str | None = None,
) -> dict[str, Any]:
    """Build the failure envelope."""
    return {
        "success": False,
        "error": error,
        "code": code,
        "request_id": request_id or get_request_id(),
        "timestamp": isoformat_now(),
    }


def error_response(
    error: str,
    code: str,
    status_code: int,
    request_id: str | None = None,
) -> JSONResponse:
    """Return a JSON error with the standard body."""
    return JSONResponse(
        status_code=status_code,
        content=error_body(error=error, code=code, request_id=request_id),
    )
