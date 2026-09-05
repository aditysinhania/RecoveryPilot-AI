"""Auth JWT, password hashing, and HTTP contract tests."""

from __future__ import annotations

from datetime import timedelta
from uuid import uuid4

import pytest
from fastapi.testclient import TestClient
from services.auth.passwords import hash_password, verify_password
from services.auth.tokens import access_payload, decode_token, encode_token, refresh_payload

from app.db.health import ping_database


def test_password_hash_roundtrip() -> None:
    """bcrypt hashes verify and do not store plaintext."""
    hashed = hash_password("correct-horse")
    assert hashed != "correct-horse"
    assert verify_password("correct-horse", hashed) is True
    assert verify_password("wrong-password", hashed) is False


def test_jwt_access_roundtrip() -> None:
    """Access tokens encode sub and typ."""
    user_id = uuid4()
    session_id = uuid4()
    token = encode_token(
        access_payload(user_id, "ops@example.com", None, session_id),
        secret="test-secret",
        algorithm="HS256",
        expires_delta=timedelta(minutes=5),
    )
    payload = decode_token(token, secret="test-secret", algorithm="HS256")
    assert payload["sub"] == str(user_id)
    assert payload["typ"] == "access"
    assert payload["sid"] == str(session_id)


def test_jwt_refresh_roundtrip() -> None:
    """Refresh tokens bind to a session id."""
    user_id = uuid4()
    session_id = uuid4()
    token = encode_token(
        refresh_payload(user_id, session_id),
        secret="test-secret",
        algorithm="HS256",
        expires_delta=timedelta(days=1),
    )
    payload = decode_token(token, secret="test-secret", algorithm="HS256")
    assert payload["typ"] == "refresh"
    assert payload["sid"] == str(session_id)


def test_auth_paths_registered(client: TestClient) -> None:
    """OpenAPI advertises auth, onboarding, and account routes."""
    paths = client.get("/openapi.json").json()["paths"]
    assert "/api/v1/auth/login" in paths
    assert "/api/v1/auth/signup" in paths
    assert "/api/v1/auth/refresh" in paths
    assert "/api/v1/auth/me" in paths
    assert "/api/v1/auth/logout" in paths
    assert "/api/v1/onboarding/merchant" in paths
    assert "/api/v1/account/settings" in paths


def test_me_without_token_is_401(client: TestClient) -> None:
    """Protected routes reject missing bearer tokens."""
    response = client.get("/api/v1/auth/me")
    assert response.status_code == 401
    body = response.json()
    assert body["success"] is False
    assert body["code"] == "unauthorized"


def test_signup_short_password_is_422(client: TestClient) -> None:
    """Pydantic rejects passwords shorter than policy."""
    response = client.post(
        "/api/v1/auth/signup",
        json={"email": "short@example.com", "password": "ab", "full_name": "Ada"},
    )
    assert response.status_code == 422
    body = response.json()
    assert body["success"] is False
    assert "internal server error" not in body.get("error", "").lower()
    assert body.get("message")


def test_login_failure_is_friendly_not_500(client: TestClient) -> None:
    """Postgres down is 503; unknown user is 401. Never a raw 500."""
    response = client.post(
        "/api/v1/auth/login",
        json={"email": "nobody@example.com", "password": "correct-horse"},
    )
    assert response.status_code != 500, response.text
    body = response.json()
    assert body["success"] is False
    assert "internal server error" not in str(body.get("error", "")).lower()
    assert body.get("message") or body.get("error")
    if not ping_database():
        assert response.status_code == 503
        assert body["code"] == "database_unavailable"
    else:
        assert response.status_code == 401
        assert body["code"] == "invalid_credentials"


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for auth signup")
def test_signup_login_me_refresh_logout(client: TestClient) -> None:
    """Full JWT loop against Postgres merchant_users / auth_sessions."""
    email = f"ops-{uuid4().hex[:10]}@example.com"
    password = "correct-horse"
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": password, "full_name": "Ada Merchant"},
    )
    assert signup.status_code == 201, signup.text
    tokens = signup.json()["data"]
    assert tokens["token_type"] == "bearer"
    assert tokens["user"]["email"] == email
    assert tokens["user"]["onboarding_completed"] is False

    me = client.get(
        "/api/v1/auth/me",
        headers={"Authorization": f"Bearer {tokens['access_token']}"},
    )
    assert me.status_code == 200
    assert me.json()["data"]["full_name"] == "Ada Merchant"

    login = client.post("/api/v1/auth/login", json={"email": email, "password": password})
    assert login.status_code == 200
    login_tokens = login.json()["data"]

    refreshed = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_tokens["refresh_token"]},
    )
    assert refreshed.status_code == 200
    new_refresh = refreshed.json()["data"]["refresh_token"]

    reused = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": login_tokens["refresh_token"]},
    )
    assert reused.status_code == 401

    logout = client.post("/api/v1/auth/logout", json={"refresh_token": new_refresh})
    assert logout.status_code == 200

    after = client.post("/api/v1/auth/refresh", json={"refresh_token": new_refresh})
    assert after.status_code == 401


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for onboarding")
def test_onboarding_four_steps(client: TestClient) -> None:
    """Merchant → business → Razorpay → workspace marks onboarding complete."""
    email = f"onboard-{uuid4().hex[:10]}@example.com"
    signup = client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "correct-horse", "full_name": "Onboard User"},
    )
    token = signup.json()["data"]["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    step1 = client.post(
        "/api/v1/onboarding/merchant",
        headers=headers,
        json={
            "merchant_name": "Northwind Yoga",
            "phone": "+919999999999",
            "timezone": "Asia/Kolkata",
        },
    )
    assert step1.status_code == 200, step1.text
    assert step1.json()["data"]["merchant_id"]

    step2 = client.post(
        "/api/v1/onboarding/business",
        headers=headers,
        json={"business_type": "Fitness & Wellness"},
    )
    assert step2.status_code == 200, step2.text

    step3 = client.post(
        "/api/v1/onboarding/razorpay",
        headers=headers,
        json={
            "key_id": "rzp_test_demo",
            "key_secret": "sandbox_secret",
            "webhook_secret": "hook_secret",
        },
    )
    assert step3.status_code == 200, step3.text

    step4 = client.post(
        "/api/v1/onboarding/workspace",
        headers=headers,
        json={"workspace_kind": "empty"},
    )
    assert step4.status_code == 200, step4.text
    body = step4.json()["data"]
    assert body["onboarding_completed"] is True
    assert body["workspace_kind"] == "empty"

    settings = client.get("/api/v1/account/settings", headers=headers)
    assert settings.status_code == 200, settings.text
    snapshot = settings.json()["data"]
    assert snapshot["merchant_name"] == "Northwind Yoga"
    assert snapshot["razorpay_configured"] is True
    assert "sandbox_secret" not in settings.text


@pytest.mark.skipif(not ping_database(), reason="PostgreSQL is required for login failures")
def test_login_wrong_password(client: TestClient) -> None:
    """Wrong password returns a generic 401."""
    email = f"wrong-{uuid4().hex[:10]}@example.com"
    client.post(
        "/api/v1/auth/signup",
        json={"email": email, "password": "correct-horse", "full_name": "Ada"},
    )
    response = client.post("/api/v1/auth/login", json={"email": email, "password": "nope-nope"})
    assert response.status_code == 401
    assert response.json()["code"] == "invalid_credentials"
