"""Standard success and error envelopes for every endpoint."""

from __future__ import annotations

from typing import Any, TypeVar

from fastapi.responses import JSONResponse

from app.schemas.common import ApiResponse, ErrorResponse, PaginatedResponse
from app.utils.pagination import build_page_meta
from app.utils.request_id import get_correlation_id, get_request_id
from app.utils.time import isoformat_now

T = TypeVar("T")


def _ids() -> tuple[str, str]:
    """Return (request_id, correlation_id) from the current task."""
    return get_request_id(), get_correlation_id()


def success_body(
    data: Any = None,
    message: str = "ok",
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Build the success envelope as a dict (OpenAPI uses ``ApiResponse``)."""
    rid, cid = _ids()
    return ApiResponse[Any](
        message=message,
        data=data,
        request_id=request_id or rid,
        correlation_id=correlation_id or cid,
        timestamp=isoformat_now(),
    ).model_dump(mode="json")


def paginated_body(
    data: list[Any],
    *,
    page: int,
    page_size: int,
    total: int,
    message: str = "ok",
) -> dict[str, Any]:
    """Build a paginated success envelope including page-window metadata."""
    rid, cid = _ids()
    meta = build_page_meta(page, page_size, total)
    return PaginatedResponse[Any](
        message=message,
        data=data,
        page=meta.page,
        page_size=meta.page_size,
        total=meta.total_records,
        total_records=meta.total_records,
        total_pages=meta.total_pages,
        has_next=meta.has_next,
        has_previous=meta.has_previous,
        request_id=rid,
        correlation_id=cid,
        timestamp=isoformat_now(),
    ).model_dump(mode="json")


def error_body(
    error: str,
    code: str,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> dict[str, Any]:
    """Build the failure envelope."""
    rid, cid = _ids()
    return ErrorResponse(
        error=error,
        message=error,
        code=code,
        request_id=request_id or rid,
        correlation_id=correlation_id or cid,
        timestamp=isoformat_now(),
    ).model_dump(mode="json")


def error_response(
    error: str,
    code: str,
    status_code: int,
    request_id: str | None = None,
    correlation_id: str | None = None,
) -> JSONResponse:
    """Return a JSON error with the standard body."""
    return JSONResponse(
        status_code=status_code,
        content=error_body(
            error=error,
            code=code,
            request_id=request_id,
            correlation_id=correlation_id,
        ),
    )
