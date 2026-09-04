"""Audit and compliance replay contract tests."""

from __future__ import annotations

from uuid import uuid4

import pytest
from fastapi.testclient import TestClient

from app.db.health import ping_database
from services.audit_service import InvalidAuditFilterError, parse_audit_filters
from shared.enums import ActorType, AuditEventType


def test_audit_paths_registered(client: TestClient) -> None:
    """OpenAPI must advertise the four compliance replay routes."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/audit/events" in paths
    assert "/api/v1/audit/correlation/{correlation_id}" in paths
    assert "/api/v1/audit/cases/{recovery_case_id}" in paths
    assert "/api/v1/audit/cases/{recovery_case_id}/policy" in paths


def test_events_invalid_type_is_400(client: TestClient) -> None:
    """Unknown event_type values use invalid_audit_filter."""
    response = client.get("/api/v1/audit/events", params={"event_type": "NOT_AN_EVENT"})
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "invalid_audit_filter"


def test_events_invalid_date_range_is_400(client: TestClient) -> None:
    """Inverted date bounds use invalid_audit_filter."""
    response = client.get(
        "/api/v1/audit/events",
        params={"date_from": "2026-09-02", "date_to": "2026-09-01"},
    )
    assert response.status_code == 400
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "invalid_audit_filter"


def test_parse_audit_filters_actor_enum() -> None:
    """ActorType tokens are parsed as actor_type, not actor_name."""
    filters = parse_audit_filters(actor="POLICY_ENGINE", event_type="POLICY_EVALUATED")
    assert filters.actor_type == ActorType.POLICY_ENGINE
    assert filters.actor_name is None
    assert filters.event_type == AuditEventType.POLICY_EVALUATED


def test_parse_audit_filters_actor_name() -> None:
    """Non-enum actor values are treated as an actor_name substring."""
    filters = parse_audit_filters(actor="Diagnosis Agent")
    assert filters.actor_type is None
    assert filters.actor_name == "Diagnosis Agent"


def test_parse_audit_filters_rejects_bad_event_type() -> None:
    """Unknown event_type raises InvalidAuditFilterError."""
    with pytest.raises(InvalidAuditFilterError):
        parse_audit_filters(event_type="BOUNCED")


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for audit 404")
def test_unknown_case_timeline_is_404(client: TestClient) -> None:
    """A well-formed case id with no row returns audit_event_not_found."""
    response = client.get(f"/api/v1/audit/cases/{uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "audit_event_not_found"


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for correlation 404")
def test_unknown_correlation_is_404(client: TestClient) -> None:
    """A token with no matching rows returns correlation_not_found."""
    response = client.get("/api/v1/audit/correlation/does-not-exist")
    assert response.status_code == 404
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "correlation_not_found"
