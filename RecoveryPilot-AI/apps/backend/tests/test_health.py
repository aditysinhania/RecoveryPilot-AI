"""Health endpoint contract tests."""

from __future__ import annotations

from fastapi.testclient import TestClient

from app.config.constants import REQUEST_ID_HEADER


def test_health_returns_200(client: TestClient) -> None:
    """Liveness probe must be 200 even if Postgres is down."""
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
    """Incoming X-Request-ID is echoed on the response."""
    response = client.get("/api/v1/health", headers={REQUEST_ID_HEADER: "test-req-1"})
    assert response.headers[REQUEST_ID_HEADER] == "test-req-1"
    assert response.json()["request_id"] == "test-req-1"
