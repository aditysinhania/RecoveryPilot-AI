"""Request-id contextvar used by logging and response envelopes."""

from __future__ import annotations

from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")


def set_request_id(request_id: str) -> None:
    """Bind the current request id for this asyncio task."""
    request_id_ctx.set(request_id)


def get_request_id() -> str:
    """Return the request id for the current task, or ``-`` outside a request."""
    return request_id_ctx.get()
