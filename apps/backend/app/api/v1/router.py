"""Central v1 router. Domain modules register here, not in ``main.py``."""

from __future__ import annotations

from fastapi import APIRouter

from app.api.v1 import (
    account,
    actions,
    audit,
    auth,
    health,
    merchants,
    onboarding,
    ops,
    recovery,
    simulator,
    webhooks,
)

api_v1_router = APIRouter()
api_v1_router.include_router(health.router)
api_v1_router.include_router(auth.router)
api_v1_router.include_router(onboarding.router)
api_v1_router.include_router(account.router)
api_v1_router.include_router(merchants.router)
api_v1_router.include_router(recovery.router)
api_v1_router.include_router(audit.router)
api_v1_router.include_router(simulator.router)
api_v1_router.include_router(actions.router)
api_v1_router.include_router(webhooks.router)
api_v1_router.include_router(ops.router)
