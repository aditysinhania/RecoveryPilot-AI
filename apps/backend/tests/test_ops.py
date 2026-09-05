"""Observability probes: metrics, health extensions, ops snapshot."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config.constants import REQUEST_ID_HEADER
from app.config.logging import JsonLogFormatter
from app.core.exceptions import RecoveryNotFoundError
from app.core.sentry import _before_send


def test_metrics_endpoint_exposes_prometheus(client: TestClient) -> None:
    """GET /metrics is Prometheus text with HTTP and domain series."""
    client.get("/api/v1/live")
    response = client.get("/metrics")
    assert response.status_code == 200
    body = response.text
    assert "recoverypilot_http_requests_total" in body
    assert "recoverypilot_webhooks_received_total" in body
    assert "recoverypilot_scheduler_jobs" in body
    assert "recoverypilot_gemini_requests_total" in body


def test_health_gemini_and_razorpay(client: TestClient) -> None:
    """Gemini and Razorpay probes are 200 and never call live vendors."""
    gemini = client.get("/api/v1/health/gemini")
    assert gemini.status_code == 200
    gemini_data = gemini.json()["data"]
    assert gemini_data["name"] == "gemini"
    assert gemini_data["status"] in {"ok", "unconfigured"}
    razorpay = client.get("/api/v1/health/razorpay")
    assert razorpay.status_code == 200
    assert razorpay.json()["data"]["mode"] in {"mock", "sandbox"}


def test_health_scheduler(client: TestClient) -> None:
    """Scheduler probe reports enabled/thread state without ticking jobs."""
    response = client.get("/api/v1/health/scheduler")
    assert response.status_code == 200
    data = response.json()["data"]
    assert "enabled" in data
    assert "thread_alive" in data
    assert data["status"] in {"ok", "disabled", "stopped"}


def test_ops_status_includes_version_and_probes(client: TestClient) -> None:
    """Operations snapshot carries build info and dependency probes."""
    response = client.get("/api/v1/ops/status", headers={REQUEST_ID_HEADER: "ops-req-1"})
    assert response.status_code == 200
    body = response.json()
    assert body["request_id"] == "ops-req-1"
    data = body["data"]
    assert data["version"]
    assert data["build_sha"]
    assert data["api"]["status"] == "ok"
    assert data["database"]["name"] == "database"
    assert "webhooks" in data
    assert "http" in data
    assert data["gemini"]["name"] == "gemini"
    assert data["razorpay"]["name"] == "razorpay"


def test_json_logs_include_request_context() -> None:
    """JSON formatter stamps request_id, correlation_id, and case identifiers."""
    import logging

    record = logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg="probe",
        args=(),
        exc_info=None,
    )
    record.request_id = "req-log"
    record.correlation_id = "corr-log"
    record.merchant_id = "merchant-1"
    record.recovery_case_id = "case-1"
    record.execution_id = "exec-1"
    record.status_code = 200
    record.latency_ms = 12.5
    line = JsonLogFormatter().format(record)
    assert '"request_id": "req-log"' in line
    assert '"correlation_id": "corr-log"' in line
    assert '"merchant_id": "merchant-1"' in line
    assert '"recovery_case_id": "case-1"' in line
    assert '"execution_id": "exec-1"' in line
    assert '"latency_ms": 12.5' in line
    assert '"status_code": 200' in line


def test_sentry_drops_business_errors() -> None:
    """Expected ApplicationException events are not sent to Sentry."""
    dropped = _before_send(
        {"message": "not found"},
        {"exc_info": (RecoveryNotFoundError, RecoveryNotFoundError("missing"), None)},
    )
    assert dropped is None
    kept = _before_send(
        {"message": "boom"},
        {"exc_info": (RuntimeError, RuntimeError("boom"), None)},
    )
    assert kept is not None
