# Observability — Phase 10B

Metrics, JSON logs, health probes, and Sentry. Recovery-domain modules are
not modified; instrumentation lives in FastAPI middleware and HTTP adapters.

---

## Prometheus

Scrape `GET /metrics` (plain Prometheus text, not the JSON envelope).

| Series | Meaning |
| --- | --- |
| `recoverypilot_http_requests_total` | HTTP count (`method`, `path`, `status`) |
| `recoverypilot_http_request_duration_seconds` | HTTP latency histogram |
| `recoverypilot_webhooks_received_total` | Verified webhook deliveries |
| `recoverypilot_webhooks_replayed_total` | Duplicate event ids |
| `recoverypilot_recovery_actions_executed_total` | Execute/schedule/replay HTTP calls |
| `recoverypilot_payment_links_generated_total` | Links returned by those calls |
| `recoverypilot_retry_attempts_total` | Retry attempts on those calls |
| `recoverypilot_scheduler_jobs{status=}` | Gauge: scheduled / running / dead_letter |
| `recoverypilot_payment_links_sent` | Gauge from `recovery_actions` snapshot |
| `recoverypilot_successful_retries` | Gauge from `recovery_actions` snapshot |
| `recoverypilot_gemini_requests_total` | From `gemini.generate.start` logs |
| `recoverypilot_gemini_fallback_total` | From Gemini skip/fail logs |
| `recoverypilot_gemini_cache_hits_total` | From `gemini.cache.hit` logs |

Path labels use FastAPI route templates where available so cardinality stays
bounded. `/metrics` itself is excluded from the HTTP series.

Gemini counters are incremented by a logging filter. Explanation and Gemini
client code is unchanged.

Suggested scrape: 15s. Grafana can graph p95 from the histogram and webhook
rate from `rate(recoverypilot_webhooks_received_total[5m])`.

---

## Structured logs

Every line is one JSON object on stdout:

```json
{
  "timestamp": "...",
  "level": "INFO",
  "logger": "app.core.middleware",
  "message": "http.request",
  "environment": "production",
  "request_id": "...",
  "correlation_id": "...",
  "merchant_id": "...",
  "recovery_case_id": "...",
  "execution_id": "...",
  "method": "GET",
  "path": "/api/v1/live",
  "status_code": 200,
  "latency_ms": 1.2
}
```

`request_id` / `correlation_id` come from `X-Request-ID` / `X-Correlation-ID`
(or are generated). Merchant, case, and execution ids are copied from extra
fields and from UUID path segments. Access logs include latency and status.

Ship container stdout to your log stack (Cloud Logging, Loki, ELK). Do not
log secrets, tokens, or full card/VPA data (existing redaction still applies).

---

## Health probes

| Path | Purpose |
| --- | --- |
| `GET /api/v1/live` | Process liveness |
| `GET /api/v1/ready` | Postgres `SELECT 1` (503 if down) |
| `GET /api/v1/health` | Combined; always 200 |
| `GET /api/v1/health/database` | Same as ready |
| `GET /api/v1/health/scheduler` | Tick thread + queue counts |
| `GET /api/v1/health/gemini` | Key configured vs placeholder (no generateContent) |
| `GET /api/v1/health/razorpay` | Sandbox vs mock (no charges) |
| `GET /api/v1/ops/status` | Aggregated snapshot for the Operations UI |

Gemini and Razorpay probes never call vendor HTTP APIs.

---

## Sentry

Set `SENTRY_DSN` to enable. Empty DSN leaves Sentry off (local/CI default).

- Environment = `APP_ENV`
- Release = `APP_VERSION+BUILD_SHA`
- Traces = `SENTRY_TRACES_SAMPLE_RATE`
- `before_send` drops `ApplicationException` and other 4xx HTTP errors
  (not-found, invalid webhook signature, validation). Unhandled 500s are sent.

---

## Operations Status UI

Route `/operations` reads `GET /api/v1/ops/status` every 15s and shows API,
database, scheduler, Gemini, Razorpay, webhook throughput, HTTP p95, and
build SHA.
