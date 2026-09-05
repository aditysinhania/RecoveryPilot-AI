"""JSON structured logging factory."""

from __future__ import annotations

import json
import logging
import sys
from datetime import UTC, datetime
from typing import Any

from app.config.settings import settings
from app.core.metrics import GeminiMetricsLogFilter
from app.utils.request_id import (
    get_correlation_id,
    get_execution_id,
    get_merchant_id,
    get_recovery_case_id,
    get_request_id,
)

_CONTEXT_KEYS = (
    "method",
    "path",
    "status_code",
    "latency_ms",
    "merchant_id",
    "recovery_case_id",
    "execution_id",
    "case_id",
)


class JsonLogFormatter(logging.Formatter):
    """Emit one JSON object per log line."""

    def format(self, record: logging.LogRecord) -> str:
        """Serialize a log record including request context when present."""
        payload: dict[str, Any] = {
            "timestamp": datetime.now(UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "environment": settings.app_env,
            "request_id": getattr(record, "request_id", None) or get_request_id(),
            "correlation_id": getattr(record, "correlation_id", None) or get_correlation_id(),
            "merchant_id": getattr(record, "merchant_id", None) or get_merchant_id() or None,
            "recovery_case_id": getattr(record, "recovery_case_id", None)
            or getattr(record, "case_id", None)
            or get_recovery_case_id()
            or None,
            "execution_id": getattr(record, "execution_id", None) or get_execution_id() or None,
        }
        for key in _CONTEXT_KEYS:
            if key in {"merchant_id", "recovery_case_id", "execution_id", "case_id"}:
                continue
            value = getattr(record, key, None)
            if value is not None:
                payload[key] = value
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def configure_logging() -> None:
    """Configure root logging once for the API process."""
    level = getattr(logging, settings.log_level, logging.INFO)
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLogFormatter())
    handler.addFilter(GeminiMetricsLogFilter())
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level)


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a named logger under the RecoveryPilot hierarchy."""
    return logging.getLogger(name or "recoverypilot")
