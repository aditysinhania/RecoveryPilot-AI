"""Request and correlation id contextvars used by logging and envelopes."""

from __future__ import annotations

from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")


def set_request_id(request_id: str) -> None:
    """Bind the current request id for this asyncio task."""
    request_id_ctx.set(request_id)


def get_request_id() -> str:
    """Return the request id for the current task, or ``-`` outside a request."""
    return request_id_ctx.get()


def set_correlation_id(correlation_id: str) -> None:
    """Bind the correlation id (may equal request_id when the client omitted one)."""
    correlation_id_ctx.set(correlation_id)


def get_correlation_id() -> str:
    """Return the correlation id for the current task, or ``-`` outside a request."""
    return correlation_id_ctx.get()
