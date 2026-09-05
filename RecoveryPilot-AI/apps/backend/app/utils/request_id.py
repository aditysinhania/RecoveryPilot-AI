"""Request and correlation id contextvars used by logging and envelopes."""

from __future__ import annotations

from contextvars import ContextVar

request_id_ctx: ContextVar[str] = ContextVar("request_id", default="-")
correlation_id_ctx: ContextVar[str] = ContextVar("correlation_id", default="-")
merchant_id_ctx: ContextVar[str] = ContextVar("merchant_id", default="")
recovery_case_id_ctx: ContextVar[str] = ContextVar("recovery_case_id", default="")
execution_id_ctx: ContextVar[str] = ContextVar("execution_id", default="")


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


def set_merchant_id(merchant_id: str) -> None:
    """Bind merchant_id for structured logs."""
    merchant_id_ctx.set(merchant_id)


def get_merchant_id() -> str:
    """Return merchant_id for the current task, or empty."""
    return merchant_id_ctx.get()


def set_recovery_case_id(recovery_case_id: str) -> None:
    """Bind recovery_case_id for structured logs."""
    recovery_case_id_ctx.set(recovery_case_id)


def get_recovery_case_id() -> str:
    """Return recovery_case_id for the current task, or empty."""
    return recovery_case_id_ctx.get()


def set_execution_id(execution_id: str) -> None:
    """Bind execution_id for structured logs."""
    execution_id_ctx.set(execution_id)


def get_execution_id() -> str:
    """Return execution_id for the current task, or empty."""
    return execution_id_ctx.get()
