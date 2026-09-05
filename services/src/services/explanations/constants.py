"""Shared explanation-agent constants. No API keys."""

from __future__ import annotations

from integrations.gemini.constants import PROMPT_VERSION

MERCHANT_DISCLAIMER: str = (
    "Based on payment history and RecoveryPilot policy evaluation."
)

__all__ = ["MERCHANT_DISCLAIMER", "PROMPT_VERSION"]
