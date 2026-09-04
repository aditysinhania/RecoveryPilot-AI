"""Gemini generateContent adapter. Explanation copy only — never recovery decisions."""

from integrations.gemini.cache import ExplanationCache, get_explanation_cache
from integrations.gemini.constants import (
    CACHE_TTL,
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
)
from integrations.gemini.gemini_client import GeminiClient, GeminiError
from integrations.gemini.parser import extract_json_object, text_within
from integrations.gemini.prompts import (
    compliance_prompt,
    customer_prompt,
    dashboard_prompt,
    merchant_prompt,
)

__all__ = [
    "CACHE_TTL",
    "DEFAULT_MAX_OUTPUT_TOKENS",
    "DEFAULT_MODEL",
    "DEFAULT_TEMPERATURE",
    "ExplanationCache",
    "GeminiClient",
    "GeminiError",
    "compliance_prompt",
    "customer_prompt",
    "dashboard_prompt",
    "extract_json_object",
    "get_explanation_cache",
    "merchant_prompt",
    "text_within",
]
