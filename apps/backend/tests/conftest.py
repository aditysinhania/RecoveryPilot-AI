"""Pytest fixtures for the FastAPI foundation tests."""

from __future__ import annotations

import os

os.environ["APP_ENV"] = "local"
os.environ["API_VERSION"] = "v1"
os.environ.setdefault("LOG_LEVEL", "WARNING")
os.environ["ACTION_SCHEDULER_ENABLED"] = "false"

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from app.config.settings import get_settings
from app.core.lifespan import create_app


@pytest.fixture(scope="session")
def client() -> Generator[TestClient, None, None]:
    """Session-scoped TestClient with lifespan (DB ping may fail locally)."""
    get_settings.cache_clear()
    with TestClient(create_app()) as test_client:
        yield test_client
