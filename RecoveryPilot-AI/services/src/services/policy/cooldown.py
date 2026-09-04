"""Retry gap, rolling retry cap, and DND window helpers. Pure functions."""

from __future__ import annotations

from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

from services.policy.constants import (
    CONTACT_WINDOW_END_HOUR,
    CONTACT_WINDOW_START_HOUR,
    MAX_RETRIES_IN_WINDOW,
    MIN_RETRY_GAP,
    RETRY_WINDOW,
)
from services.policy.models import RecoveryActionSnapshot
from shared.enums import ExecutionStatus, RecoveryActionType

_RETRY_TYPES: frozenset[RecoveryActionType] = frozenset({RecoveryActionType.RETRY_PAYMENT})
_IGNORED_STATUS: frozenset[ExecutionStatus] = frozenset(
    {ExecutionStatus.SKIPPED, ExecutionStatus.CANCELLED}
)


def to_local(moment: datetime, timezone: str) -> datetime:
    """Convert ``moment`` into ``timezone``. Naive values are treated as already local."""
    tz = ZoneInfo(timezone)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=tz)
    return moment.astimezone(tz)


def in_contact_window(
    moment: datetime,
    timezone: str,
    *,
    start_hour: int = CONTACT_WINDOW_START_HOUR,
    end_hour: int = CONTACT_WINDOW_END_HOUR,
) -> bool:
    """True when ``moment`` falls in ``[start_hour, end_hour)`` in ``timezone``."""
    local = to_local(moment, timezone)
    minutes = local.hour * 60 + local.minute
    return start_hour * 60 <= minutes < end_hour * 60


def next_contact_window_start(
    moment: datetime,
    timezone: str,
    *,
    start_hour: int = CONTACT_WINDOW_START_HOUR,
    end_hour: int = CONTACT_WINDOW_END_HOUR,
) -> datetime | None:
    """Return the next window open, or ``None`` when already inside the window."""
    if in_contact_window(moment, timezone, start_hour=start_hour, end_hour=end_hour):
        return None
    local = to_local(moment, timezone)
    today_start = local.replace(hour=start_hour, minute=0, second=0, microsecond=0)
    if local < today_start:
        return today_start
    tomorrow = local.date() + timedelta(days=1)
    return datetime(
        tomorrow.year,
        tomorrow.month,
        tomorrow.day,
        start_hour,
        0,
        0,
        tzinfo=local.tzinfo,
    )


def retry_actions(actions: list[RecoveryActionSnapshot]) -> list[RecoveryActionSnapshot]:
    """Payment-retry actions that count toward the cooldown cap."""
    counted: list[RecoveryActionSnapshot] = []
    for action in actions:
        if action.action_type not in _RETRY_TYPES:
            continue
        if action.execution_status in _IGNORED_STATUS:
            continue
        counted.append(action)
    return counted


def retry_cooldown_until(
    actions: list[RecoveryActionSnapshot],
    as_of: datetime,
    *,
    max_retries: int = MAX_RETRIES_IN_WINDOW,
    window: timedelta = RETRY_WINDOW,
    min_gap: timedelta = MIN_RETRY_GAP,
) -> tuple[datetime | None, str | None]:
    """Compute the next instant a retry is allowed.

    Args:
        actions: Prior recovery actions on the case.
        as_of: Evaluation clock.
        max_retries: Cap inside ``window``.
        window: Rolling lookback for the cap.
        min_gap: Minimum spacing after the last retry.

    Returns:
        ``(cooldown_until, reason_code)`` or ``(None, None)`` when clear.
    """
    retries = retry_actions(actions)
    times = sorted(item.event_time() for item in retries)
    candidates: list[tuple[datetime, str]] = []
    if times:
        gap_until = times[-1] + min_gap
        if as_of < gap_until:
            candidates.append((gap_until, "RETRY_COOLDOWN"))
    recent = [stamp for stamp in times if stamp > as_of - window]
    if len(recent) >= max_retries:
        cap_until = min(recent) + window
        if as_of < cap_until:
            candidates.append((cap_until, "RETRY_CAP"))
    if not candidates:
        return None, None
    until, code = max(candidates, key=lambda item: item[0])
    return until, code
