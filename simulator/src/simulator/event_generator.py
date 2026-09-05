"""In-memory FitLife ecosystem: customers, invoices, journeys, metrics."""

from __future__ import annotations

import calendar
import json
import logging
from datetime import datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from simulator.config import GeneratorConfig, deterministic_uuid
from simulator.distributions import (
    OutageWindow,
    SeededRNG,
    apply_festival_failure_bias,
    build_outages,
    calendar_day,
    cluster_failures_for_persistence,
    customer_uuid,
    indian_name,
    indian_mobile,
    INDIAN_FESTIVALS_2026,
    is_salary_dependent,
    is_weekend,
    latent_pay_discipline,
    mandate_for_segment,
    matching_outage,
    method_for_segment,
    payday_recovery_boost,
    plan_for_segment,
    razorpay_id,
    salary_nsf_bias,
    slug_email,
)

logger = logging.getLogger(__name__)

DIAGNOSIS_CONFIDENCE: dict[str, tuple[float, float]] = {
    "INSUFFICIENT_FUNDS": (0.82, 0.06),
    "UPI_FAILURE": (0.78, 0.07),
    "BANK_TIMEOUT": (0.76, 0.07),
    "CARD_EXPIRED": (0.88, 0.04),
    "MANDATE_REVOKED": (0.91, 0.03),
    "CUSTOMER_CANCELLED": (0.84, 0.05),
    "ALREADY_PAID": (0.93, 0.03),
    "DISPUTE": (0.80, 0.06),
    "UNKNOWN": (0.42, 0.10),
}


def _iso(moment: datetime | None) -> str | None:
    """Serialize a timezone-aware datetime."""
    if moment is None:
        return None
    return moment.isoformat()


def generate_merchant(cfg: GeneratorConfig) -> dict[str, Any]:
    """Single FitLife Gym merchant row."""
    now = cfg.as_of
    created = cfg.window_start - timedelta(days=400)
    return {
        "id": str(cfg.merchant_id),
        "merchant_name": cfg.merchant_name,
        "business_category": cfg.business_category,
        "email": cfg.merchant_email,
        "phone": cfg.merchant_phone,
        "razorpay_account_id": cfg.razorpay_account_id,
        "timezone": cfg.timezone,
        "created_at": _iso(created),
        "updated_at": _iso(now),
    }


def generate_customers(cfg: GeneratorConfig, rng: SeededRNG) -> list[dict[str, Any]]:
    """Weighted personas with Indian names, Bangalore mobiles, and channel consent."""
    tz = ZoneInfo(cfg.timezone)
    rows: list[dict[str, Any]] = []
    for index in range(cfg.n_customers):
        segment = rng.weighted(cfg.segment_weights)
        name = indian_name(rng)
        language = rng.weighted(cfg.language_weights)
        whatsapp = rng.chance(0.82 if segment != "CHURN_RISK" else 0.45)
        sms = rng.chance(0.70)
        voice = rng.chance(0.25 if segment in {"HIGH_VALUE", "AT_RISK"} else 0.12)
        if whatsapp or sms or voice:
            consent = "GRANTED"
        elif segment == "CHURN_RISK" and rng.chance(0.4):
            consent = "WITHDRAWN"
        else:
            consent = "PENDING"
        created = cfg.window_start - timedelta(days=rng.randint(10, 700))
        cid = customer_uuid(cfg, index)
        rows.append(
            {
                "id": str(cid),
                "merchant_id": str(cfg.merchant_id),
                "full_name": name,
                "email": slug_email(name, index),
                "phone": indian_mobile(rng),
                "customer_segment": segment,
                "preferred_payment_method": method_for_segment(segment, cfg, rng),
                "preferred_language": language,
                "consent_status": consent,
                "consent_whatsapp": whatsapp,
                "consent_sms": sms,
                "consent_voice": voice,
                "salary_dependent": is_salary_dependent(segment, rng),
                "created_at": _iso(created.astimezone(tz) if created.tzinfo else created),
                "updated_at": _iso(cfg.as_of),
            }
        )
    logger.info("generator.customers", extra={"count": len(rows)})
    return rows


def _add_calendar_months(moment: datetime, months: int, bill_day: int) -> datetime:
    """Advance `months` calendar months, clamped to a valid billing day."""
    month_index = moment.month - 1 + months
    year = moment.year + month_index // 12
    month = month_index % 12 + 1
    day = min(bill_day, calendar.monthrange(year, month)[1], 28)
    return moment.replace(year=year, month=month, day=day, hour=7, minute=12, second=0)


def _billing_dates(
    started: datetime,
    frequency: str,
    bill_day: int,
    window_start: datetime,
    as_of: datetime,
) -> list[datetime]:
    """Invoice timestamps inside the observation window using calendar months."""
    step = {"MONTHLY": 1, "QUARTERLY": 3, "YEARLY": 12}.get(frequency, 1)
    cursor = _add_calendar_months(started, 0, bill_day)
    safety = 0
    while cursor < window_start and safety < 48:
        cursor = _add_calendar_months(cursor, step, bill_day)
        safety += 1
    dates: list[datetime] = []
    safety = 0
    while cursor <= as_of and safety < 24:
        dates.append(cursor)
        cursor = _add_calendar_months(cursor, step, bill_day)
        safety += 1
    return dates


def generate_subscriptions(
    cfg: GeneratorConfig,
    rng: SeededRNG,
    customers: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Primary plans plus renewal/upgrade history to hit the subscription target."""
    tz = ZoneInfo(cfg.timezone)
    rows: list[dict[str, Any]] = []
    sub_index = 0

    def add_sub(customer: dict[str, Any], plan: str, status: str, mandate: str) -> dict[str, Any]:
        nonlocal sub_index
        freq = rng.weighted(cfg.frequency_weights)
        bill_day = rng.randint(1, 28)
        started = cfg.window_start - timedelta(days=rng.randint(20, 500))
        sid = deterministic_uuid(cfg.seed, "subscription", str(sub_index))
        amount = cfg.plan_paise[plan]
        next_bill = (cfg.as_of + timedelta(days=rng.randint(1, 28))).date().isoformat()
        row = {
            "id": str(sid),
            "customer_id": customer["id"],
            "merchant_id": str(cfg.merchant_id),
            "subscription_name": f"{cfg.plan_brand} {plan}",
            "plan_name": plan,
            "billing_amount": amount,
            "billing_frequency": freq,
            "billing_day": bill_day,
            "next_billing_date": next_bill,
            "mandate_status": mandate,
            "subscription_status": status,
            "started_at": _iso(started.astimezone(tz)),
            "renewal_count": max(0, (cfg.as_of.year - started.year) * 12 + cfg.as_of.month - started.month),
            "created_at": _iso(started.astimezone(tz)),
            "updated_at": _iso(cfg.as_of),
        }
        rows.append(row)
        sub_index += 1
        return row

    for customer in customers:
        plan = plan_for_segment(customer["customer_segment"], cfg, rng)
        mandate = mandate_for_segment(customer["customer_segment"], rng)
        status = "ACTIVE"
        if mandate == "REVOKED":
            status = "CANCELLED"
        elif mandate == "PAUSED":
            status = "PAUSED"
        elif mandate == "EXPIRED":
            status = "PAST_DUE"
        add_sub(customer, plan, status, mandate)

    extra_needed = cfg.n_subscriptions - len(rows)
    for extra in range(max(0, extra_needed)):
        customer = customers[extra % len(customers)]
        add_sub(
            customer,
            plan_for_segment(customer["customer_segment"], cfg, rng),
            "COMPLETED" if rng.chance(0.55) else "CANCELLED",
            "EXPIRED" if rng.chance(0.5) else "REVOKED",
        )
    logger.info("generator.subscriptions", extra={"count": len(rows)})
    return rows


def _pick_failure_reason(
    cfg: GeneratorConfig,
    rng: SeededRNG,
    due: datetime,
    method: str,
    salary_dependent: bool,
    outages: list[OutageWindow],
) -> str:
    """Failure cause from weights, biased by payday and rail outages."""
    tz = ZoneInfo(cfg.timezone)
    outage = matching_outage(due, method, outages)
    if outage is not None:
        return outage.failure_reason
    weights = dict(cfg.failure_weights)
    day = calendar_day(due, tz)
    if salary_dependent:
        weights["INSUFFICIENT_FUNDS"] *= salary_nsf_bias(day)
    if method == "UPI":
        weights["UPI_FAILURE"] *= 1.4
        weights["CARD_EXPIRED"] *= 0.2
    if method == "CARD":
        weights["CARD_EXPIRED"] *= 1.6
        weights["UPI_FAILURE"] *= 0.4
    if is_weekend(due, tz):
        weights["UPI_FAILURE"] *= 1.25
        weights["BANK_TIMEOUT"] *= 1.2
    weights = apply_festival_failure_bias(
        weights, due, tz, cfg.enable_festival_calendar
    )
    return rng.weighted(weights)


def _assign_journey(
    reason: str,
    segment: str,
    salary_dependent: bool,
    rng: SeededRNG,
) -> str:
    """Map diagnosis + persona to a bounded journey. Recovery is not a coin flip."""
    if reason == "ALREADY_PAID":
        return "D_ALREADY_PAID"
    if reason in {"MANDATE_REVOKED", "CUSTOMER_CANCELLED"}:
        return "C_STOP"
    if reason == "DISPUTE":
        return "C_ESCALATE"
    if reason == "INSUFFICIENT_FUNDS" and salary_dependent:
        if segment == "CHURN_RISK":
            return "B_PROMISE"
        return "A_PAYDAY"
    if reason == "CARD_EXPIRED":
        return "A_SWITCH"
    if reason in {"UPI_FAILURE", "BANK_TIMEOUT"}:
        return "A_RETRY"
    if segment == "CHURN_RISK":
        return "B_PROMISE"
    if segment == "HIGH_VALUE":
        return "A_RETRY"
    return "B_PROMISE" if rng.chance(0.22) else "A_RETRY"


def generate_first_payments(
    cfg: GeneratorConfig,
    rng: SeededRNG,
    customers: list[dict[str, Any]],
    subscriptions: list[dict[str, Any]],
    outages: list[OutageWindow],
) -> list[dict[str, Any]]:
    """First-attempt invoices across the 90-day window."""
    tz = ZoneInfo(cfg.timezone)
    by_customer = {row["id"]: row for row in customers}
    payments: list[dict[str, Any]] = []
    pay_index = 0
    active_subs = list(subscriptions)
    for sub in active_subs:
        customer = by_customer[sub["customer_id"]]
        started = datetime.fromisoformat(str(sub["started_at"]))
        dues = _billing_dates(
            started,
            sub["billing_frequency"],
            int(sub["billing_day"]),
            cfg.window_start,
            cfg.as_of,
        )
        method = customer["preferred_payment_method"]
        for due in dues:
            local_due = due if due.tzinfo else due.replace(tzinfo=tz)
            pid = deterministic_uuid(cfg.seed, "payment", str(pay_index))
            payments.append(
                {
                    "id": str(pid),
                    "merchant_id": str(cfg.merchant_id),
                    "customer_id": customer["id"],
                    "subscription_id": sub["id"],
                    "razorpay_order_id": razorpay_id(cfg.seed, "order", str(pay_index)),
                    "razorpay_payment_id": razorpay_id(cfg.seed, "pay", str(pay_index)),
                    "idempotency_key": f"{cfg.idempotency_prefix}:{sub['id']}:{local_due.date().isoformat()}:1",
                    "payment_status": "CAPTURED",
                    "failure_reason": None,
                    "payment_method": method,
                    "amount": sub["billing_amount"],
                    "currency": "INR",
                    "attempt_number": 1,
                    "payment_due_date": local_due.date().isoformat(),
                    "payment_time": _iso(local_due + timedelta(minutes=rng.randint(1, 40))),
                    "paid_at": _iso(local_due + timedelta(minutes=rng.randint(2, 90))),
                    "created_at": _iso(local_due),
                    "updated_at": _iso(local_due + timedelta(minutes=5)),
                    "plan_name": sub["plan_name"],
                    "salary_dependent": customer["salary_dependent"],
                    "segment": customer["customer_segment"],
                    "is_original_failure": False,
                }
            )
            pay_index += 1

    rng.random.shuffle(payments)
    logger.info("generator.first_payments", extra={"count": len(payments)})
    return payments


def mark_failures(
    cfg: GeneratorConfig,
    rng: SeededRNG,
    payments: list[dict[str, Any]],
    outages: list[OutageWindow],
) -> list[dict[str, Any]]:
    """Flip exactly n_failed_payments rows to FAILED with weighted reasons."""
    tz = ZoneInfo(cfg.timezone)
    candidates = [row for row in payments if row["attempt_number"] == 1]
    rng.random.shuffle(candidates)
    if cfg.enable_behaviour_persistence:
        candidates = cluster_failures_for_persistence(candidates, cfg.n_failed_payments)
    failed = candidates[: cfg.n_failed_payments]
    failed_ids = {row["id"] for row in failed}
    for row in payments:
        if row["id"] not in failed_ids:
            continue
        due = datetime.fromisoformat(str(row["created_at"]))
        method = str(row["payment_method"])
        reason = _pick_failure_reason(
            cfg,
            rng,
            due,
            method,
            bool(row["salary_dependent"]),
            outages,
        )
        row["payment_status"] = "FAILED"
        row["failure_reason"] = reason
        row["paid_at"] = None
        row["is_original_failure"] = True
        if matching_outage(due, method, outages) is not None:
            row["failure_reason"] = matching_outage(due, method, outages).failure_reason  # type: ignore[union-attr]
        if is_weekend(due, tz) and reason == "INSUFFICIENT_FUNDS":
            row["updated_at"] = _iso(due + timedelta(minutes=8))
    logger.info("generator.failures", extra={"count": cfg.n_failed_payments})
    return [row for row in payments if row["is_original_failure"]]


def _priority(segment: str, amount: int, reason: str) -> float:
    """Deterministic priority used by the recovery queue."""
    base = {
        "HIGH_VALUE": 0.92,
        "LOYAL": 0.74,
        "ACTIVE": 0.62,
        "NEW": 0.55,
        "AT_RISK": 0.70,
        "CHURN_RISK": 0.48,
    }[segment]
    amount_boost = min(0.08, amount / 2_500_000)
    dispute = 0.05 if reason == "DISPUTE" else 0.0
    return round(min(0.99, base + amount_boost + dispute), 4)


def generate_recovery(
    cfg: GeneratorConfig,
    rng: SeededRNG,
    failed_payments: list[dict[str, Any]],
    outages: list[OutageWindow],
) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    """Build cases, actions, promises, audit rows, and optional retry payments."""
    tz = ZoneInfo(cfg.timezone)
    cases: list[dict[str, Any]] = []
    actions: list[dict[str, Any]] = []
    promises: list[dict[str, Any]] = []
    audits: list[dict[str, Any]] = []
    retries: list[dict[str, Any]] = []
    promise_target = cfg.n_promises
    promise_count = 0
    action_i = 0
    audit_i = 0
    retry_i = 0

    def add_audit(
        case_id: str,
        at: datetime,
        actor_type: str,
        actor_name: str,
        event_type: str,
        summary: str,
        payload: dict[str, Any],
        decision: str | None,
    ) -> None:
        nonlocal audit_i
        audits.append(
            {
                "id": str(deterministic_uuid(cfg.seed, "audit", str(audit_i))),
                "recovery_case_id": case_id,
                "actor_type": actor_type,
                "actor_name": actor_name,
                "event_type": event_type,
                "event_summary": summary,
                "structured_payload": json.dumps(payload, sort_keys=True),
                "policy_decision": decision,
                "created_at": _iso(at),
            }
        )
        audit_i += 1

    def add_action(
        case_id: str,
        action_type: str,
        scheduled: datetime,
        executed: datetime | None,
        status: str,
        retry_number: int,
        metadata: dict[str, Any],
        link: str | None = None,
    ) -> None:
        nonlocal action_i
        actions.append(
            {
                "id": str(deterministic_uuid(cfg.seed, "action", str(action_i))),
                "recovery_case_id": case_id,
                "action_type": action_type,
                "scheduled_time": _iso(scheduled),
                "executed_time": _iso(executed),
                "execution_status": status,
                "razorpay_payment_link": link,
                "retry_number": retry_number,
                "response_code": "OK" if status == "SUCCEEDED" else "SKIPPED",
                "response_message": metadata.get("retry_reason", action_type),
                "action_metadata": json.dumps(metadata, sort_keys=True),
                "created_at": _iso(scheduled),
            }
        )
        action_i += 1

    for fail_i, payment in enumerate(failed_payments):
        failed_at = datetime.fromisoformat(str(payment["created_at"]))
        reason = str(payment["failure_reason"])
        segment = str(payment["segment"])
        salary_dep = bool(payment["salary_dependent"])
        journey = _assign_journey(reason, segment, salary_dep, rng)
        if journey == "B_PROMISE" and promise_count >= promise_target:
            journey = "A_RETRY"
        if journey == "B_PROMISE":
            promise_count += 1
        elif promise_count < promise_target and reason == "INSUFFICIENT_FUNDS":
            journey = "B_PROMISE"
            promise_count += 1

        mean, sigma = DIAGNOSIS_CONFIDENCE[reason]
        confidence = round(rng.gauss_clip(mean, sigma, 0.2, 0.99), 4)
        diagnosed_at = failed_at + timedelta(minutes=rng.randint(4, 40))
        case_id = str(deterministic_uuid(cfg.seed, "case", payment["id"]))
        started = diagnosed_at
        completed: datetime | None = None
        status = "DIAGNOSED"
        recovered = False
        suppressed = False
        escalated = False

        add_audit(
            case_id,
            failed_at + timedelta(minutes=1),
            "SYSTEM",
            "Razorpay Webhook",
            "CASE_OPENED",
            f"Opened recovery for failed {payment['razorpay_payment_id']}",
            {"payment_id": payment["id"], "failure_reason": reason, "event": "payment.failed"},
            None,
        )
        add_audit(
            case_id,
            diagnosed_at,
            "AI_AGENT",
            "Diagnosis Agent",
            "DIAGNOSIS_COMPLETED",
            f"Diagnosed {reason} via {cfg.diagnosis_model}",
            {
                "diagnosed_reason": reason,
                "model": cfg.diagnosis_model,
                "version": cfg.diagnosis_version,
                "confidence": confidence,
            },
            None,
        )

        if journey == "D_ALREADY_PAID":
            policy = "BLOCK"
            status = "CLOSED"
            suppressed = True
            completed = diagnosed_at + timedelta(minutes=2)
            add_action(
                case_id,
                "NO_ACTION",
                diagnosed_at,
                completed,
                "SKIPPED",
                0,
                {"retry_reason": "already_paid", "scheduler_id": "sched_none"},
            )
            add_audit(
                case_id,
                diagnosed_at + timedelta(seconds=30),
                "POLICY_ENGINE",
                "Policy Engine",
                "POLICY_EVALUATED",
                "Blocked retry: already paid",
                {"reason": reason},
                policy,
            )
        elif journey == "C_STOP":
            policy = "BLOCK"
            status = "STOPPED"
            suppressed = True
            completed = diagnosed_at + timedelta(minutes=6)
            add_action(
                case_id,
                "STOP_RECOVERY",
                diagnosed_at,
                completed,
                "SUCCEEDED",
                0,
                {"retry_reason": "mandate_or_cancel", "scheduler_id": "sched_stop"},
            )
            add_audit(
                case_id,
                diagnosed_at + timedelta(minutes=1),
                "POLICY_ENGINE",
                "Policy Engine",
                "RECOVERY_STOPPED",
                "Stopping rules: do not chase revoked/cancelled mandates",
                {"reason": reason},
                policy,
            )
        elif journey == "C_ESCALATE":
            policy = "ESCALATE"
            status = "ESCALATED"
            escalated = True
            suppressed = True
            completed = diagnosed_at + timedelta(hours=2)
            add_action(
                case_id,
                "ESCALATE_TO_AGENT",
                diagnosed_at + timedelta(minutes=10),
                completed,
                "SUCCEEDED",
                0,
                {"retry_reason": "dispute", "scheduler_id": "sched_esc"},
            )
            add_audit(
                case_id,
                diagnosed_at + timedelta(minutes=5),
                "POLICY_ENGINE",
                "Policy Engine",
                "ESCALATED",
                "Dispute opened — human only",
                {"reason": reason},
                policy,
            )
        elif journey == "B_PROMISE":
            policy = "ALLOW"
            promised_on = (failed_at + timedelta(days=rng.randint(3, 9))).date()
            delay_days = rng.randint(0, 4)
            fulfill_at = datetime.combine(promised_on, datetime.min.time(), tzinfo=tz)
            fulfill_at = fulfill_at + timedelta(days=delay_days, hours=10)
            high_trust = segment in {"HIGH_VALUE", "LOYAL", "ACTIVE"}
            fulfilled = high_trust or (salary_dep and payday_recovery_boost(promised_on.day) > 0.5)
            partial = fulfilled and rng.chance(0.18)
            pstat = "FULFILLED" if fulfilled and fulfill_at <= cfg.as_of else "BROKEN"
            paid_amount = int(payment["amount"])
            if partial:
                paid_amount = int(payment["amount"]) // 2
            if fulfill_at > cfg.as_of:
                pstat = "OPEN"
                paid_amount = 0
                status = "WAITING_PROMISE"
                completed = None
            elif pstat == "FULFILLED":
                status = "RECOVERED"
                recovered = True
                completed = fulfill_at
            else:
                paid_amount = 0
                status = "ESCALATED"
                escalated = True
                completed = fulfill_at + timedelta(hours=6)
            promises.append(
                {
                    "id": str(deterministic_uuid(cfg.seed, "promise", payment["id"])),
                    "recovery_case_id": case_id,
                    "promised_amount": payment["amount"],
                    "paid_amount": paid_amount,
                    "promised_date": promised_on.isoformat(),
                    "promise_status": pstat,
                    "fulfilled_at": _iso(fulfill_at) if pstat == "FULFILLED" else None,
                    "created_at": _iso(diagnosed_at + timedelta(minutes=20)),
                }
            )
            add_action(
                case_id,
                "PROMISE_TO_PAY",
                diagnosed_at + timedelta(minutes=15),
                diagnosed_at + timedelta(minutes=20),
                "SUCCEEDED",
                0,
                {"retry_reason": "customer_promised", "scheduler_id": "sched_ptp"},
            )
            add_audit(
                case_id,
                diagnosed_at + timedelta(minutes=20),
                "CUSTOMER",
                "Customer",
                "PROMISE_RECORDED",
                f"Customer promised {payment['amount']} paise on {promised_on}",
                {"promised_date": promised_on.isoformat()},
                policy,
            )
            if pstat == "FULFILLED":
                add_audit(
                    case_id,
                    fulfill_at,
                    "SYSTEM",
                    "Recovery Executor",
                    "PROMISE_FULFILLED",
                    "Promise captured",
                    {"amount": payment["amount"]},
                    "ALLOW",
                )
            elif pstat == "BROKEN":
                add_action(
                    case_id,
                    "ESCALATE_TO_AGENT",
                    fulfill_at + timedelta(hours=4),
                    completed,
                    "SUCCEEDED",
                    1,
                    {"retry_reason": "promise_broken", "scheduler_id": "sched_esc"},
                )
                add_audit(
                    case_id,
                    fulfill_at + timedelta(hours=4),
                    "POLICY_ENGINE",
                    "Policy Engine",
                    "PROMISE_BROKEN",
                    "Broken promise — escalate",
                    {"promised_date": promised_on.isoformat()},
                    "ESCALATE",
                )
        else:
            policy = "ALLOW"
            add_audit(
                case_id,
                diagnosed_at + timedelta(minutes=2),
                "POLICY_ENGINE",
                "Policy Engine",
                "POLICY_EVALUATED",
                "Allow bounded recovery",
                {"journey": journey, "reason": reason},
                policy,
            )
            if journey == "A_PAYDAY":
                wait_until = failed_at + timedelta(days=1)
                while calendar_day(wait_until, tz) > 5 and wait_until < cfg.as_of + timedelta(days=20):
                    wait_until += timedelta(days=1)
                wait_until = wait_until.replace(hour=9, minute=15)
                add_action(
                    case_id,
                    "WAIT_FOR_PAYDAY",
                    diagnosed_at + timedelta(minutes=8),
                    diagnosed_at + timedelta(minutes=9),
                    "SUCCEEDED",
                    0,
                    {"retry_reason": "salary_cycle", "scheduler_id": "sched_payday"},
                )
                recover = payday_recovery_boost(calendar_day(wait_until, tz)) >= 0.5 and wait_until <= cfg.as_of
                exec_status = "SUCCEEDED" if recover else "FAILED"
                add_action(
                    case_id,
                    "RETRY_PAYMENT",
                    wait_until,
                    wait_until + timedelta(minutes=4) if wait_until <= cfg.as_of else None,
                    exec_status if wait_until <= cfg.as_of else "SCHEDULED",
                    1,
                    {"retry_reason": "post_payday", "scheduler_id": "sched_retry"},
                )
                if recover:
                    status = "RECOVERED"
                    recovered = True
                    completed = wait_until + timedelta(minutes=4)
                elif wait_until > cfg.as_of:
                    status = "WAITING_RETRY"
                    completed = None
                else:
                    status = "WAITING_RETRY"
                    completed = None
            elif journey == "A_SWITCH":
                link = razorpay_id(cfg.seed, "plink", payment["id"])
                executed = diagnosed_at + timedelta(hours=6)
                recover = segment in {"HIGH_VALUE", "LOYAL", "NEW", "ACTIVE"}
                add_action(
                    case_id,
                    "SWITCH_PAYMENT_METHOD",
                    diagnosed_at + timedelta(minutes=12),
                    executed,
                    "SUCCEEDED" if recover else "FAILED",
                    1,
                    {
                        "retry_reason": "card_expired",
                        "payment_link_id": link,
                        "scheduler_id": "sched_switch",
                    },
                    link=f"https://rzp.io/i/{link[6:]}",
                )
                if recover:
                    status = "RECOVERED"
                    recovered = True
                    completed = executed
                else:
                    status = "WAITING_RETRY"
                    completed = None
            else:
                outage = matching_outage(failed_at, str(payment["payment_method"]), outages)
                retry_at = failed_at + timedelta(hours=8)
                if outage is not None:
                    retry_at = outage.ended_at + timedelta(minutes=25)
                recover = True
                if segment == "CHURN_RISK":
                    recover = False
                if reason == "UNKNOWN":
                    recover = segment == "HIGH_VALUE"
                if retry_at > cfg.as_of:
                    recover = False
                    status = "WAITING_RETRY"
                    completed = None
                    add_action(
                        case_id,
                        "RETRY_PAYMENT",
                        retry_at,
                        None,
                        "SCHEDULED",
                        1,
                        {"retry_reason": "rail_retry", "scheduler_id": "sched_retry"},
                    )
                else:
                    add_action(
                        case_id,
                        "RETRY_PAYMENT",
                        retry_at,
                        retry_at + timedelta(minutes=3),
                        "SUCCEEDED" if recover else "FAILED",
                        1,
                        {"retry_reason": "smart_retry", "scheduler_id": "sched_retry"},
                    )
                    if recover:
                        status = "RECOVERED"
                        recovered = True
                        completed = retry_at + timedelta(minutes=3)
                    else:
                        status = "WAITING_RETRY"
                        completed = None

        if recovered:
            retry_i += 1
            retry_time = completed or cfg.as_of
            retries.append(
                {
                    "id": str(deterministic_uuid(cfg.seed, "retry_pay", payment["id"])),
                    "merchant_id": payment["merchant_id"],
                    "customer_id": payment["customer_id"],
                    "subscription_id": payment["subscription_id"],
                    "razorpay_order_id": razorpay_id(cfg.seed, "order", f"retry-{payment['id']}"),
                    "razorpay_payment_id": razorpay_id(cfg.seed, "pay", f"retry-{payment['id']}"),
                    "idempotency_key": f"{payment['idempotency_key']}:retry",
                    "payment_status": "CAPTURED",
                    "failure_reason": None,
                    "payment_method": payment["payment_method"],
                    "amount": payment["amount"],
                    "currency": "INR",
                    "attempt_number": 2,
                    "payment_due_date": payment["payment_due_date"],
                    "payment_time": _iso(retry_time),
                    "paid_at": _iso(retry_time),
                    "created_at": _iso(retry_time),
                    "updated_at": _iso(retry_time),
                    "plan_name": payment["plan_name"],
                    "salary_dependent": payment["salary_dependent"],
                    "segment": payment["segment"],
                    "is_original_failure": False,
                }
            )
            add_audit(
                case_id,
                retry_time,
                "SYSTEM",
                "Recovery Executor",
                "PAYMENT_CAPTURED",
                "Retry captured",
                {"amount": payment["amount"]},
                "ALLOW",
            )

        if completed is not None and status in {"RECOVERED", "STOPPED", "ESCALATED", "CLOSED"}:
            add_audit(
                case_id,
                completed,
                "SYSTEM",
                "Recovery Executor",
                "CASE_CLOSED",
                f"Case {status.lower()}",
                {"status": status},
                None,
            )

        cases.append(
            {
                "id": case_id,
                "payment_id": payment["id"],
                "customer_id": payment["customer_id"],
                "merchant_id": str(cfg.merchant_id),
                "recovery_status": status,
                "diagnosed_reason": reason,
                "diagnosis_model": cfg.diagnosis_model,
                "diagnosis_version": cfg.diagnosis_version,
                "ai_confidence": confidence,
                "priority_score": _priority(segment, int(payment["amount"]), reason),
                "recovery_started_at": _iso(started),
                "recovery_completed_at": _iso(completed),
                "journey": journey,
                "ai_recovered": recovered,
                "ai_suppressed": suppressed,
                "ai_escalated": escalated,
                "amount": payment["amount"],
                "created_at": _iso(failed_at + timedelta(minutes=1)),
                "updated_at": _iso(completed or cfg.as_of),
            }
        )

    while len(actions) < cfg.n_recovery_actions:
        case = cases[len(actions) % len(cases)]
        pad_at = datetime.fromisoformat(str(case["created_at"])) + timedelta(hours=3)
        add_action(
            case["id"],
            "GENERATE_PAYMENT_LINK",
            pad_at,
            pad_at + timedelta(minutes=2),
            "SUCCEEDED",
            2,
            {
                "retry_reason": "backup_link",
                "payment_link_id": razorpay_id(cfg.seed, "plink", case["id"] + str(len(actions))),
                "scheduler_id": "sched_pad",
            },
        )

    while len(audits) < cfg.n_audit_events and cases:
        case = cases[len(audits) % len(cases)]
        add_audit(
            case["id"],
            datetime.fromisoformat(str(case["created_at"])) + timedelta(minutes=len(audits) % 50),
            "SYSTEM",
            "Scheduler",
            "ACTION_SCHEDULED",
            "Scheduler heartbeat",
            {"tick": len(audits)},
            None,
        )

    logger.info(
        "generator.recovery",
        extra={
            "cases": len(cases),
            "actions": len(actions),
            "promises": len(promises),
            "audits": len(audits),
            "retries": len(retries),
        },
    )
    return cases, actions, promises, audits, retries


def trim_payments(
    cfg: GeneratorConfig,
    rng: SeededRNG,
    payments: list[dict[str, Any]],
    customers: list[dict[str, Any]],
    subscriptions: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    """Keep all original failures and their retries; fill or trim to the attempt target."""
    failures = [row for row in payments if row.get("is_original_failure")]
    retries = [row for row in payments if int(row.get("attempt_number", 1)) > 1]
    captured = [
        row
        for row in payments
        if not row.get("is_original_failure") and int(row.get("attempt_number", 1)) == 1
    ]
    kept = failures + retries
    remaining = cfg.n_payment_attempts - len(kept)
    if remaining > 0:
        kept.extend(captured[:remaining])
    extra_i = 0
    by_customer = {row["id"]: row for row in customers}
    while len(kept) < cfg.n_payment_attempts and subscriptions:
        sub = subscriptions[extra_i % len(subscriptions)]
        customer = by_customer[sub["customer_id"]]
        due = cfg.window_start + timedelta(days=(extra_i % max(1, cfg.lookback_days - 1)), hours=11, minutes=20)
        if due > cfg.as_of:
            due = cfg.as_of - timedelta(hours=2)
        key = f"topup:{extra_i}"
        kept.append(
            {
                "id": str(deterministic_uuid(cfg.seed, "payment_topup", key)),
                "merchant_id": str(cfg.merchant_id),
                "customer_id": customer["id"],
                "subscription_id": sub["id"],
                "razorpay_order_id": razorpay_id(cfg.seed, "order", f"topup-{key}"),
                "razorpay_payment_id": razorpay_id(cfg.seed, "pay", f"topup-{key}"),
                "idempotency_key": f"{cfg.idempotency_prefix}:topup:{sub['id']}:{extra_i}",
                "payment_status": "CAPTURED",
                "failure_reason": None,
                "payment_method": customer["preferred_payment_method"],
                "amount": sub["billing_amount"],
                "currency": "INR",
                "attempt_number": 1,
                "payment_due_date": due.date().isoformat(),
                "payment_time": _iso(due),
                "paid_at": _iso(due + timedelta(minutes=rng.randint(2, 40))),
                "created_at": _iso(due),
                "updated_at": _iso(due),
                "plan_name": sub["plan_name"],
                "salary_dependent": customer["salary_dependent"],
                "segment": customer["customer_segment"],
                "is_original_failure": False,
            }
        )
        extra_i += 1
    logger.info("generator.payments.trimmed", extra={"count": len(kept)})
    return kept


def generate_metrics(
    cfg: GeneratorConfig,
    cases: list[dict[str, Any]],
) -> dict[str, Any]:
    """AI-strategy dashboard snapshot for FitLife."""
    at_risk = sum(int(c["amount"]) for c in cases)
    recovered = sum(int(c["amount"]) for c in cases if c["ai_recovered"])
    suppressed = sum(int(c["amount"]) for c in cases if c["ai_suppressed"])
    escalations = sum(1 for c in cases if c["ai_escalated"])
    stops = sum(1 for c in cases if c["recovery_status"] == "STOPPED")
    durations: list[float] = []
    for case in cases:
        if case["ai_recovered"] and case["recovery_completed_at"] and case["recovery_started_at"]:
            start = datetime.fromisoformat(str(case["recovery_started_at"]))
            end = datetime.fromisoformat(str(case["recovery_completed_at"]))
            durations.append((end - start).total_seconds() / 3600)
    avg_hours = round(sum(durations) / len(durations), 2) if durations else 0.0
    rate = recovered / at_risk if at_risk else 0.0
    return {
        "id": str(deterministic_uuid(cfg.seed, "metrics", str(cfg.merchant_id))),
        "merchant_id": str(cfg.merchant_id),
        "revenue_at_risk": at_risk,
        "recovered_revenue": recovered,
        "suppressed_revenue": suppressed,
        "recovery_rate": round(rate, 4),
        "escalation_count": escalations,
        "policy_stop_count": stops,
        "average_recovery_hours": avg_hours,
        "updated_at": _iso(cfg.as_of),
    }


def generate_baseline(cases: list[dict[str, Any]], failed: list[dict[str, Any]]) -> dict[str, Any]:
    """Naive dunning: retry immediately, no diagnosis, no stopping rules."""
    by_id = {row["id"]: row for row in failed}
    recovered = 0
    recovered_amt = 0
    harmful = 0
    for case in cases:
        payment = by_id[case["payment_id"]]
        reason = str(payment["failure_reason"])
        if reason in {"ALREADY_PAID", "DISPUTE", "MANDATE_REVOKED", "CUSTOMER_CANCELLED"}:
            harmful += 1
            continue
        if reason in {"UPI_FAILURE", "BANK_TIMEOUT", "UNKNOWN"}:
            recovered += 1
            recovered_amt += int(payment["amount"])
            continue
        if reason == "INSUFFICIENT_FUNDS":
            continue
        if reason == "CARD_EXPIRED":
            continue
    at_risk = sum(int(c["amount"]) for c in cases)
    return {
        "strategy": "baseline_immediate_retry",
        "recovered_count": recovered,
        "recovered_revenue": recovered_amt,
        "harmful_retries": harmful,
        "recovery_rate": round(recovered_amt / at_risk, 4) if at_risk else 0.0,
        "notes": "No payday wait, no stop on dispute/already-paid/revoked, no method switch.",
    }


def _preferred_channel(
    intended: str | None,
    customer: dict[str, Any],
) -> str | None:
    """Honour consent: fall back WhatsApp → SMS → none (and Voice → SMS)."""
    if intended is None:
        return None
    whatsapp = bool(customer.get("consent_whatsapp"))
    sms = bool(customer.get("consent_sms"))
    voice = bool(customer.get("consent_voice"))
    if intended == "whatsapp":
        if whatsapp:
            return "whatsapp"
        return "sms" if sms else None
    if intended == "voice":
        if voice:
            return "voice"
        if whatsapp:
            return "whatsapp"
        return "sms" if sms else None
    if intended == "sms":
        if sms:
            return "sms"
        return "whatsapp" if whatsapp else None
    return None


def generate_communication_costs(
    cfg: GeneratorConfig,
    customers: list[dict[str, Any]],
    cases: list[dict[str, Any]],
    actions: list[dict[str, Any]],
    metrics: dict[str, Any],
    baseline: dict[str, Any],
) -> dict[str, Any]:
    """SMS / WhatsApp / Voice spend and recovery ROI from executed actions.

    Derived from existing rows — no extra RNG, no CSV column changes.
    """
    by_customer = {row["id"]: row for row in customers}
    by_case = {row["id"]: row for row in cases}
    intended = {
        "RETRY_PAYMENT": "sms",
        "WAIT_FOR_PAYDAY": "sms",
        "GENERATE_PAYMENT_LINK": "whatsapp",
        "SWITCH_PAYMENT_METHOD": "whatsapp",
        "PROMISE_TO_PAY": "whatsapp",
        "ESCALATE_TO_AGENT": "voice",
        "STOP_RECOVERY": None,
        "NO_ACTION": None,
    }
    counts = {"sms": 0, "whatsapp": 0, "voice": 0, "suppressed": 0}
    for action in actions:
        if action.get("execution_status") not in {"SUCCEEDED", "FAILED"}:
            continue
        case = by_case.get(str(action["recovery_case_id"]))
        if case is None:
            continue
        customer = by_customer.get(str(case["customer_id"]), {})
        channel = _preferred_channel(intended.get(str(action["action_type"])), customer)
        if channel is None:
            counts["suppressed"] += 1
            continue
        counts[channel] += 1

    sms_cost = counts["sms"] * cfg.sms_cost_paise
    wa_cost = counts["whatsapp"] * cfg.whatsapp_cost_paise
    voice_cost = counts["voice"] * cfg.voice_cost_paise
    total = sms_cost + wa_cost + voice_cost
    recovered = int(metrics["recovered_revenue"])
    baseline_sms = len(cases) * cfg.sms_cost_paise
    roi = round(recovered / total, 4) if total else None
    baseline_roi = (
        round(int(baseline["recovered_revenue"]) / baseline_sms, 4) if baseline_sms else None
    )
    return {
        "unit_costs_paise": {
            "sms": cfg.sms_cost_paise,
            "whatsapp": cfg.whatsapp_cost_paise,
            "voice": cfg.voice_cost_paise,
        },
        "ai": {
            "sms_count": counts["sms"],
            "whatsapp_count": counts["whatsapp"],
            "voice_count": counts["voice"],
            "suppressed_count": counts["suppressed"],
            "sms_cost_paise": sms_cost,
            "whatsapp_cost_paise": wa_cost,
            "voice_cost_paise": voice_cost,
            "total_cost_paise": total,
            "recovered_revenue_paise": recovered,
            "net_recovered_paise": recovered - total,
            "recovery_roi": roi,
        },
        "baseline": {
            "sms_count": len(cases),
            "whatsapp_count": 0,
            "voice_count": 0,
            "total_cost_paise": baseline_sms,
            "recovered_revenue_paise": int(baseline["recovered_revenue"]),
            "net_recovered_paise": int(baseline["recovered_revenue"]) - baseline_sms,
            "recovery_roi": baseline_roi,
            "notes": "One generic SMS per failed payment. No WhatsApp, no voice, no consent gate.",
        },
        "roi_lift": None if roi is None or baseline_roi is None else round(roi - baseline_roi, 4),
        "net_lift_paise": (recovered - total) - (int(baseline["recovered_revenue"]) - baseline_sms),
        "notes": (
            "Ratio ROI (recovered / comms cost) favours cheap blast SMS. "
            "net_lift_paise is the rupee comparison: extra recovered after outreach cost."
        ),
    }


def summarize_customer_behaviour(
    customers: list[dict[str, Any]],
    payments: list[dict[str, Any]],
) -> dict[str, Any]:
    """90-day payment stickiness per customer, derived after generation."""
    from collections import defaultdict

    by_cust: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for pay in payments:
        if int(pay.get("attempt_number", 1)) != 1:
            continue
        by_cust[str(pay["customer_id"])].append(pay)
    profiles: list[dict[str, Any]] = []
    streak_fail = 0
    streak_pay = 0
    for customer in customers:
        ledger = sorted(by_cust.get(customer["id"], []), key=lambda row: str(row["created_at"]))
        flags = [
            1 if row.get("is_original_failure") or row.get("payment_status") == "FAILED" else 0
            for row in ledger
        ]
        fail_run = pay_run = max_fail = max_pay = 0
        for flag in flags:
            if flag:
                fail_run += 1
                pay_run = 0
            else:
                pay_run += 1
                fail_run = 0
            max_fail = max(max_fail, fail_run)
            max_pay = max(max_pay, pay_run)
        attempts = len(flags)
        failures = sum(flags)
        discipline = latent_pay_discipline(customer["id"], customer["customer_segment"])
        sticky = max_fail >= 2 or max_pay >= 3
        if max_fail >= 2:
            streak_fail += 1
        if max_pay >= 3:
            streak_pay += 1
        profiles.append(
            {
                "customer_id": customer["id"],
                "segment": customer["customer_segment"],
                "salary_dependent": customer["salary_dependent"],
                "latent_pay_discipline": discipline,
                "invoice_attempts": attempts,
                "failed_invoices": failures,
                "captured_invoices": attempts - failures,
                "max_fail_streak": max_fail,
                "max_capture_streak": max_pay,
                "observed_reliability": round(1 - (failures / attempts), 4) if attempts else None,
                "sticky_behaviour": sticky,
            }
        )
    return {
        "customers": len(profiles),
        "customers_with_fail_streak_2plus": streak_fail,
        "customers_with_capture_streak_3plus": streak_pay,
        "persistence_enabled_at_generation": False,
        "rows": profiles,
    }


def festival_calendar_report(cfg: GeneratorConfig) -> dict[str, Any]:
    """List festival dates in/near the window and whether they biased generation."""
    tz = ZoneInfo(cfg.timezone)
    window_start = cfg.window_start.astimezone(tz).date()
    window_end = cfg.as_of.astimezone(tz).date()
    entries = []
    for fest_date, name, effect in INDIAN_FESTIVALS_2026:
        in_window = window_start <= fest_date <= window_end
        entries.append(
            {
                "date": fest_date.isoformat(),
                "name": name,
                "effect": effect,
                "in_observation_window": in_window,
                "applied": bool(cfg.enable_festival_calendar and in_window),
            }
        )
    return {
        "enabled": cfg.enable_festival_calendar,
        "timezone": cfg.timezone,
        "festivals": entries,
    }


def build_ecosystem(cfg: GeneratorConfig) -> dict[str, Any]:
    """Run the full deterministic pipeline and return in-memory tables."""
    rng = SeededRNG(cfg.seed)
    outages = build_outages(cfg, rng)
    merchant = generate_merchant(cfg)
    customers = generate_customers(cfg, rng)
    subscriptions = generate_subscriptions(cfg, rng, customers)
    payments = generate_first_payments(cfg, rng, customers, subscriptions, outages)
    failed = mark_failures(cfg, rng, payments, outages)
    cases, actions, promises, audits, retries = generate_recovery(cfg, rng, failed, outages)
    payments.extend(retries)
    payments = trim_payments(cfg, rng, payments, customers, subscriptions)
    metrics = generate_metrics(cfg, cases)
    baseline = generate_baseline(cases, failed)
    behaviour = summarize_customer_behaviour(customers, payments)
    behaviour["persistence_enabled_at_generation"] = cfg.enable_behaviour_persistence
    comms = generate_communication_costs(cfg, customers, cases, actions, metrics, baseline)
    festivals = festival_calendar_report(cfg)
    logger.info("generator.ecosystem.done", extra={"seed": cfg.seed})
    return {
        "merchant": merchant,
        "customers": customers,
        "subscriptions": subscriptions,
        "payments": payments,
        "recovery_cases": cases,
        "recovery_actions": actions,
        "promises_to_pay": promises,
        "audit_logs": audits,
        "merchant_metrics": [metrics],
        "outages": outages,
        "baseline": baseline,
        "failed_payments": failed,
        "customer_behaviour": behaviour,
        "communication_costs": comms,
        "festival_calendar": festivals,
    }
