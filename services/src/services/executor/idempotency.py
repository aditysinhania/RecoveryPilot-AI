"""Stable idempotency keys for simulated executions."""

from __future__ import annotations

from datetime import datetime
from uuid import UUID, uuid5

from services.executor.constants import IDEMPOTENCY_NAMESPACE


def canonical_scheduled_at(scheduled_at: datetime) -> str:
    """ISO-8601 form used inside the key. Naive values are treated as UTC."""
    if scheduled_at.tzinfo is None:
        return scheduled_at.isoformat()
    return scheduled_at.isoformat()


def make_idempotency_key(
    recovery_case_id: UUID | None,
    strategy: str,
    scheduled_at: datetime,
) -> str:
    """Build a stable key: same case + strategy + scheduled time → same key.

    Args:
        recovery_case_id: Case id, or a placeholder when missing.
        strategy: Planner strategy value.
        scheduled_at: Plan schedule instant.

    Returns:
        Deterministic ``exec:`` key string.
    """
    case = str(recovery_case_id) if recovery_case_id is not None else "no-case"
    stamp = canonical_scheduled_at(scheduled_at)
    return f"exec:{case}:{strategy}:{stamp}"


def execution_id_for(idempotency_key: str) -> UUID:
    """uuid5 so a repeated key yields the same execution_id."""
    return uuid5(IDEMPOTENCY_NAMESPACE, idempotency_key)
