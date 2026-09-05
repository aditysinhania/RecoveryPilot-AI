"""Prometheus counters, histograms, and gauges. No recovery-domain logic."""

from __future__ import annotations

import logging
from typing import Any

from prometheus_client import CONTENT_TYPE_LATEST, Counter, Gauge, Histogram, generate_latest

logger = logging.getLogger(__name__)

HTTP_REQUESTS = Counter(
    "recoverypilot_http_requests_total",
    "HTTP requests handled by the API.",
    ("method", "path", "status"),
)
HTTP_LATENCY = Histogram(
    "recoverypilot_http_request_duration_seconds",
    "HTTP request latency in seconds.",
    ("method", "path"),
    buckets=(0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0),
)
WEBHOOKS_RECEIVED = Counter(
    "recoverypilot_webhooks_received_total",
    "Verified Razorpay webhook deliveries (including replays).",
)
WEBHOOKS_REPLAYED = Counter(
    "recoverypilot_webhooks_replayed_total",
    "Duplicate Razorpay webhook deliveries.",
)
ACTIONS_EXECUTED = Counter(
    "recoverypilot_recovery_actions_executed_total",
    "Recovery actions executed through the HTTP adapter.",
)
PAYMENT_LINKS = Counter(
    "recoverypilot_payment_links_generated_total",
    "Payment links returned by execute/schedule HTTP calls.",
)
RETRY_ATTEMPTS = Counter(
    "recoverypilot_retry_attempts_total",
    "Retry attempts reported on execute/schedule HTTP calls.",
)
GEMINI_REQUESTS = Counter(
    "recoverypilot_gemini_requests_total",
    "Gemini generateContent attempts (from structured logs).",
)
GEMINI_FALLBACK = Counter(
    "recoverypilot_gemini_fallback_total",
    "Gemini failures or skipped calls that fall back locally.",
)
GEMINI_CACHE_HITS = Counter(
    "recoverypilot_gemini_cache_hits_total",
    "Gemini explanation cache hits.",
)
SCHEDULER_JOBS = Gauge(
    "recoverypilot_scheduler_jobs",
    "Scheduler job counts by status.",
    ("status",),
)
PAYMENT_LINKS_GAUGE = Gauge(
    "recoverypilot_payment_links_sent",
    "Payment links recorded in recovery_actions (dashboard snapshot).",
)
RETRIES_GAUGE = Gauge(
    "recoverypilot_successful_retries",
    "Successful retries recorded in recovery_actions (dashboard snapshot).",
)

_GEMINI_REQUEST_MESSAGES = frozenset({"gemini.generate.start"})
_GEMINI_FALLBACK_MESSAGES = frozenset(
    {"gemini.generate.failed", "gemini.generate.caught", "gemini.skip_unconfigured"}
)
_GEMINI_CACHE_MESSAGES = frozenset({"gemini.cache.hit"})


class GeminiMetricsLogFilter(logging.Filter):
    """Increment Gemini Prometheus counters from existing log lines.

    Does not change Gemini or explanation business logic.
    """

    def filter(self, record: logging.LogRecord) -> bool:
        """Always pass the record through; side-effect is metric increments."""
        message = record.getMessage()
        if message in _GEMINI_REQUEST_MESSAGES:
            GEMINI_REQUESTS.inc()
        elif message in _GEMINI_FALLBACK_MESSAGES:
            GEMINI_FALLBACK.inc()
        elif message in _GEMINI_CACHE_MESSAGES:
            GEMINI_CACHE_HITS.inc()
        return True


def observe_http(method: str, path: str, status_code: int, duration_seconds: float) -> None:
    """Record one HTTP request. Low-cardinality path templates only."""
    status = str(status_code)
    HTTP_REQUESTS.labels(method=method, path=path, status=status).inc()
    HTTP_LATENCY.labels(method=method, path=path).observe(duration_seconds)


def record_webhook(*, replayed: bool) -> None:
    """Count a verified webhook delivery in the HTTP adapter."""
    WEBHOOKS_RECEIVED.inc()
    if replayed:
        WEBHOOKS_REPLAYED.inc()


def record_action_execution(*, payment_link: str | None, retry_attempts: int) -> None:
    """Count an execute/schedule/replay result in the HTTP adapter."""
    ACTIONS_EXECUTED.inc()
    if payment_link:
        PAYMENT_LINKS.inc()
    if retry_attempts > 0:
        RETRY_ATTEMPTS.inc(retry_attempts)


def refresh_runtime_gauges() -> None:
    """Pull scheduler and action snapshot gauges. Failures must not break /metrics."""
    try:
        from app.services.ops_service import snapshot_runtime_gauges

        snapshot_runtime_gauges()
    except Exception as exc:  # noqa: BLE001 — scrape must stay 200
        logger.info("metrics.gauges.refresh_failed", extra={"error_type": type(exc).__name__})


def render_metrics() -> tuple[bytes, str]:
    """Return Prometheus text and content type."""
    refresh_runtime_gauges()
    return generate_latest(), CONTENT_TYPE_LATEST


def http_snapshot() -> dict[str, Any]:
    """In-process HTTP request count and latency percentiles for the ops UI."""
    request_count = _counter_total(HTTP_REQUESTS)
    p50, p95 = _histogram_percentiles(HTTP_LATENCY, (0.50, 0.95))
    return {
        "request_count": request_count,
        "latency_p50_ms": p50,
        "latency_p95_ms": p95,
    }


def _counter_total(counter: Counter) -> int:
    """Sum a labeled or unlabeled counter."""
    total = 0.0
    for metric in counter.collect():
        for sample in metric.samples:
            if sample.name.endswith("_total"):
                total += sample.value
    return int(total)


def _histogram_percentiles(
    histogram: Histogram,
    percentiles: tuple[float, ...],
) -> tuple[float, ...]:
    """Approximate percentiles from cumulative buckets. Values are milliseconds."""
    buckets: list[tuple[float, float]] = []
    count = 0.0
    for metric in histogram.collect():
        for sample in metric.samples:
            if sample.name.endswith("_bucket"):
                le = sample.labels.get("le")
                if le is None or le == "+Inf":
                    continue
                buckets.append((float(le), sample.value))
            elif sample.name.endswith("_count"):
                count += sample.value
    if not buckets or count <= 0:
        return tuple(0.0 for _ in percentiles)
    buckets.sort(key=lambda item: item[0])
    results: list[float] = []
    for pct in percentiles:
        target = count * pct
        chosen = buckets[-1][0]
        for upper, cumulative in buckets:
            if cumulative >= target:
                chosen = upper
                break
        results.append(round(chosen * 1000, 2))
    return tuple(results)
