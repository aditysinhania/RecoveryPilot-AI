"""HTTP client for Gemini generateContent. Never logs API keys."""

from __future__ import annotations

import logging
import os
from typing import Any

import httpx

from integrations.gemini.constants import (
    DEFAULT_MAX_OUTPUT_TOKENS,
    DEFAULT_MODEL,
    DEFAULT_TEMPERATURE,
    GENERATE_URL,
    PLACEHOLDER_API_KEYS,
    REQUEST_TIMEOUT_SECONDS,
)

logger = logging.getLogger(__name__)


class GeminiError(Exception):
    """Raised when Gemini cannot produce a usable response."""


class GeminiClient:
    """Thin generateContent wrapper. Does not choose recovery actions."""

    def __init__(
        self,
        *,
        api_key: str,
        model: str = DEFAULT_MODEL,
        temperature: float = DEFAULT_TEMPERATURE,
        max_output_tokens: int = DEFAULT_MAX_OUTPUT_TOKENS,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        self._api_key = api_key
        self.model = model
        self.temperature = temperature
        self.max_output_tokens = max_output_tokens
        self._transport = transport

    @classmethod
    def from_settings(cls) -> GeminiClient:
        """Load key and model from ``Settings()``, else process environment.

        Returns:
            A client. Placeholder keys are kept so ``is_available`` is false.
        """
        api_key = os.environ.get("GEMINI_API_KEY", "")
        model = os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)
        temperature = DEFAULT_TEMPERATURE
        max_tokens = DEFAULT_MAX_OUTPUT_TOKENS
        try:
            from app.config.settings import Settings

            loaded = Settings()
            api_key = loaded.gemini_api_key
            model = loaded.gemini_model
            temperature = float(loaded.gemini_temperature)
            max_tokens = int(loaded.gemini_max_output_tokens)
        except Exception:  # noqa: BLE001 — integrations must run without FastAPI
            logger.info("gemini.settings.fallback_env")
        return cls(
            api_key=api_key,
            model=model,
            temperature=temperature,
            max_output_tokens=max_tokens,
        )

    def is_available(self) -> bool:
        """False when the key is missing or a documented placeholder."""
        key = (self._api_key or "").strip()
        if key in PLACEHOLDER_API_KEYS:
            return False
        if key.lower().startswith("placeholder"):
            return False
        return True

    def generate(self, prompt: str) -> str:
        """Call Gemini and return the first text part.

        Args:
            prompt: Fully built prompt. Must already be sanitized.

        Returns:
            Model text (often a JSON object).

        Raises:
            GeminiError: When the client is unconfigured or the HTTP call fails.
        """
        if not self.is_available():
            raise GeminiError("Gemini API key is not configured.")
        url = GENERATE_URL.format(model=self.model)
        body: dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
            "generationConfig": {
                "temperature": self.temperature,
                "maxOutputTokens": self.max_output_tokens,
                "responseMimeType": "application/json",
            },
        }
        logger.info(
            "gemini.generate.start",
            extra={"model": self.model, "prompt_chars": len(prompt)},
        )
        try:
            with httpx.Client(timeout=REQUEST_TIMEOUT_SECONDS, transport=self._transport) as http:
                response = http.post(
                    url,
                    json=body,
                    headers={"x-goog-api-key": self._api_key, "Content-Type": "application/json"},
                )
        except httpx.HTTPError as exc:
            logger.info("gemini.generate.http_error", extra={"error": type(exc).__name__})
            raise GeminiError("Gemini HTTP error.") from exc
        if response.status_code >= 400:
            logger.info(
                "gemini.generate.bad_status",
                extra={"status_code": response.status_code},
            )
            raise GeminiError(f"Gemini status {response.status_code}.")
        data = response.json()
        text = _first_text(data)
        if not text:
            raise GeminiError("Gemini returned no text.")
        logger.info("gemini.generate.ok", extra={"chars": len(text)})
        return text


def _first_text(payload: dict[str, Any]) -> str:
    """Read candidates[0].content.parts[*].text."""
    candidates = payload.get("candidates") or []
    if not candidates:
        return ""
    parts = ((candidates[0] or {}).get("content") or {}).get("parts") or []
    chunks = [str(part.get("text", "")) for part in parts if isinstance(part, dict)]
    return "".join(chunks).strip()
