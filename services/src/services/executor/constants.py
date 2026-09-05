"""Constants for the deterministic recovery executor."""

from __future__ import annotations

from datetime import timedelta
from uuid import UUID

EXECUTOR_VERSION: str = "recovery_executor_v1"
DEFAULT_TIMEZONE: str = "Asia/Kolkata"
ACTOR: str = "EXECUTOR_ENGINE"

# uuid5 namespace so the same case/strategy/time always hashes the same.
IDEMPOTENCY_NAMESPACE: UUID = UUID("c3d4e5f6-a7b8-9012-cdef-1234567890ab")

PAYMENT_LINK_TTL: timedelta = timedelta(hours=48)
CARD_UPDATE_TTL: timedelta = timedelta(hours=24)

# Copied from simulator recovery mix (do not import simulator).
# Cumulative buckets over 0–99 from sha256.
RETRY_OUTCOME_BUCKETS: tuple[tuple[int, str], ...] = (
    (55, "SUCCESS"),
    (70, "FAILED"),
    (82, "BANK_TIMEOUT"),
    (94, "NSF"),
    (100, "AUTH_FAILURE"),
)

STRATEGY_TO_EXECUTION: dict[str, str] = {
    "RETRY_PAYMENT": "EXECUTE_RETRY",
    "RETRY_SILENTLY": "EXECUTE_RETRY",
    "SEND_PAYMENT_LINK": "GENERATE_PAYMENT_LINK",
    "SWITCH_PAYMENT_METHOD": "SWITCH_TO_UPI",
    "REQUEST_NEW_MANDATE": "REQUEST_CARD_UPDATE",
    "WAIT_FOR_PAYDAY": "WAIT_UNTIL_TIME",
    "HONOUR_PROMISE_TO_PAY": "WAIT_UNTIL_TIME",
    "ESCALATE_TO_HUMAN": "ESCALATE_CASE",
    "STOP_RECOVERY": "STOP_EXECUTION",
}

RETRY_WEBHOOK: dict[str, tuple[str, ...]] = {
    "SUCCESS": ("payment.authorized", "payment.captured", "subscription.charged"),
    "FAILED": ("payment.failed",),
    "BANK_TIMEOUT": ("payment.failed",),
    "NSF": ("payment.failed",),
    "AUTH_FAILURE": ("payment.failed",),
}

HIGH_PROBABILITY_SUCCESS: float = 0.85
LOW_PROBABILITY_FAIL: float = 0.12

TRACE_IDEMPOTENCY: str = "idempotency_check"
TRACE_START: str = "execution_start"
TRACE_RETRY: str = "retry_creation"
TRACE_PAYMENT_LINK: str = "payment_link_creation"
TRACE_CARD_UPDATE: str = "card_update_creation"
TRACE_WAIT: str = "wait_scheduled"
TRACE_TERMINAL: str = "terminal_action"
TRACE_WEBHOOK: str = "webhook_processing"
TRACE_AUDIT: str = "audit_event_creation"
