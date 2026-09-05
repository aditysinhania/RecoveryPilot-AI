"""JWT auth routes. Routers stay thin."""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Request, status

from app.api.deps import CurrentUserDep, LoggerDep, SessionDep, SettingsDep
from app.core.responses import success_body
from app.schemas.auth import (
    AuthUserOut,
    LoginRequest,
    LogoutRequest,
    RefreshRequest,
    SignupRequest,
    TokenOut,
)
from app.schemas.common import ApiResponse
from app.services import auth_service

router = APIRouter(prefix="/auth", tags=["Auth"])


def _client_meta(request: Request) -> tuple[str | None, str | None]:
    """User-Agent and client IP for session rows. No secrets."""
    agent = request.headers.get("user-agent")
    forwarded = request.headers.get("x-forwarded-for")
    ip = (
        forwarded.split(",")[0].strip()
        if forwarded
        else (request.client.host if request.client else None)
    )
    return agent, ip


@router.post("/signup", status_code=status.HTTP_201_CREATED, response_model=ApiResponse[TokenOut])
def signup(
    payload: SignupRequest,
    request: Request,
    db: SessionDep,
    settings: SettingsDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Register a merchant operator. Returns access + refresh JWTs."""
    agent, ip = _client_meta(request)
    logger.info("auth.signup.start")
    data = auth_service.signup(
        db,
        settings,
        email=str(payload.email),
        password=payload.password,
        full_name=payload.full_name,
        user_agent=agent,
        ip_address=ip,
    )
    logger.info("auth.signup.ok", extra={"user_id": str(data.user.id)})
    return success_body(data=data, message="ok")


@router.post("/login", response_model=ApiResponse[TokenOut])
def login(
    payload: LoginRequest,
    request: Request,
    db: SessionDep,
    settings: SettingsDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Email/password login. Returns access + refresh JWTs."""
    agent, ip = _client_meta(request)
    logger.info("auth.login.start")
    data = auth_service.login(
        db,
        settings,
        email=str(payload.email),
        password=payload.password,
        user_agent=agent,
        ip_address=ip,
    )
    logger.info("auth.login.ok", extra={"user_id": str(data.user.id)})
    return success_body(data=data, message="ok")


@router.post("/refresh", response_model=ApiResponse[TokenOut])
def refresh(
    payload: RefreshRequest,
    request: Request,
    db: SessionDep,
    settings: SettingsDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Rotate the refresh token and issue a new access token."""
    agent, ip = _client_meta(request)
    logger.info("auth.refresh.start")
    data = auth_service.refresh(
        db,
        settings,
        payload.refresh_token,
        user_agent=agent,
        ip_address=ip,
    )
    logger.info("auth.refresh.ok", extra={"user_id": str(data.user.id)})
    return success_body(data=data, message="ok")


@router.post("/logout")
def logout(
    payload: LogoutRequest,
    db: SessionDep,
    settings: SettingsDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Revoke the refresh session. Always succeeds for well-formed tokens."""
    auth_service.logout(db, settings, payload.refresh_token)
    logger.info("auth.logout.ok")
    return success_body(data={"revoked": True}, message="ok")


@router.get("/me", response_model=ApiResponse[AuthUserOut])
def me(
    principal: CurrentUserDep,
    logger: LoggerDep,
) -> dict[str, Any]:
    """Return the authenticated operator. Requires a valid access token."""
    logger.info("auth.me.ok", extra={"user_id": str(principal.user.id)})
    return success_body(data=principal.user, message="ok")
