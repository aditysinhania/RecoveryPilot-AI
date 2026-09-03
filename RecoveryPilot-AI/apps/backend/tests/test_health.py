"""Health endpoint contract tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config.constants import CORRELATION_ID_HEADER, REQUEST_ID_HEADER


def test_live_returns_200(client: TestClient) -> None:
    """Process liveness must be 200 and must not require Postgres."""
    response = client.get("/api/v1/live")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"]["status"] == "ok"
    assert body["request_id"]
    assert body["correlation_id"]
    assert REQUEST_ID_HEADER in response.headers
    assert CORRELATION_ID_HEADER in response.headers


def test_health_returns_200(client: TestClient) -> None:
    """Combined probe must be 200 even if Postgres is down."""
    response = client.get("/api/v1/health")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "data" in body
    assert body["data"]["version"]
    assert body["data"]["environment"]
    assert body["data"]["database"] in {"connected", "unavailable"}
    assert REQUEST_ID_HEADER in response.headers


def test_health_accepts_incoming_request_id(client: TestClient) -> None:
    """Incoming X-Request-ID is echoed on the response and body."""
    response = client.get("/api/v1/health", headers={REQUEST_ID_HEADER: "test-req-1"})
    assert response.headers[REQUEST_ID_HEADER] == "test-req-1"
    assert response.json()["request_id"] == "test-req-1"


def test_correlation_id_echoed(client: TestClient) -> None:
    """Incoming X-Correlation-ID is echoed; request_id stays independent."""
    response = client.get(
        "/api/v1/live",
        headers={
            REQUEST_ID_HEADER: "req-abc",
            CORRELATION_ID_HEADER: "corr-xyz",
        },
    )
    assert response.status_code == 200
    assert response.headers[REQUEST_ID_HEADER] == "req-abc"
    assert response.headers[CORRELATION_ID_HEADER] == "corr-xyz"
    body = response.json()
    assert body["request_id"] == "req-abc"
    assert body["correlation_id"] == "corr-xyz"


def test_correlation_id_defaults_to_request_id(client: TestClient) -> None:
    """When the client omits X-Correlation-ID, it matches request_id."""
    response = client.get("/api/v1/live", headers={REQUEST_ID_HEADER: "req-only"})
    assert response.headers[CORRELATION_ID_HEADER] == "req-only"
    body = response.json()
    assert body["request_id"] == "req-only"
    assert body["correlation_id"] == "req-only"
