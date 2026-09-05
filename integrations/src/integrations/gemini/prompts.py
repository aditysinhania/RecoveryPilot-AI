"""Prompt templates for Gemini explanation modes. No ORM, no secrets."""

from __future__ import annotations

import json
from typing import Any

from integrations.gemini.constants import PROMPT_VERSION

_SHARED_RULES = f"""You are RecoveryPilot's explanation writer.
Prompt version: {PROMPT_VERSION}.
You NEVER decide recovery actions, retries, channels, or policy.
You only rewrite the provided JSON as clear text.
Rules:
- Use only the JSON in this message.
- Do not invent payment amounts, dates, names, links, or outcomes.
- If a field is missing, say that the information was not provided.
- Do not mention confidence scores, model names, API keys, or internal IDs.
- Do not threaten the customer.
- Reply with a single JSON object only. No markdown.
"""


def _dump(payload: dict[str, Any]) -> str:
    """Serialize the sanitized payload for the prompt body."""
    return json.dumps(payload, ensure_ascii=False, indent=2)


def merchant_prompt(payload: dict[str, Any]) -> str:
    """2–4 sentence merchant-facing explanation. No jargon."""
    return (
        f"{_SHARED_RULES}\n"
        "Task: write a merchant explanation.\n"
        "Cover: why the payment failed, why this recovery strategy was chosen, "
        "and the expected outcome.\n"
        "Tone: professional, plain language, 2 to 4 sentences.\n"
        "Do not include a confidence score. Do not add a disclaimer; the service appends one.\n"
        'Return JSON: {"explanation": "..."}\n'
        f"INPUT:\n{_dump(payload)}\n"
    )


def customer_prompt(payload: dict[str, Any], channel: str) -> str:
    """Payment communication for WhatsApp, SMS, or Email."""
    limit = "320 characters" if channel == "SMS" else "a short message"
    return (
        f"{_SHARED_RULES}\n"
        f"Task: write a {channel} message asking the customer to complete payment.\n"
        f"Keep it under {limit}. Professional, friendly, never threatening.\n"
        "English body. Also provide a Hinglish template that uses "
        "{first_name}, {amount_rupees}, {merchant}, and {payment_link} placeholders.\n"
        "Do not mention policies, diagnosis codes, or confidence.\n"
        "Return JSON: "
        '{"body": "...", "hinglish_placeholder": "..."}\n'
        f"INPUT:\n{_dump(payload)}\n"
    )


def compliance_prompt(payload: dict[str, Any]) -> str:
    """Audit-ready factual narrative. Structured fields stay in the engines."""
    return (
        f"{_SHARED_RULES}\n"
        "Task: write one factual audit paragraph that restates diagnosis, "
        "evidence, triggered policies, blocked policies, planner strategy, "
        "and execution outcome. Do not add facts that are not in INPUT.\n"
        'Return JSON: {"narrative": "..."}\n'
        f"INPUT:\n{_dump(payload)}\n"
    )


def dashboard_prompt(payload: dict[str, Any]) -> str:
    """One-sentence dashboard card copy. Max 160 characters."""
    return (
        f"{_SHARED_RULES}\n"
        "Task: write a dashboard card summary. One sentence, maximum 160 characters.\n"
        "Do not invent a next action or risk level; those are already decided.\n"
        'Return JSON: {"title": "...", "summary": "..."}\n'
        f"INPUT:\n{_dump(payload)}\n"
    )
