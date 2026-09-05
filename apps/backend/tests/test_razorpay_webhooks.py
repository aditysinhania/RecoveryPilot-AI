"""Razorpay webhook ingest tests. No live Razorpay HTTP."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any
from uuid import UUID, uuid4
from zoneinfo import ZoneInfo

import pytest
from fastapi.testclient import TestClient

from app.config.constants import CORRELATION_ID_HEADER, REQUEST_ID_HEADER
from app.config.settings import get_settings
from app.db.session import get_db
from integrations.razorpay import SIGNATURE_HEADER, expected_webhook_signature, verify_webhook_signature
from services.razorpay_webhook_service import build_webhook_service
from services.razorpay_webhooks.constants import DISPLAY_WEBHOOK_REPLAY
from services.razorpay_webhooks.service import RazorpayWebhookService

IST = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 9, 5, 12, 0, tzinfo=IST)
SECRET = "placeholder_webhook_secret"


class _DummySession:
    """Stand-in session so HTTP tests never open PostgreSQL."""

    def commit(self) -> None:
        return None

    def rollback(self) -> None:
        return None

    def close(self) -> None:
        return None


def _body(
    event: str,
    event_id: str,
    *,
    case_id: UUID | None = None,
    payment_id: str = "pay_test_1",
) -> dict[str, Any]:
    """Minimal Razorpay webhook JSON."""
    """Minimal Razorpay webhook JSON."""
    notes = {"recovery_case_id": str(case_id)} if case_id is not None else {}
    return {
        "id": event_id,
        "event": event,
        "payload": {
            "payment": {
                "entity": {
                    "id": payment_id,
                    "notes": notes,
                }
            }
        },
    }


def _raw(payload: dict[str, Any]) -> bytes:
    """Stable JSON bytes for HMAC."""
    return json.dumps(payload, separators=(",", ":"), sort_keys=True).encode("utf-8")


def _sign(raw: bytes, secret: str = SECRET) -> str:
    """HMAC-SHA256 hex matching Razorpay's webhook scheme."""
    return expected_webhook_signature(raw, secret)


def _service() -> RazorpayWebhookService:
    """In-memory inbox + orchestrator. Notes-only case mapping."""
    return build_webhook_service(db=None)


def test_verify_webhook_signature_accepts_matching_hmac() -> None:
    """Valid HMAC-SHA256 of the raw body is accepted."""
    raw = b'{"id":"evt_ok","event":"payment.captured"}'
    assert verify_webhook_signature(raw, _sign(raw), SECRET) is True


def test_verify_webhook_signature_rejects_wrong_secret() -> None:
    """A signature produced with a different secret is rejected."""
    raw = b'{"id":"evt_bad_secret"}'
    forged = _sign(raw, "other-secret")
    assert verify_webhook_signature(raw, forged, SECRET) is False


def test_verify_webhook_signature_rejects_empty_secret() -> None:
    """Missing webhook secret never verifies."""
    raw = b"{}"
    assert verify_webhook_signature(raw, _sign(raw), "") is False


def test_invalid_signature_returns_401(client: TestClient) -> None:
    """POST /webhooks/razorpay returns 401 and does not persist."""
    raw = _raw(_body("payment.captured", "evt_http_bad"))
    response = client.post(
        "/api/v1/webhooks/razorpay",
        content=raw,
        headers={
            SIGNATURE_HEADER: "not-a-valid-hmac",
            "Content-Type": "application/json",
        },
    )
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "invalid_webhook_signature"


def test_missing_signature_returns_401(client: TestClient) -> None:
    """Omitting X-Razorpay-Signature is treated as invalid."""
    raw = _raw(_body("payment.captured", "evt_http_missing"))
    response = client.post(
        "/api/v1/webhooks/razorpay",
        content=raw,
        headers={"Content-Type": "application/json"},
    )
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_webhook_signature"


def test_duplicate_event_is_idempotent() -> None:
    """The same razorpay_event_id is stored once and marked replayed on retry."""
    service = _service()
    case_id = uuid4()
    raw = _raw(_body("payment.captured", "evt_dup_1", case_id=case_id))
    first = service.ingest(raw, request_id="req-1", correlation_id="corr-1", as_of=AS_OF)
    second = service.ingest(raw, request_id="req-2", correlation_id="corr-2", as_of=AS_OF)
    assert first.replayed is False
    assert first.processed is True
    assert second.replayed is True
    assert second.razorpay_event_id == "evt_dup_1"
    summary = service.summary()
    assert summary.received == 1
    assert summary.replayed == 1
    assert summary.processed == 1


def test_replay_appends_webhook_replay_audit() -> None:
    """Duplicate deliveries append WEBHOOK_REPLAY with request_id and correlation_id."""
    service = _service()
    case_id = uuid4()
    raw = _raw(_body("payment.failed", "evt_replay_1", case_id=case_id))
    service.ingest(raw, request_id="req-a", correlation_id="corr-a", as_of=AS_OF)
    service.ingest(raw, request_id="req-b", correlation_id="corr-b", as_of=AS_OF)
    audits = service._action_store.audits  # noqa: SLF001 — inspect in-memory store
    replay = [
        item
        for item in audits
        if item["payload"].get("display_type") == DISPLAY_WEBHOOK_REPLAY
    ]
    assert len(replay) == 1
    payload = replay[0]["payload"]
    assert payload["replay"] is True
    assert payload["webhook_replay"] is True
    assert payload["duplicate"] is True
    assert payload["request_id"] == "req-b"
    assert payload["correlation_id"] == "corr-b"
    assert payload["razorpay_event_id"] == "evt_replay_1"


def test_unknown_event_type_is_stored_not_dispatched() -> None:
    """Unsupported events are persisted and processed without orchestrator dispatch."""
    service = _service()
    case_id = uuid4()
    raw = _raw(_body("invoice.paid", "evt_unknown_1", case_id=case_id))
    result = service.ingest(raw, request_id="req-u", correlation_id="corr-u", as_of=AS_OF)
    assert result.unknown_event is True
    assert result.processed is True
    assert result.replayed is False
    assert service._action_store.audits == []  # noqa: SLF001
    stored = service._inbox.get("evt_unknown_1")  # noqa: SLF001
    assert stored is not None
    assert stored.signature_verified is True
    assert stored.processed_at is not None


def test_supported_event_dispatches_through_orchestrator() -> None:
    """payment.captured maps via notes.recovery_case_id and writes an audit trail."""
    service = _service()
    case_id = uuid4()
    raw = _raw(_body("payment.captured", "evt_cap_1", case_id=case_id))
    result = service.ingest(
        raw,
        request_id="req-cap",
        correlation_id="corr-cap",
        as_of=AS_OF,
    )
    assert result.processed is True
    assert result.unknown_event is False
    assert result.recovery_case_id == case_id
    audits = service._action_store.audits  # noqa: SLF001
    assert len(audits) == 1
    payload = audits[0]["payload"]
    assert payload["request_id"] == "req-cap"
    assert payload["correlation_id"] == "corr-cap"
    assert payload["event"] == "payment.captured"
    assert audits[0]["event_type"].value == "PAYMENT_CAPTURED"


def test_http_valid_signature_ingests_and_summary(
    client: TestClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Signed POST stores the event; GET /webhooks/summary returns inbox counts."""
    service = _service()
    dummy = _DummySession()
    monkeypatch.setattr(
        "app.services.webhook_service.build_webhook_service", lambda db=None: service
    )
    monkeypatch.setattr("app.services.webhook_service.SessionLocal", lambda: dummy)

    def _dummy_db() -> Any:
        """Yield the in-memory dummy session for GET /summary."""
        yield dummy

    client.app.dependency_overrides[get_db] = _dummy_db
    try:
        settings = get_settings()
        case_id = uuid4()
        payload = _body("payment.authorized", "evt_http_ok", case_id=case_id)
        raw = _raw(payload)
        response = client.post(
            "/api/v1/webhooks/razorpay",
            content=raw,
            headers={
                SIGNATURE_HEADER: _sign(raw, settings.razorpay_webhook_secret),
                "Content-Type": "application/json",
                REQUEST_ID_HEADER: "req-http-ok",
                CORRELATION_ID_HEADER: "corr-http-ok",
            },
        )
        assert response.status_code == 200
        data = response.json()["data"]
        assert data["signature_verified"] is True
        assert data["razorpay_event_id"] == "evt_http_ok"
        assert data["replayed"] is False
        assert response.json()["request_id"] == "req-http-ok"
        assert response.json()["correlation_id"] == "corr-http-ok"

        summary = client.get("/api/v1/webhooks/summary")
        assert summary.status_code == 200
        counts = summary.json()["data"]
        assert counts["received"] == 1
        assert counts["processed"] == 1
        assert counts["replayed"] == 0
        assert counts["failed"] == 0
    finally:
        client.app.dependency_overrides.pop(get_db, None)
