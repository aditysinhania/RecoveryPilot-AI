"""Deterministic calendar helpers for payday, weekends, and festivals."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from services.diagnosis.constants import INDIAN_FESTIVALS_2026
from services.planner.constants import (
    CONTACT_WINDOW_END_HOUR,
    CONTACT_WINDOW_START_HOUR,
    PAYDAY_DAYS,
    PAYDAY_RETRY_HOUR,
    PAYDAY_RETRY_MINUTE,
    PAYDAY_WINDOW_END_HOUR,
)


def to_local(moment: datetime, timezone: str) -> datetime:
    """Convert ``moment`` into ``timezone``. Naive values are treated as already local."""
    tz = ZoneInfo(timezone)
    if moment.tzinfo is None:
        return moment.replace(tzinfo=tz)
    return moment.astimezone(tz)


def _festival_dates() -> set[date]:
    """Static 2026 festival calendar copied via diagnosis constants (no simulator import)."""
    return {row[0] for row in INDIAN_FESTIVALS_2026}


def is_weekend(day: date) -> bool:
    """Saturday or Sunday."""
    return day.weekday() >= 5


def is_festival(day: date) -> bool:
    """True when ``day`` is on the 2026 festival calendar."""
    return day in _festival_dates()


def is_business_day(day: date) -> bool:
    """Weekday that is not a listed festival."""
    return not is_weekend(day) and not is_festival(day)


def at_local(
    day: date,
    timezone: str,
    *,
    hour: int,
    minute: int = 0,
) -> datetime:
    """Build a timezone-aware datetime on ``day``."""
    tz = ZoneInfo(timezone)
    return datetime(day.year, day.month, day.day, hour, minute, tzinfo=tz)


def next_business_morning(
    moment: datetime,
    timezone: str,
    *,
    hour: int = PAYDAY_RETRY_HOUR,
    minute: int = PAYDAY_RETRY_MINUTE,
) -> datetime:
    """Next business-day slot at ``hour:minute`` that is not before ``moment``."""
    local = to_local(moment, timezone)
    day = local.date()
    for _ in range(0, 21):
        if is_business_day(day):
            slot = at_local(day, timezone, hour=hour, minute=minute)
            if slot >= local:
                return slot
        day = day + timedelta(days=1)
    return at_local(day, timezone, hour=hour, minute=minute)


def apply_business_window(
    moment: datetime,
    timezone: str,
    *,
    honour_exact_date: bool = False,
) -> datetime:
    """Move ``moment`` to the next valid contact window unless promised-date exact.

    Args:
        moment: Candidate schedule.
        timezone: Customer / merchant timezone.
        honour_exact_date: When True, keep the calendar date (promise-to-pay).

    Returns:
        Adjusted timestamp.
    """
    local = to_local(moment, timezone)
    if honour_exact_date:
        return local
    if not is_business_day(local.date()):
        return next_business_morning(local + timedelta(seconds=1), timezone)
    minutes = local.hour * 60 + local.minute
    start = CONTACT_WINDOW_START_HOUR * 60
    end = CONTACT_WINDOW_END_HOUR * 60
    if minutes < start:
        return local.replace(
            hour=CONTACT_WINDOW_START_HOUR, minute=0, second=0, microsecond=0
        )
    if minutes >= end:
        nxt = datetime(
            local.year, local.month, local.day, 0, 0, tzinfo=local.tzinfo
        ) + timedelta(days=1)
        return next_business_morning(nxt, timezone)
    return local


def next_payday_slot(moment: datetime, timezone: str) -> datetime:
    """Next 09:15 IST (local) inside a payday day (1st–5th), not before ``moment``.

    If ``moment`` already sits in 09:00–11:00 on a payday day, return ``moment``.
    """
    local = to_local(moment, timezone)
    day = local.date()
    for i in range(0, 40):
        candidate = day + timedelta(days=i)
        if candidate.day not in PAYDAY_DAYS:
            continue
        window_start = at_local(
            candidate, timezone, hour=PAYDAY_RETRY_HOUR, minute=0
        )
        window_end = at_local(
            candidate, timezone, hour=PAYDAY_WINDOW_END_HOUR, minute=0
        )
        slot = at_local(
            candidate,
            timezone,
            hour=PAYDAY_RETRY_HOUR,
            minute=PAYDAY_RETRY_MINUTE,
        )
        if i == 0 and window_start <= local < window_end:
            return local
        if slot >= local:
            return slot
    jan = date(local.year + 1, 1, 1)
    return at_local(jan, timezone, hour=PAYDAY_RETRY_HOUR, minute=PAYDAY_RETRY_MINUTE)


def payday_window_for(scheduled_at: datetime, timezone: str) -> tuple[datetime, datetime]:
    """09:00–11:00 on the scheduled local day."""
    local = to_local(scheduled_at, timezone)
    day = local.date()
    start = at_local(day, timezone, hour=PAYDAY_RETRY_HOUR, minute=0)
    end = at_local(day, timezone, hour=PAYDAY_WINDOW_END_HOUR, minute=0)
    return start, end


def after_cooldown(candidate: datetime, cooldown_until: datetime | None) -> datetime:
    """Raise ``candidate`` to ``cooldown_until`` when the policy wait is later."""
    if cooldown_until is None:
        return candidate
    cool = cooldown_until
    if cool.tzinfo is None and candidate.tzinfo is not None:
        cool = cool.replace(tzinfo=candidate.tzinfo)
    elif cool.tzinfo is not None and candidate.tzinfo is not None:
        cool = cool.astimezone(candidate.tzinfo)
    return candidate if candidate >= cool else cool
