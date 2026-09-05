"""Constants for the Gemini explanation client. No API keys here."""

from __future__ import annotations

from datetime import timedelta

DEFAULT_MODEL: str = "gemini-2.5-flash"
DEFAULT_TEMPERATURE: float = 0.2
DEFAULT_MAX_OUTPUT_TOKENS: int = 512
PROMPT_VERSION: str = "explanation_prompt_v1"
GENERATE_URL: str = (
    "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
)
REQUEST_TIMEOUT_SECONDS: float = 15.0
CACHE_TTL: timedelta = timedelta(hours=24)
PLACEHOLDER_API_KEYS: frozenset[str] = frozenset(
    {
        "",
        "placeholder_gemini_key",
        "changeme",
        "your_api_key_here",
    }
)

# Output length guards. Over-long Gemini text is rejected and replaced.
MAX_MERCHANT_CHARS: int = 800
MIN_MERCHANT_CHARS: int = 40
MAX_SMS_CHARS: int = 320
MAX_WHATSAPP_CHARS: int = 1024
MAX_EMAIL_CHARS: int = 1500
MAX_COMPLIANCE_CHARS: int = 2000
MAX_DASHBOARD_SUMMARY_CHARS: int = 160
MAX_HINGLISH_CHARS: int = 400
