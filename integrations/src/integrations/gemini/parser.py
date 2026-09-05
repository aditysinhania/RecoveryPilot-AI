"""Parse Gemini text into a JSON object. No domain models here."""

from __future__ import annotations

import json
import logging
import re
from typing import Any

logger = logging.getLogger(__name__)

_FENCE = re.compile(r"```(?:json)?\s*([\s\S]*?)```", re.IGNORECASE)


def extract_json_object(text: str | None) -> dict[str, Any] | None:
    """Pull the first JSON object out of a Gemini response.

    Args:
        text: Raw model output, possibly wrapped in markdown fences.

    Returns:
        A dict, or ``None`` when parsing fails. Never raises.
    """
    if not text or not text.strip():
        return None
    stripped = text.strip()
    fenced = _FENCE.search(stripped)
    candidate = fenced.group(1).strip() if fenced else stripped
    start = candidate.find("{")
    end = candidate.rfind("}")
    if start < 0 or end <= start:
        logger.info("gemini.parse.no_object")
        return None
    blob = candidate[start : end + 1]
    try:
        parsed = json.loads(blob)
    except json.JSONDecodeError:
        logger.info("gemini.parse.json_error")
        return None
    if not isinstance(parsed, dict):
        logger.info("gemini.parse.not_object")
        return None
    logger.info("gemini.parse.ok", extra={"keys": list(parsed.keys())[:12]})
    return parsed


def text_within(value: str, *, minimum: int, maximum: int) -> bool:
    """True when ``value`` length is inside ``[minimum, maximum]``."""
    n = len(value.strip())
    return minimum <= n <= maximum
