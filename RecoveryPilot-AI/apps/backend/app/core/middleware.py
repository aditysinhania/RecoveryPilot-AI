"""ASGI middleware: trusted host, CORS, gzip, ids, timing, access logs, metrics."""

from __future__ import annotations

import logging
import re
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.constants import (
    CORRELATION_ID_HEADER,
    GZIP_MINIMUM_BYTES,
    REQUEST_ID_HEADER,
)
from app.config.settings import Settings
from app.core.metrics import observe_http
from app.utils.request_id import (
    set_correlation_id,
    set_execution_id,
    set_merchant_id,
    set_recovery_case_id,
    set_request_id,
)
from app.utils.uuid import new_uuid_str

logger = logging.getLogger(__name__)

_UUID_RE = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_SKIP_METRICS_PATHS = frozenset({"/metrics"})


def _route_template(request: Request) -> str:
    """Prefer the matched FastAPI route template to keep metric cardinality low."""
    route = request.scope.get("route")
    path = getattr(route, "path", None)
    if isinstance(path, str) and path:
        return path
    return request.url.path


def _bind_ids_from_path(path: str) -> None:
    """Copy UUID path segments into log context. Does not change routing."""
    merchant = re.search(r"/merchants/(" + _UUID_RE.pattern + r")", path)
    if merchant:
        set_merchant_id(merchant.group(1))
    case = re.search(
        r"/(?:cases|recovery|actions)/(" + _UUID_RE.pattern + r")",
        path,
    )
    if case:
        set_recovery_case_id(case.group(1))
    execution = re.search(r"/replay/(" + _UUID_RE.pattern + r")", path)
    if execution:
        set_execution_id(execution.group(1))


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign request_id and correlation_id; echo both on the response."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Bind ids onto the request, contextvars, and response headers."""
        incoming_rid = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming_rid.strip() if incoming_rid else new_uuid_str()
        incoming_cid = request.headers.get(CORRELATION_ID_HEADER)
        correlation_id = incoming_cid.strip() if incoming_cid else request_id
        request.state.request_id = request_id
        request.state.correlation_id = correlation_id
        set_request_id(request_id)
        set_correlation_id(correlation_id)
        set_merchant_id("")
        set_recovery_case_id("")
        set_execution_id("")
        _bind_ids_from_path(request.url.path)
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Record elapsed milliseconds on ``request.state.latency_ms``."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Time the downstream stack and record Prometheus HTTP metrics."""
        started = time.perf_counter()
        response = await call_next(request)
        elapsed = time.perf_counter() - started
        request.state.latency_ms = round(elapsed * 1000, 2)
        response.headers["X-Response-Time-Ms"] = str(request.state.latency_ms)
        path = _route_template(request)
        if path not in _SKIP_METRICS_PATHS:
            observe_http(request.method, path, response.status_code, elapsed)
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, latency, request_id, and correlation_id."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Emit one access log line after the response is produced."""
        response = await call_next(request)
        path = request.url.path
        if path in _SKIP_METRICS_PATHS:
            return response
        latency = getattr(request.state, "latency_ms", None)
        logger.info(
            "http.request",
            extra={
                "request_id": getattr(request.state, "request_id", "-"),
                "correlation_id": getattr(request.state, "correlation_id", "-"),
                "method": request.method,
                "path": path,
                "status_code": response.status_code,
                "latency_ms": latency,
            },
        )
        return response


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Attach the middleware stack. Last ``add_middleware`` is outermost.

    Request flow (outer → inner):
    TrustedHost → CORS → GZip → Request ID → Timing → Structured Logging
    → Exception Handling (Starlette) → route.
    """
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(RequestIdMiddleware)
    app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_BYTES)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER, CORRELATION_ID_HEADER],
    )
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_host_list or ["*"],
    )
