"""Recovery queue API contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.health import ping_database
from services.recovery_service import (
    InvalidDateRangeError,
    InvalidFilterError,
    parse_queue_filters,
)


def test_recovery_paths_registered(client: TestClient) -> None:
    """OpenAPI must advertise the four recovery queue routes."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/recovery/queue" in paths
    assert "/api/v1/recovery/summary" in paths
    assert "/api/v1/recovery/cases/{recovery_case_id}" in paths
    assert "/api/v1/recovery/cases/{recovery_case_id}/timeline" in paths


def test_queue_invalid_status_is_400(client: TestClient) -> None:
    """Unknown status values use invalid_filter, not a generic 422."""
    response = client.get("/api/v1/recovery/queue", params={"status": "NOT_A_STATUS"})
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "invalid_filter"


def test_queue_invalid_date_range_is_400(client: TestClient) -> None:
    """date_from after date_to is invalid_date_range."""
    response = client.get(
        "/api/v1/recovery/queue",
        params={"date_from": "2026-09-02", "date_to": "2026-09-01"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "invalid_date_range"


def test_parse_queue_filters_priority_band() -> None:
    """HIGH maps to a minimum priority_score of 0.8."""
    filters = parse_queue_filters(priority="HIGH")
    assert filters.min_priority == 0.8
    assert filters.max_priority is None


def test_parse_queue_filters_rejects_bad_enum() -> None:
    """Unknown failure_reason raises InvalidFilterError."""
    with pytest.raises(InvalidFilterError):
        parse_queue_filters(failure_reason="BOUNCED")


def test_parse_queue_filters_rejects_inverted_dates() -> None:
    """Inverted date bounds raise InvalidDateRangeError."""
    with pytest.raises(InvalidDateRangeError):
        parse_queue_filters(date_from="2026-02-01", date_to="2026-01-01")


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for case 404")
def test_unknown_recovery_case_is_404(client: TestClient) -> None:
    """A well-formed id with no row returns recovery_case_not_found."""
    response = client.get(f"/api/v1/recovery/cases/{uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "recovery_case_not_found"


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for queue list")
def test_queue_returns_paginated_metadata(client: TestClient) -> None:
    """Queue responses include total_records, total_pages, and next/prev flags."""
    response = client.get(
        "/api/v1/recovery/queue",
        params={"page": 1, "page_size": 10},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert "total_records" in body
    assert "total_pages" in body
    assert "has_next" in body
    assert "has_previous" in body
    assert body["page"] == 1
    assert body["page_size"] == 10
    assert isinstance(body["data"], list)
