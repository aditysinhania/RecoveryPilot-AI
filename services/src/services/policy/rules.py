"""Independent policy rules. Each function inspects PolicyContext only."""

from __future__ import annotations

from datetime import datetime, time, timedelta

from services.diagnosis.models import DiagnosisCategory
from services.policy.consent import (
    consent_pending,
    consent_revoked,
    split_channels,
)
from services.policy.constants import (
    BROKEN_PROMISE_PRIORITY_BOOST,
    CHANNELS,
    EVIDENCE_ALREADY_PAID,
    EVIDENCE_CANCELLED,
    EVIDENCE_CHARGEBACK,
    EVIDENCE_CONSENT_CHANNEL,
    EVIDENCE_CONSENT_PENDING,
    EVIDENCE_CONSENT_REVOKED,
    EVIDENCE_DND,
    EVIDENCE_HARDSHIP,
    EVIDENCE_HIGH_VALUE,
    EVIDENCE_MANDATE_EXPIRED,
    EVIDENCE_MANDATE_REVOKED,
    EVIDENCE_OUTAGE,
    EVIDENCE_PROMISE_ACTIVE,
    EVIDENCE_PROMISE_BROKEN,
    EVIDENCE_PROMISE_FULFILLED,
    EVIDENCE_RETRY_CAP,
    EVIDENCE_RETRY_GAP,
    HIGH_VALUE_PRIORITY_BOOST,
    HIGH_VALUE_THRESHOLD_PAISE,
)
from services.policy.cooldown import (
    next_contact_window_start,
    retry_cooldown_until,
    to_local,
)
from services.policy.models import (
    PolicyContext,
    PolicyRuleResult,
    PromisePolicySnapshot,
    RuleVerdict,
)
from shared.enums import CustomerSegment, MandateStatus, PromiseStatus, SubscriptionStatus


def _pass(name: str, reason: str = "No blocking condition.") -> PolicyRuleResult:
    """Build a PASS result."""
    return PolicyRuleResult(
        policy_name=name,
        verdict=RuleVerdict.PASS,
        reason=reason,
        evidence_codes=[],
    )


def _active_promise(context: PolicyContext) -> PromisePolicySnapshot | None:
    """Most recently dated OPEN promise, if any."""
    open_rows = [row for row in context.promises if row.status == PromiseStatus.OPEN]
    if not open_rows:
        return None
    return max(open_rows, key=lambda row: row.promised_date)


def rule_already_paid(context: PolicyContext) -> PolicyRuleResult:
    """STOP immediately when the invoice is already settled."""
    diagnosis = context.diagnosis.diagnosis
    already = diagnosis == DiagnosisCategory.ALREADY_PAID or bool(
        context.diagnosis.features.get("already_paid_after_failure")
    )
    if not already:
        return _pass("already_paid")
    return PolicyRuleResult(
        policy_name="already_paid",
        verdict=RuleVerdict.STOP,
        reason="Successful payment exists after the failure. Never retry.",
        evidence_codes=[EVIDENCE_ALREADY_PAID],
        allowed_channels=[],
        blocked_channels=list(CHANNELS),
    )


def rule_chargeback(context: PolicyContext) -> PolicyRuleResult:
    """ESCALATE and block payment retries when a dispute is active."""
    if context.diagnosis.diagnosis != DiagnosisCategory.CHARGEBACK_ACTIVE:
        return _pass("chargeback")
    return PolicyRuleResult(
        policy_name="chargeback",
        verdict=RuleVerdict.ESCALATE,
        reason="Dispute or chargeback is active. Block payment retries and escalate.",
        evidence_codes=[EVIDENCE_CHARGEBACK],
        allowed_channels=[],
        blocked_channels=list(CHANNELS),
        manual_review_required=True,
    )


def rule_consent(context: PolicyContext) -> PolicyRuleResult:
    """STOP on withdrawn consent; DENY while pending; otherwise restrict channels."""
    allowed, blocked = split_channels(context.customer)
    if consent_revoked(context.customer):
        return PolicyRuleResult(
            policy_name="consent",
            verdict=RuleVerdict.STOP,
            reason="Customer revoked communication consent. Stop recovery outreach.",
            evidence_codes=[EVIDENCE_CONSENT_REVOKED],
            allowed_channels=[],
            blocked_channels=list(CHANNELS),
        )
    if consent_pending(context.customer):
        return PolicyRuleResult(
            policy_name="consent",
            verdict=RuleVerdict.FAIL,
            reason="Communication consent is pending. Do not contact the customer.",
            evidence_codes=[EVIDENCE_CONSENT_PENDING],
            allowed_channels=[],
            blocked_channels=list(CHANNELS),
        )
    if blocked:
        return PolicyRuleResult(
            policy_name="consent",
            verdict=RuleVerdict.PASS,
            reason=f"Outreach restricted. Blocked channels: {', '.join(blocked)}.",
            evidence_codes=[EVIDENCE_CONSENT_CHANNEL],
            allowed_channels=allowed,
            blocked_channels=blocked,
        )
    return PolicyRuleResult(
        policy_name="consent",
        verdict=RuleVerdict.PASS,
        reason="Communication consent granted for all channels.",
        evidence_codes=[],
        allowed_channels=allowed,
        blocked_channels=[],
    )


def rule_mandate(context: PolicyContext) -> PolicyRuleResult:
    """STOP when the mandate is revoked. Expired mandates stay ALLOW for a later update."""
    revoked = context.diagnosis.diagnosis == DiagnosisCategory.MANDATE_REVOKED
    status = context.subscription.mandate_status if context.subscription else None
    if revoked or status == MandateStatus.REVOKED:
        return PolicyRuleResult(
            policy_name="mandate",
            verdict=RuleVerdict.STOP,
            reason="Mandate is revoked. Stop recovery.",
            evidence_codes=[EVIDENCE_MANDATE_REVOKED],
            allowed_channels=[],
            blocked_channels=list(CHANNELS),
        )
    if status == MandateStatus.EXPIRED:
        return PolicyRuleResult(
            policy_name="mandate",
            verdict=RuleVerdict.PASS,
            reason="Mandate is expired. Mandate-update flow is allowed later.",
            evidence_codes=[EVIDENCE_MANDATE_EXPIRED],
        )
    return _pass("mandate")


def rule_promise_to_pay(context: PolicyContext) -> PolicyRuleResult:
    """WAIT on an open promise, STOP if fulfilled, ALLOW escalation if broken."""
    fulfilled = [row for row in context.promises if row.status == PromiseStatus.FULFILLED]
    if fulfilled:
        latest = max(fulfilled, key=lambda row: row.promised_date)
        return PolicyRuleResult(
            policy_name="promise_to_pay",
            verdict=RuleVerdict.STOP,
            reason=f"Promise-to-pay fulfilled (promised {latest.promised_date.isoformat()}). Stop recovery.",
            evidence_codes=[EVIDENCE_PROMISE_FULFILLED],
            allowed_channels=[],
            blocked_channels=list(CHANNELS),
        )
    local = to_local(context.as_of, context.customer.timezone)
    open_promise = _active_promise(context)
    broken_marked = [row for row in context.promises if row.status == PromiseStatus.BROKEN]
    if open_promise is not None:
        if local.date() <= open_promise.promised_date:
            resume = datetime.combine(
                open_promise.promised_date + timedelta(days=1),
                time(hour=8),
                tzinfo=local.tzinfo,
            )
            return PolicyRuleResult(
                policy_name="promise_to_pay",
                verdict=RuleVerdict.WAIT,
                reason=(
                    f"Promise-to-pay active until {open_promise.promised_date.isoformat()}."
                ),
                evidence_codes=[EVIDENCE_PROMISE_ACTIVE],
                cooldown_until=resume,
                allowed_channels=[],
                blocked_channels=list(CHANNELS),
            )
        return PolicyRuleResult(
            policy_name="promise_to_pay",
            verdict=RuleVerdict.PASS,
            reason=(
                f"Promise-to-pay broken (promised {open_promise.promised_date.isoformat()}). "
                "Planner may escalate."
            ),
            evidence_codes=[EVIDENCE_PROMISE_BROKEN],
            manual_review_required=True,
            priority_boost=BROKEN_PROMISE_PRIORITY_BOOST,
        )
    if broken_marked:
        latest = max(broken_marked, key=lambda row: row.promised_date)
        return PolicyRuleResult(
            policy_name="promise_to_pay",
            verdict=RuleVerdict.PASS,
            reason=(
                f"Promise-to-pay broken (promised {latest.promised_date.isoformat()}). "
                "Planner may escalate."
            ),
            evidence_codes=[EVIDENCE_PROMISE_BROKEN],
            manual_review_required=True,
            priority_boost=BROKEN_PROMISE_PRIORITY_BOOST,
        )
    return _pass("promise_to_pay")


def rule_retry_cooldown(context: PolicyContext) -> PolicyRuleResult:
    """WAIT when the rolling retry cap or minimum gap is still active."""
    until, code = retry_cooldown_until(context.recovery_actions, context.as_of)
    if until is None or code is None:
        return _pass("retry_cooldown")
    remaining = until - context.as_of
    hours = max(0, int(remaining.total_seconds() // 3600))
    if code == "RETRY_CAP":
        reason = (
            f"Maximum 3 retries in 7 days reached. Next retry after "
            f"{until.isoformat()}."
        )
        evidence = EVIDENCE_RETRY_CAP
    else:
        reason = f"Retry cooldown active for {hours} hours."
        evidence = EVIDENCE_RETRY_GAP
    return PolicyRuleResult(
        policy_name="retry_cooldown",
        verdict=RuleVerdict.WAIT,
        reason=reason,
        evidence_codes=[evidence],
        cooldown_until=until,
        silent_retry_allowed=True,
    )


def rule_outage(context: PolicyContext) -> PolicyRuleResult:
    """WAIT on rail timeouts. Silent retry later; do not notify immediately."""
    diagnosis = context.diagnosis.diagnosis
    if diagnosis not in {DiagnosisCategory.BANK_TIMEOUT, DiagnosisCategory.UPI_TIMEOUT}:
        return _pass("outage")
    return PolicyRuleResult(
        policy_name="outage",
        verdict=RuleVerdict.WAIT,
        reason=(
            f"Diagnosis is {diagnosis.value}. Wait for the rail to recover. "
            "Silent retry is allowed later; do not notify the customer now."
        ),
        evidence_codes=[EVIDENCE_OUTAGE],
        allowed_channels=[],
        blocked_channels=list(CHANNELS),
        silent_retry_allowed=True,
    )


def rule_dnd_contact(context: PolicyContext) -> PolicyRuleResult:
    """WAIT outside the 08:00–19:00 contact window in the customer timezone."""
    tz_name = context.customer.timezone
    nxt = next_contact_window_start(context.as_of, tz_name)
    if nxt is None:
        return _pass("dnd_contact")
    local = to_local(context.as_of, tz_name)
    return PolicyRuleResult(
        policy_name="dnd_contact",
        verdict=RuleVerdict.WAIT,
        reason=(
            f"Outside allowed contact window (08:00–19:00 {tz_name}). "
            f"Current local time is {local.strftime('%H:%M')}."
        ),
        evidence_codes=[EVIDENCE_DND],
        cooldown_until=nxt,
        allowed_channels=[],
        blocked_channels=list(CHANNELS),
        silent_retry_allowed=True,
    )


def rule_churn_protection(context: PolicyContext) -> PolicyRuleResult:
    """STOP on cancellation. ESCALATE on hardship instead of repeating recovery."""
    cancelled = context.diagnosis.diagnosis == DiagnosisCategory.CUSTOMER_CANCELLED
    sub_cancelled = (
        context.subscription is not None
        and context.subscription.subscription_status == SubscriptionStatus.CANCELLED
    )
    if cancelled or sub_cancelled:
        return PolicyRuleResult(
            policy_name="churn_protection",
            verdict=RuleVerdict.STOP,
            reason="Customer cancelled the subscription. Stop recovery.",
            evidence_codes=[EVIDENCE_CANCELLED],
            allowed_channels=[],
            blocked_channels=list(CHANNELS),
        )
    if context.customer.hardship:
        return PolicyRuleResult(
            policy_name="churn_protection",
            verdict=RuleVerdict.ESCALATE,
            reason="Hardship flag is set. Escalate instead of repeating recovery.",
            evidence_codes=[EVIDENCE_HARDSHIP],
            allowed_channels=[],
            blocked_channels=list(CHANNELS),
            manual_review_required=True,
        )
    return _pass("churn_protection")


def rule_high_value(context: PolicyContext) -> PolicyRuleResult:
    """ALLOW an escalation path and raise planner priority for HIGH_VALUE invoices."""
    amount = context.payment.amount
    high = context.customer.segment == CustomerSegment.HIGH_VALUE
    if not high or amount < HIGH_VALUE_THRESHOLD_PAISE:
        return _pass("high_value")
    return PolicyRuleResult(
        policy_name="high_value",
        verdict=RuleVerdict.PASS,
        reason=(
            "HIGH_VALUE customer above the amount threshold. "
            "Escalation path allowed; planner priority increased."
        ),
        evidence_codes=[EVIDENCE_HIGH_VALUE],
        manual_review_required=True,
        priority_boost=HIGH_VALUE_PRIORITY_BOOST,
    )
