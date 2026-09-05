"""Strategy-aware schedule: payday, outage, promise, cooldown, business window."""

from __future__ import annotations

from datetime import timedelta

from services.planner.constants import (
    OUTAGE_RETRY_DELAY,
    OUTAGE_RETRY_WINDOW,
    PLAN_TTL,
    PROMISE_HOUR,
    PROMISE_MINUTE,
)
from services.planner.models import PlannerContext, PlannerStrategy, RetryWindow, ScheduleResult
from services.planner.timing import (
    after_cooldown,
    apply_business_window,
    at_local,
    next_payday_slot,
    payday_window_for,
    to_local,
)


def _month_name(moment, timezone: str) -> str:
    """Short month + day for human timing reasons (e.g. Sept 2)."""
    local = to_local(moment, timezone)
    month = local.strftime("%b").replace("Sep", "Sept")
    return f"{month} {local.day}"


def schedule(strategy: PlannerStrategy, context: PlannerContext) -> ScheduleResult:
    """Compute scheduled_at, retry window, and a timing reason.

    Args:
        strategy: Chosen primary strategy.
        context: Planner snapshots including policy cooldown.

    Returns:
        Deterministic schedule. Nothing is written to a job queue.
    """
    tz = context.timezone
    as_of = context.as_of
    cooldown = context.policy.cooldown_until

    if strategy == PlannerStrategy.STOP_RECOVERY:
        return ScheduleResult(
            scheduled_at=as_of,
            retry_window=None,
            expires_at=None,
            timing_reason="Stop immediately. No retry window.",
        )

    if strategy == PlannerStrategy.ESCALATE_TO_HUMAN:
        when = apply_business_window(after_cooldown(as_of, cooldown), tz)
        return ScheduleResult(
            scheduled_at=when,
            retry_window=None,
            expires_at=when + PLAN_TTL,
            timing_reason="Escalate as soon as the contact window is open.",
        )

    if strategy == PlannerStrategy.HONOUR_PROMISE_TO_PAY and context.promised_date is not None:
        slot = at_local(
            context.promised_date, tz, hour=PROMISE_HOUR, minute=PROMISE_MINUTE
        )
        slot = after_cooldown(slot, cooldown)
        slot = apply_business_window(slot, tz, honour_exact_date=True)
        start = at_local(context.promised_date, tz, hour=8, minute=0)
        end = at_local(context.promised_date, tz, hour=19, minute=0)
        return ScheduleResult(
            scheduled_at=slot,
            retry_window=RetryWindow(
                start=start,
                end=end,
                label=f"Promised date {context.promised_date.isoformat()} 08:00–19:00",
            ),
            expires_at=end,
            timing_reason=(
                f"Schedule exactly on promised payment date "
                f"{context.promised_date.isoformat()} at {slot.strftime('%H:%M')}."
            ),
        )

    if strategy == PlannerStrategy.WAIT_FOR_PAYDAY:
        anchor = after_cooldown(as_of, cooldown)
        first = next_payday_slot(anchor, tz)
        first = apply_business_window(first, tz)
        first = next_payday_slot(first, tz)
        win_start, win_end = payday_window_for(first, tz)
        cool_txt = ""
        if cooldown is not None:
            cool_local = to_local(cooldown, tz)
            cool_txt = (
                f" and retry cooldown expires {_month_name(cool_local, tz)} "
                f"{cool_local.strftime('%H:%M')}"
            )
        hours = context.behaviour.pays_within_hours_of_salary
        reason = (
            f"Wait until {_month_name(first, tz)} {first.strftime('%H:%M')} because "
            f"customer historically pays within {hours}h of salary credit{cool_txt}."
        )
        return ScheduleResult(
            scheduled_at=first,
            retry_window=RetryWindow(
                start=win_start,
                end=win_end,
                label="Payday 09:00–11:00 IST",
            ),
            expires_at=first + PLAN_TTL,
            timing_reason=reason,
        )

    if strategy == PlannerStrategy.RETRY_SILENTLY:
        end = context.outage_ended_at or as_of
        raw = end + OUTAGE_RETRY_DELAY
        raw = after_cooldown(raw, cooldown)
        when = apply_business_window(raw, tz)
        delay_min = int(OUTAGE_RETRY_DELAY.total_seconds() // 60)
        return ScheduleResult(
            scheduled_at=when,
            retry_window=RetryWindow(
                start=when,
                end=when + OUTAGE_RETRY_WINDOW,
                label=f"Silent retry {delay_min}–90 minutes after outage end",
            ),
            expires_at=when + PLAN_TTL,
            timing_reason=(
                f"Silent retry {delay_min} minutes after outage end "
                f"({to_local(when, tz).strftime('%Y-%m-%d %H:%M %Z')})."
            ),
        )

    # RETRY_PAYMENT, SEND_PAYMENT_LINK, SWITCH, REQUEST_NEW_MANDATE
    when = after_cooldown(as_of, cooldown)
    when = apply_business_window(when, tz)
    label = "Next contact window 08:00–19:00"
    if cooldown is not None:
        label = "After policy cooldown, inside contact window"
    return ScheduleResult(
        scheduled_at=when,
        retry_window=RetryWindow(
            start=when,
            end=when + timedelta(hours=4),
            label=label,
        ),
        expires_at=when + PLAN_TTL,
        timing_reason=(
            f"Schedule at {to_local(when, tz).strftime('%Y-%m-%d %H:%M %Z')} "
            "respecting cooldown and the business contact window."
        ),
    )
