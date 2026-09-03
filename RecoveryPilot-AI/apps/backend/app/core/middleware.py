"""ASGI middleware: request id, timing, and structured access logs."""

from __future__ import annotations

import logging
import time
from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from app.config.constants import GZIP_MINIMUM_BYTES, REQUEST_ID_HEADER
from app.config.settings import Settings
from app.utils.request_id import set_request_id
from app.utils.uuid import new_uuid_str

logger = logging.getLogger(__name__)


class RequestIdMiddleware(BaseHTTPMiddleware):
    """Assign a UUID request id and echo it on ``X-Request-ID``."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Bind request id onto the request, contextvar, and response header."""
        incoming = request.headers.get(REQUEST_ID_HEADER)
        request_id = incoming.strip() if incoming else new_uuid_str()
        request.state.request_id = request_id
        set_request_id(request_id)
        response = await call_next(request)
        response.headers[REQUEST_ID_HEADER] = request_id
        return response


class RequestTimingMiddleware(BaseHTTPMiddleware):
    """Record elapsed milliseconds on ``request.state.latency_ms``."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Time the downstream stack."""
        started = time.perf_counter()
        response = await call_next(request)
        request.state.latency_ms = round((time.perf_counter() - started) * 1000, 2)
        response.headers["X-Response-Time-Ms"] = str(request.state.latency_ms)
        return response


class StructuredLoggingMiddleware(BaseHTTPMiddleware):
    """Log method, path, status, latency, and request id as JSON fields."""

    async def dispatch(
        self,
        request: Request,
        call_next: Callable[[Request], Awaitable[Response]],
    ) -> Response:
        """Emit one access log line after the response is produced."""
        response = await call_next(request)
        latency = getattr(request.state, "latency_ms", None)
        logger.info(
            "http.request",
            extra={
                "request_id": getattr(request.state, "request_id", "-"),
                "method": request.method,
                "path": request.url.path,
                "status_code": response.status_code,
                "latency_ms": latency,
            },
        )
        return response


def register_middleware(app: FastAPI, settings: Settings) -> None:
    """Attach the middleware stack. Last ``add_middleware`` is outermost.

    Order (outer → inner): Request ID → Timing → Logging → CORS → GZip → Trusted Host.
    """
    app.add_middleware(
        TrustedHostMiddleware,
        allowed_hosts=settings.trusted_host_list or ["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=GZIP_MINIMUM_BYTES)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[REQUEST_ID_HEADER],
    )
    app.add_middleware(StructuredLoggingMiddleware)
    app.add_middleware(RequestTimingMiddleware)
    app.add_middleware(RequestIdMiddleware)
