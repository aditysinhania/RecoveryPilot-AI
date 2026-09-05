"""Feature extractors for the diagnosis engine. Pure functions, no I/O."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

from services.diagnosis.constants import (
    DUPLICATE_WINDOW_HOURS,
    INDIAN_FESTIVALS_2026,
    PAYDAY_DAYS,
    PRE_PAYDAY_DAYS,
    SALARY_DEPENDENT_SEGMENTS,
    TIER_ELITE_PAISE,
    TIER_PREMIUM_PAISE,
    TIER_PRO_PAISE,
)
from services.diagnosis.models import (
    DiagnosisContext,
    DiagnosisFeatures,
    OutageWindow,
    PaymentSnapshot,
)
from shared.enums import (
    FailureReason,
    MandateStatus,
    PaymentMethod,
    PaymentStatus,
    PromiseStatus,
    SubscriptionStatus,
)

_SUCCESS_STATUSES = frozenset(
    {PaymentStatus.CAPTURED, PaymentStatus.RECOVERED, PaymentStatus.AUTHORIZED}
)
_UPI_METHODS = frozenset({PaymentMethod.UPI, PaymentMethod.MANDATE})
_CARD_METHODS = frozenset({PaymentMethod.CARD, PaymentMethod.EMI})
_BANK_METHODS = frozenset({PaymentMethod.NETBANKING})


def _local(moment: datetime, tz: ZoneInfo) -> datetime:
    """Normalize a timestamp into the merchant timezone."""
    if moment.tzinfo is None:
        return moment.replace(tzinfo=tz)
    return moment.astimezone(tz)


def festival_on(moment: datetime, tz: ZoneInfo) -> tuple[date, str, str] | None:
    """Return the festival tuple if ``moment`` falls on a listed calendar day."""
    local_day = _local(moment, tz).date()
    for fest_date, name, effect in INDIAN_FESTIVALS_2026:
        if fest_date == local_day:
            return fest_date, name, effect
    return None


def days_until_payday(moment: datetime, tz: ZoneInfo) -> int:
    """Days until the next 1st-of-month payday window. Zero if already in it."""
    local_day = _local(moment, tz).date()
    if local_day.day in PAYDAY_DAYS:
        return 0
    if local_day.month == 12:
        next_pay = date(local_day.year + 1, 1, 1)
    else:
        next_pay = date(local_day.year, local_day.month + 1, 1)
    return (next_pay - local_day).days


def subscription_tier(plan_name: str | None, billing_amount: int | None) -> str:
    """Infer Starter / Pro / Elite / Premium from plan name or paise."""
    name = (plan_name or "").lower()
    if "premium" in name:
        return "Premium"
    if "elite" in name:
        return "Elite"
    if "pro" in name:
        return "Pro"
    if "starter" in name:
        return "Starter"
    amount = billing_amount or 0
    if amount >= TIER_PREMIUM_PAISE:
        return "Premium"
    if amount >= TIER_ELITE_PAISE:
        return "Elite"
    if amount >= TIER_PRO_PAISE:
        return "Pro"
    return "Starter"


def matching_outage(
    moment: datetime, method: PaymentMethod | None, outages: list[OutageWindow]
) -> OutageWindow | None:
    """Return the first outage whose rail matches the payment method."""
    if method is None:
        return None
    if method in _UPI_METHODS:
        rail = "UPI"
    elif method in _CARD_METHODS:
        rail = "CARD"
    elif method in _BANK_METHODS:
        rail = "NETBANKING"
    else:
        rail = str(method)
    for outage in outages:
        if outage.contains(moment) and outage.rail.upper() == rail:
            return outage
    return None


def _is_success(status: PaymentStatus) -> bool:
    """True when the attempt collected or authorized funds."""
    return status in _SUCCESS_STATUSES


def already_paid_after_failure(
    failed: PaymentSnapshot, others: list[PaymentSnapshot]
) -> bool:
    """True if a later successful payment covers the same invoice."""
    for other in others:
        if other.id == failed.id:
            continue
        marker = other.paid_at or other.created_at
        if marker <= failed.created_at:
            continue
        if not _is_success(other.status):
            continue
        same_sub = (
            failed.subscription_id is not None
            and other.subscription_id == failed.subscription_id
        )
        same_amount = other.amount == failed.amount
        if same_sub or same_amount:
            return True
    return False


def duplicate_captured(
    failed: PaymentSnapshot, others: list[PaymentSnapshot]
) -> bool:
    """True if another capture exists in the duplicate window for the same invoice."""
    window = timedelta(hours=DUPLICATE_WINDOW_HOURS)
    for other in others:
        if other.id == failed.id:
            continue
        if not _is_success(other.status):
            continue
        delta = abs(other.created_at - failed.created_at)
        same_key = (
            failed.idempotency_key
            and other.idempotency_key
            and failed.idempotency_key == other.idempotency_key
        )
        same_invoice = other.amount == failed.amount and (
            other.due_date == failed.due_date
            or other.subscription_id == failed.subscription_id
        )
        if (same_key or same_invoice) and delta <= window:
            return True
    return False


def extract_features(context: DiagnosisContext) -> DiagnosisFeatures:
    """Build the typed feature object used by rules and scorers.

    Args:
        context: Snapshots collected by the service layer or a test fixture.

    Returns:
        ``DiagnosisFeatures`` with calendar, history, and rail flags.
    """
    tz = ZoneInfo(context.timezone)
    payment = context.payment
    failed_at = _local(payment.created_at, tz)
    as_of = _local(context.as_of, tz)
    others = [row for row in context.customer_payments if row.id != payment.id]
    prior = [row for row in others if row.created_at < payment.created_at]
    successes = [row for row in prior if _is_success(row.status)]
    prior_count = len(prior)
    success_rate = (len(successes) / prior_count) if prior_count else 0.0
    outage = matching_outage(payment.created_at, payment.method, context.outages)
    fest = festival_on(payment.created_at, tz)
    due = payment.due_date
    days_overdue = 0
    if due is not None:
        days_overdue = max(0, (as_of.date() - due).days)
    else:
        days_overdue = max(0, (as_of.date() - failed_at.date()).days)
    calendar_day = failed_at.day
    plan = context.subscription.name if context.subscription else None
    billing = context.subscription.billing_amount if context.subscription else payment.amount
    mandate = context.subscription.mandate_status if context.subscription else None
    sub_status = context.subscription.subscription_status if context.subscription else None
    salary = context.customer.salary_dependent or (
        context.customer.segment.value in SALARY_DEPENDENT_SEGMENTS
    )
    retry_count = max(0, payment.attempt_number - 1) + context.recovery_action_count
    method = payment.method
    return DiagnosisFeatures(
        days_since_failure=max(0, (as_of.date() - failed_at.date()).days),
        days_until_payday=days_until_payday(payment.created_at, tz),
        days_overdue=days_overdue,
        retry_count=retry_count,
        payment_method=method,
        customer_segment=context.customer.segment,
        mandate_status=mandate,
        subscription_plan=plan,
        subscription_tier=subscription_tier(plan, billing),
        payment_amount=payment.amount,
        outage_detected=outage is not None,
        outage_rail=outage.rail if outage else None,
        outage_summary=outage.summary if outage else None,
        previous_success_rate=round(success_rate, 4),
        previous_success_count=len(successes),
        previous_attempt_count=prior_count,
        promise_pending=any(row.status == PromiseStatus.OPEN for row in context.promises),
        weekend_payment=failed_at.weekday() >= 5,
        festival_period=fest is not None,
        festival_name=fest[1] if fest else None,
        salary_dependent=salary,
        calendar_day=calendar_day,
        pre_payday_window=calendar_day in PRE_PAYDAY_DAYS,
        payday_window=calendar_day in PAYDAY_DAYS,
        recorded_failure_reason=payment.failure_reason,
        already_paid_after_failure=already_paid_after_failure(payment, others),
        duplicate_captured=duplicate_captured(payment, others),
        dispute_signal=payment.failure_reason == FailureReason.DISPUTE,
        mandate_revoked=mandate == MandateStatus.REVOKED,
        subscription_cancelled=sub_status == SubscriptionStatus.CANCELLED,
        card_method=method in _CARD_METHODS if method else False,
        upi_method=method in _UPI_METHODS if method else False,
    )
