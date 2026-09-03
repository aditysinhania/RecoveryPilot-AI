"""Merchant dashboard route contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.health import ping_database

_MISSING_MERCHANT = "00000000-0000-4000-8000-000000000099"


def test_merchant_dashboard_paths_registered(client: TestClient) -> None:
    """OpenAPI must advertise the four read-only dashboard routes."""
    schema = client.get("/openapi.json").json()
    paths = schema["paths"]
    assert "/api/v1/merchants/{merchant_id}/summary" in paths
    assert "/api/v1/merchants/{merchant_id}/metrics" in paths
    assert "/api/v1/merchants/{merchant_id}/payments" in paths
    assert "/api/v1/merchants/{merchant_id}/failures" in paths
    assert "/api/v1/live" in paths
    assert "/api/v1/ready" in paths


def test_merchant_invalid_uuid_is_422(client: TestClient) -> None:
    """Path merchant_id must be a UUID."""
    response = client.get("/api/v1/merchants/not-a-uuid/summary")
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "validation_error"


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for merchant 404")
def test_unknown_merchant_summary_is_404(client: TestClient) -> None:
    """A well-formed id with no row returns merchant_not_found."""
    response = client.get(f"/api/v1/merchants/{_MISSING_MERCHANT}/summary")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "merchant_not_found"


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for merchant 404")
def test_unknown_merchant_payments_is_404(client: TestClient) -> None:
    """Payments listing 404s for an unknown merchant rather than an empty page."""
    response = client.get(
        f"/api/v1/merchants/{uuid4()}/payments",
        params={"page": 1, "page_size": 10},
    )
    assert response.status_code == 404
    assert response.json()["code"] == "merchant_not_found"
