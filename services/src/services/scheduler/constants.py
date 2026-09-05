"""Scheduler job statuses and queue labels. Not a PostgreSQL enum."""

from __future__ import annotations

STATUS_PENDING: str = "pending"
STATUS_RUNNING: str = "running"
STATUS_DONE: str = "done"
STATUS_CANCELLED: str = "cancelled"
STATUS_DEAD_LETTER: str = "dead_letter"

ACTIVE_STATUSES: frozenset[str] = frozenset({STATUS_PENDING, STATUS_RUNNING})
