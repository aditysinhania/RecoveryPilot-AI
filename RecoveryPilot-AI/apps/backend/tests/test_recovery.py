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
    """OpenAPI must advertise recovery queue, case, timeline, and audit routes."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/recovery/queue" in paths
    assert "/api/v1/recovery/summary" in paths
    assert "/api/v1/recovery/cases/{recovery_case_id}" in paths
    assert "/api/v1/recovery/cases/{recovery_case_id}/timeline" in paths
    assert "/api/v1/recovery/cases/{recovery_case_id}/audit" in paths


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


_FITLIFE_MERCHANT_ID = "6dad1d88-3e3f-5788-b10e-31467d72c022"


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for seeded summary")
def test_summary_open_cases_counts_active_statuses(client: TestClient) -> None:
    """Seeded FitLife open_cases is WAITING_RETRY + WAITING_PROMISE + ESCALATED."""
    response = client.get(
        "/api/v1/recovery/summary",
        params={"merchant_id": _FITLIFE_MERCHANT_ID},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    data = body["data"]
    assert data["open_cases"] == 146
    assert data["open_cases"] == (
        data["waiting_retry"] + data["waiting_promise"] + data["escalated_cases"]
    )


_AUDIT_FIELDS = (
    "event_id",
    "event_type",
    "actor",
    "status",
    "request_id",
    "correlation_id",
    "metadata",
    "created_at",
)


def _seeded_audit_sample(client: TestClient) -> tuple[str, list[dict[str, object]]]:
    """Load a recovered FitLife case that has a non-empty audit trail."""
    queue = client.get(
        "/api/v1/recovery/queue",
        params={"status": "RECOVERED", "page": 1, "page_size": 25},
    )
    assert queue.status_code == 200
    rows = queue.json()["data"]
    assert rows, "seeded queue has no RECOVERED cases"
    for row in rows:
        case_id = str(row["recovery_case_id"])
        response = client.get(f"/api/v1/recovery/cases/{case_id}/audit")
        assert response.status_code == 200
        events = response.json()["data"]
        if events:
            return case_id, events
    raise AssertionError("no seeded RECOVERED case has audit_logs rows")


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for seeded audit")
def test_case_audit_returns_seeded_events(client: TestClient) -> None:
    """Seeded cases return diagnosis, policy, planner, execution, and webhook rows when present."""
    _case_id, events = _seeded_audit_sample(client)
    assert all(key in events[0] for key in _AUDIT_FIELDS)
    types = {str(item["event_type"]) for item in events}
    present = {
        "diagnosis": types & {"DIAGNOSIS_COMPLETED"},
        "policy": types & {"POLICY_EVALUATED"},
        "planner": types & {"ACTION_SCHEDULED"},
        "execution": types & {"ACTION_EXECUTED", "ACTION_SKIPPED", "PAYMENT_CAPTURED"},
        "webhook": types & {"CASE_OPENED", "PAYMENT_CAPTURED"},
    }
    assert present["diagnosis"] or present["policy"] or present["webhook"]
    for family, matched in present.items():
        if matched:
            assert matched, f"missing {family} events"


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for audit order")
def test_case_audit_events_newest_first(client: TestClient) -> None:
    """Case audit listings are sorted by created_at descending."""
    _case_id, events = _seeded_audit_sample(client)
    created = [str(item["created_at"]) for item in events]
    assert created == sorted(created, reverse=True)


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for empty audit")
def test_unknown_case_audit_is_empty_200(client: TestClient) -> None:
    """Unknown UUID returns 200 with an empty audit list, not 404."""
    response = client.get(f"/api/v1/recovery/cases/{uuid4()}/audit")
    assert response.status_code == 200
    body = response.json()
    assert body["success"] is True
    assert body["data"] == []
