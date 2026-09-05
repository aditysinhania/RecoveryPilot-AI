"""Gemini explanation service. Rewrites engine outputs; never chooses actions.

Does not call Razorpay, send messages, or write to PostgreSQL.
Does not modify diagnosis, policy, planner, or executor results.
"""

from __future__ import annotations

import logging
import re
from datetime import UTC, datetime
from typing import Any
from uuid import UUID

from integrations.gemini.cache import ExplanationCache, get_explanation_cache
from integrations.gemini.constants import (
    MAX_COMPLIANCE_CHARS,
    MAX_DASHBOARD_SUMMARY_CHARS,
    MAX_EMAIL_CHARS,
    MAX_HINGLISH_CHARS,
    MAX_MERCHANT_CHARS,
    MAX_SMS_CHARS,
    MAX_WHATSAPP_CHARS,
    MIN_MERCHANT_CHARS,
)
from integrations.gemini.gemini_client import GeminiClient, GeminiError
from integrations.gemini.parser import extract_json_object, text_within
from integrations.gemini.prompts import (
    compliance_prompt,
    customer_prompt,
    dashboard_prompt,
    merchant_prompt,
)
from services.explanations.fallback import (
    fallback_compliance,
    fallback_customer,
    fallback_dashboard,
    fallback_merchant,
)
from services.explanations.formatter import (
    compliance_payload,
    customer_payload,
    dashboard_payload,
    merchant_payload,
    with_merchant_disclaimer,
)
from services.explanations.models import (
    BatchDashboardResult,
    ComplianceExplanation,
    CustomerMessage,
    DashboardSummary,
    ExplanationContext,
    ExplanationSource,
    ExplanationType,
    MerchantExplanation,
)

logger = logging.getLogger(__name__)

_CHANNEL_TYPES = {
    "WhatsApp": ExplanationType.CUSTOMER_WHATSAPP,
    "SMS": ExplanationType.CUSTOMER_SMS,
    "Email": ExplanationType.CUSTOMER_EMAIL,
}
_CHANNEL_MAX = {
    "WhatsApp": MAX_WHATSAPP_CHARS,
    "SMS": MAX_SMS_CHARS,
    "Email": MAX_EMAIL_CHARS,
}


def _resolve_client(client: GeminiClient | None) -> GeminiClient:
    """Use the injected client, else Settings()-backed GeminiClient."""
    return client if client is not None else GeminiClient.from_settings()


def _resolve_cache(cache: ExplanationCache | None) -> ExplanationCache:
    """Use the injected cache, else the process singleton."""
    return cache if cache is not None else get_explanation_cache()


def _case_id(context: ExplanationContext) -> str:
    """Cache key case fragment."""
    value = (
        context.case_id
        or context.plan.recovery_case_id
        or context.diagnosis.recovery_case_id
        or context.policy.recovery_case_id
    )
    return str(value) if value is not None else "no-case"


def _uuid_case(context: ExplanationContext) -> UUID | None:
    """Typed case id for result models."""
    return (
        context.case_id
        or context.plan.recovery_case_id
        or context.diagnosis.recovery_case_id
        or context.policy.recovery_case_id
    )


def _cache_key(context: ExplanationContext, explanation_type: ExplanationType, cache: ExplanationCache) -> str:
    """case + type + planner_version + policy_version."""
    return cache.make_key(
        _case_id(context),
        explanation_type.value,
        context.plan.planner_version,
        context.policy.policy_version,
    )


def _hydrate(model_cls: type, hit: dict[str, Any] | None) -> Any | None:
    """Rehydrate a cached payload, or ``None`` if it is corrupt."""
    if hit is None:
        return None
    try:
        payload = dict(hit)
        payload["cached"] = True
        return model_cls.model_validate(payload)
    except Exception:  # noqa: BLE001
        logger.info("explain.cache.corrupt", extra={"model": model_cls.__name__})
        return None


def _gemini_json(client: GeminiClient, prompt: str) -> dict[str, Any] | None:
    """Call Gemini and parse JSON. Returns None on any failure."""
    if not client.is_available():
        logger.info("gemini.skip_unconfigured")
        return None
    try:
        raw = client.generate(prompt)
    except GeminiError:
        logger.info("gemini.generate.failed")
        return None
    except Exception as exc:  # noqa: BLE001
        logger.info("gemini.generate.caught", extra={"error": type(exc).__name__})
        return None
    return extract_json_object(raw)


def _sentence_count(text: str) -> int:
    """Count sentence-like chunks for the merchant 2–4 sentence rule."""
    parts = [item.strip() for item in re.split(r"[.!?]+", text) if item.strip()]
    return len(parts)


def explain_merchant(
    context: ExplanationContext,
    *,
    client: GeminiClient | None = None,
    cache: ExplanationCache | None = None,
) -> MerchantExplanation:
    """Merchant-facing 2–4 sentence explanation.

    Args:
        context: Diagnosis, policy, plan, optional execution.
        client: Optional Gemini client (tests inject a fake).
        cache: Optional TTL cache.

    Returns:
        ``MerchantExplanation``. Falls back locally when Gemini fails.
    """
    log = _resolve_cache(cache)
    key = _cache_key(context, ExplanationType.MERCHANT, log)
    cached = _hydrate(MerchantExplanation, log.get(key))
    if cached is not None:
        return cached
    logger.info("explain.merchant.start", extra={"case_id": _case_id(context)})
    gemini = _resolve_client(client)
    parsed = _gemini_json(gemini, merchant_prompt(merchant_payload(context)))
    text = str((parsed or {}).get("explanation") or "").strip()
    usable = (
        text
        and text_within(text, minimum=MIN_MERCHANT_CHARS, maximum=MAX_MERCHANT_CHARS)
        and 2 <= _sentence_count(text) <= 4
    )
    result = (
        MerchantExplanation(
            text=with_merchant_disclaimer(text),
            source=ExplanationSource.GEMINI,
            generated_at=datetime.now(UTC),
            case_id=_uuid_case(context),
        )
        if usable
        else fallback_merchant(context)
    )
    log.set(key, result.model_dump(mode="json"))
    logger.info("explain.merchant.ok", extra={"source": result.source.value})
    return result


def explain_customer(
    context: ExplanationContext,
    channel: str,
    *,
    client: GeminiClient | None = None,
    cache: ExplanationCache | None = None,
) -> CustomerMessage:
    """Customer payment copy for WhatsApp, SMS, or Email. Not sent."""
    explanation_type = _CHANNEL_TYPES.get(channel, ExplanationType.CUSTOMER_SMS)
    log = _resolve_cache(cache)
    key = _cache_key(context, explanation_type, log)
    cached = _hydrate(CustomerMessage, log.get(key))
    if cached is not None:
        return cached
    logger.info(
        "explain.customer.start",
        extra={"case_id": _case_id(context), "channel": channel},
    )
    gemini = _resolve_client(client)
    parsed = _gemini_json(gemini, customer_prompt(customer_payload(context), channel))
    body = str((parsed or {}).get("body") or "").strip()
    hinglish = str((parsed or {}).get("hinglish_placeholder") or "").strip()
    max_chars = _CHANNEL_MAX.get(channel, MAX_SMS_CHARS)
    usable = bool(body) and text_within(body, minimum=20, maximum=max_chars)
    if hinglish and not text_within(hinglish, minimum=10, maximum=MAX_HINGLISH_CHARS):
        usable = False
    if usable:
        result = CustomerMessage(
            channel=channel,
            language="en",
            body=body,
            hinglish_placeholder=hinglish
            or "Namaste {first_name}, aapka {merchant} payment pending hai.",
            source=ExplanationSource.GEMINI,
            explanation_type=explanation_type,
            generated_at=datetime.now(UTC),
            case_id=_uuid_case(context),
        )
    else:
        result = fallback_customer(context, channel)
    log.set(key, result.model_dump(mode="json"))
    logger.info("explain.customer.ok", extra={"source": result.source.value, "channel": channel})
    return result


def explain_customer_sms(
    context: ExplanationContext,
    *,
    client: GeminiClient | None = None,
    cache: ExplanationCache | None = None,
) -> CustomerMessage:
    """SMS variant of ``explain_customer``."""
    return explain_customer(context, "SMS", client=client, cache=cache)


def explain_customer_whatsapp(
    context: ExplanationContext,
    *,
    client: GeminiClient | None = None,
    cache: ExplanationCache | None = None,
) -> CustomerMessage:
    """WhatsApp variant of ``explain_customer``."""
    return explain_customer(context, "WhatsApp", client=client, cache=cache)


def explain_customer_email(
    context: ExplanationContext,
    *,
    client: GeminiClient | None = None,
    cache: ExplanationCache | None = None,
) -> CustomerMessage:
    """Email variant of ``explain_customer``."""
    return explain_customer(context, "Email", client=client, cache=cache)


def explain_compliance(
    context: ExplanationContext,
    *,
    client: GeminiClient | None = None,
    cache: ExplanationCache | None = None,
) -> ComplianceExplanation:
    """Audit-ready explanation. Structured fields always come from engines."""
    log = _resolve_cache(cache)
    key = _cache_key(context, ExplanationType.COMPLIANCE, log)
    cached = _hydrate(ComplianceExplanation, log.get(key))
    if cached is not None:
        return cached
    logger.info("explain.compliance.start", extra={"case_id": _case_id(context)})
    base = fallback_compliance(context)
    gemini = _resolve_client(client)
    parsed = _gemini_json(gemini, compliance_prompt(compliance_payload(context)))
    narrative = str((parsed or {}).get("narrative") or "").strip()
    if narrative and text_within(narrative, minimum=40, maximum=MAX_COMPLIANCE_CHARS):
        result = base.model_copy(
            update={
                "narrative": narrative,
                "source": ExplanationSource.GEMINI,
            }
        )
    else:
        result = base
    log.set(key, result.model_dump(mode="json"))
    logger.info("explain.compliance.ok", extra={"source": result.source.value})
    return result


def explain_dashboard(
    context: ExplanationContext,
    *,
    client: GeminiClient | None = None,
    cache: ExplanationCache | None = None,
) -> DashboardSummary:
    """Dashboard card. Risk and next action stay on the engine outputs."""
    log = _resolve_cache(cache)
    key = _cache_key(context, ExplanationType.DASHBOARD, log)
    cached = _hydrate(DashboardSummary, log.get(key))
    if cached is not None:
        return cached
    logger.info("explain.dashboard.start", extra={"case_id": _case_id(context)})
    base = fallback_dashboard(context)
    gemini = _resolve_client(client)
    parsed = _gemini_json(gemini, dashboard_prompt(dashboard_payload(context)))
    title = str((parsed or {}).get("title") or "").strip() or base.title
    summary = str((parsed or {}).get("summary") or "").strip()
    usable = bool(summary) and text_within(
        summary, minimum=8, maximum=MAX_DASHBOARD_SUMMARY_CHARS
    )
    if usable:
        result = base.model_copy(
            update={
                "title": title[:80],
                "summary": summary,
                "source": ExplanationSource.GEMINI,
            }
        )
    else:
        result = base
    log.set(key, result.model_dump(mode="json"))
    logger.info("explain.dashboard.ok", extra={"source": result.source.value})
    return result


def generate_batch_summaries(
    items: list[ExplanationContext],
    *,
    client: GeminiClient | None = None,
    cache: ExplanationCache | None = None,
) -> BatchDashboardResult:
    """Dashboard cards for many cases. Cached cases skip Gemini.

    Args:
        items: Per-case engine snapshots.
        client: Shared Gemini client.
        cache: Shared TTL cache.

    Returns:
        Summaries plus cache-hit and fallback counts.
    """
    log = _resolve_cache(cache)
    gemini = _resolve_client(client)
    logger.info("explain.batch.start", extra={"count": len(items)})
    results: list[DashboardSummary] = []
    hits = 0
    fallbacks = 0
    for item in items:
        card = explain_dashboard(item, client=gemini, cache=log)
        results.append(card)
        if card.cached:
            hits += 1
        if card.source == ExplanationSource.FALLBACK and not card.cached:
            fallbacks += 1
    logger.info(
        "explain.batch.ok",
        extra={"cache_hits": hits, "fallbacks": fallbacks},
    )
    return BatchDashboardResult(results=results, cache_hits=hits, fallbacks=fallbacks)
