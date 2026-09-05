"""Sanitize engine outputs for Gemini. Strip IDs, secrets, and extra PII."""

from __future__ import annotations

import re
from typing import Any
from uuid import UUID

from services.explanations.constants import MERCHANT_DISCLAIMER
from services.explanations.models import ExplanationContext
from services.policy.models import PolicyDecisionResult

_UUID = re.compile(
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}"
)
_SECRET_KEYS = frozenset(
    {
        "api_key",
        "apikey",
        "token",
        "secret",
        "password",
        "authorization",
        "idempotency_key",
        "gemini_api_key",
        "razorpay_key_secret",
    }
)
_ID_KEYS = frozenset(
    {
        "id",
        "execution_id",
        "audit_event_id",
        "webhook_event_id",
        "payment_id",
        "recovery_case_id",
        "customer_id",
        "subscription_id",
        "payment_link_id",
        "request_id",
        "correlation_id",
        "case_id",
    }
)

DIAGNOSIS_LABELS: dict[str, str] = {
    "INSUFFICIENT_FUNDS": "insufficient funds",
    "BANK_TIMEOUT": "a bank timeout",
    "UPI_TIMEOUT": "a UPI timeout",
    "CARD_EXPIRED": "an expired card",
    "AUTHENTICATION_FAILED": "an authentication failure",
    "MANDATE_REVOKED": "a revoked mandate",
    "CUSTOMER_CANCELLED": "a cancelled subscription",
    "DUPLICATE_PAYMENT": "a duplicate payment",
    "CHARGEBACK_ACTIVE": "an active chargeback",
    "ALREADY_PAID": "the invoice already being paid",
    "UNKNOWN": "an unclear failure",
}

STRATEGY_LABELS: dict[str, str] = {
    "WAIT_FOR_PAYDAY": "wait until payday and then retry",
    "RETRY_PAYMENT": "retry the payment",
    "RETRY_SILENTLY": "retry the payment quietly after the outage",
    "SEND_PAYMENT_LINK": "send a payment link",
    "SWITCH_PAYMENT_METHOD": "ask the customer to pay with UPI",
    "REQUEST_NEW_MANDATE": "ask the customer to update their card",
    "HONOUR_PROMISE_TO_PAY": "wait until the promised payment date",
    "ESCALATE_TO_HUMAN": "hand the case to a human agent",
    "STOP_RECOVERY": "stop recovery",
}


def first_name_only(raw: str) -> str:
    """Keep a single given name. Drop emails, phones, and extra tokens."""
    token = (raw or "").strip().split()[0] if (raw or "").strip() else ""
    if not token or "@" in token or token.isdigit() or _UUID.search(token):
        return ""
    cleaned = re.sub(r"[^A-Za-z.'-]", "", token)
    return cleaned[:40]


def with_merchant_disclaimer(text: str) -> str:
    """Append the standard merchant confidence disclaimer if missing."""
    stripped = (text or "").strip()
    if not stripped:
        return MERCHANT_DISCLAIMER
    if MERCHANT_DISCLAIMER in stripped:
        return stripped
    return f"{stripped} {MERCHANT_DISCLAIMER}"


def human_diagnosis(code: str) -> str:
    """Plain-language diagnosis label."""
    return DIAGNOSIS_LABELS.get(code, code.replace("_", " ").lower())


def human_strategy(code: str) -> str:
    """Plain-language planner strategy."""
    return STRATEGY_LABELS.get(code, code.replace("_", " ").lower())


def amount_rupees(paise: int) -> int:
    """Display rupees from integer paise. Truncates, does not round."""
    return max(0, int(paise) // 100)


def blocked_policies(policy: PolicyDecisionResult) -> list[str]:
    """Failed policy names plus channel blocks. Factual, from the engine."""
    names = list(policy.failed_policies)
    for row in policy.evaluated_rules:
        if row.result.value in {"FAIL", "STOP", "DENY"} and row.policy_name not in names:
            names.append(row.policy_name)
    if policy.blocked_channels:
        names.append("blocked_channels:" + ",".join(policy.blocked_channels))
    return names


def _strip_value(value: Any) -> Any:
    """Recursively drop secrets, ids, and UUID strings."""
    if isinstance(value, UUID):
        return None
    if isinstance(value, str):
        if _UUID.search(value):
            return _UUID.sub("[id]", value)
        return value
    if isinstance(value, dict):
        cleaned: dict[str, Any] = {}
        for key, item in value.items():
            lowered = str(key).lower()
            if lowered in _SECRET_KEYS or lowered in _ID_KEYS:
                continue
            if lowered.endswith("_id"):
                continue
            stripped = _strip_value(item)
            if stripped is not None:
                cleaned[key] = stripped
        return cleaned
    if isinstance(value, list):
        return [item for item in (_strip_value(v) for v in value) if item is not None]
    return value


def sanitize_tree(payload: dict[str, Any]) -> dict[str, Any]:
    """Strip IDs and secrets from a dict before it is sent to Gemini."""
    cleaned = _strip_value(payload)
    return cleaned if isinstance(cleaned, dict) else {}


def merchant_payload(context: ExplanationContext) -> dict[str, Any]:
    """Structured merchant prompt input. No confidence, no ids."""
    execution = None
    if context.execution is not None:
        execution = {
            "status": context.execution.status.value,
            "outcome": context.execution.outcome,
            "success": context.execution.success,
        }
    raw = {
        "failure_reason": human_diagnosis(str(context.diagnosis.diagnosis)),
        "evidence": list(context.diagnosis.evidence)[:6],
        "policy_decision": str(context.policy.decision),
        "strategy": human_strategy(str(context.plan.strategy)),
        "expected_outcome": context.plan.expected_outcome,
        "timing_reason": context.plan.timing_reason,
        "execution": execution,
        "merchant_name": context.merchant_name,
    }
    return sanitize_tree(raw)


def customer_payload(context: ExplanationContext) -> dict[str, Any]:
    """Structured customer prompt input. First name only."""
    rupees = amount_rupees(context.plan.estimated_recovery_value)
    raw = {
        "first_name": first_name_only(context.customer_first_name) or "there",
        "merchant": context.merchant_name,
        "amount_rupees": rupees,
        "has_payment_link": bool(context.execution and context.execution.payment_link_id),
        "strategy": human_strategy(str(context.plan.strategy)),
        "recommended_channels": list(context.plan.recommended_channels),
    }
    return sanitize_tree(raw)


def compliance_payload(context: ExplanationContext) -> dict[str, Any]:
    """Factual fields for an audit paragraph. No extra narrative invention."""
    outcome = "not executed"
    if context.execution is not None:
        outcome = context.execution.outcome
    raw = {
        "diagnosis": str(context.diagnosis.diagnosis),
        "evidence": list(context.diagnosis.evidence),
        "triggered_policies": list(context.policy.triggered_policies),
        "blocked_policies": blocked_policies(context.policy),
        "planner_strategy": str(context.plan.strategy),
        "execution_outcome": outcome,
        "policy_decision": str(context.policy.decision),
        "policy_reason": context.policy.reason,
    }
    return sanitize_tree(raw)


def dashboard_payload(context: ExplanationContext) -> dict[str, Any]:
    """Dashboard prompt input. Risk and next action already decided."""
    raw = {
        "title": human_diagnosis(str(context.diagnosis.diagnosis)).title(),
        "risk_level": str(context.diagnosis.priority_bucket),
        "next_action": human_strategy(str(context.plan.strategy)),
        "policy_decision": str(context.policy.decision),
        "expected_outcome": context.plan.expected_outcome,
    }
    return sanitize_tree(raw)
