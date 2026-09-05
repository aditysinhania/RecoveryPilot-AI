"""Read-only dependency probes. Does not call live Gemini or Razorpay APIs."""

from __future__ import annotations

from datetime import UTC, datetime

from integrations.gemini.gemini_client import GeminiClient
from integrations.razorpay import RazorpaySandboxClient
from services.scheduler.service import ActionScheduler
from services.scheduler.sqlalchemy_store import SqlAlchemySchedulerStore
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.core.scheduler_worker import is_scheduler_thread_alive
from app.db.health import ping_database
from app.schemas.ops import ProbeComponent, SchedulerHealth


def probe_database() -> ProbeComponent:
    """SQLAlchemy ``SELECT 1``."""
    ok = ping_database()
    return ProbeComponent(
        name="database",
        status="ok" if ok else "unavailable",
        detail="connected" if ok else "PostgreSQL did not answer SELECT 1",
        mode="postgresql",
    )


def probe_gemini(settings: Settings) -> ProbeComponent:
    """Report whether a real Gemini key is configured. No generateContent call."""
    client = GeminiClient(
        api_key=settings.gemini_api_key,
        model=settings.gemini_model,
        temperature=settings.gemini_temperature,
        max_output_tokens=settings.gemini_max_output_tokens,
    )
    available = client.is_available()
    return ProbeComponent(
        name="gemini",
        status="ok" if available else "unconfigured",
        detail=settings.gemini_model,
        mode="live" if available else "placeholder",
    )


def probe_razorpay(settings: Settings) -> ProbeComponent:
    """Report Sandbox vs mock mode. Does not create charges."""
    client = RazorpaySandboxClient(
        key_id=settings.razorpay_key_id,
        key_secret=settings.razorpay_key_secret,
    )
    live = client.is_live_sandbox()
    return ProbeComponent(
        name="razorpay",
        status="ok",
        detail="Razorpay Sandbox" if live else "mock Sandbox (placeholder keys)",
        mode="sandbox" if live else "mock",
    )


def probe_scheduler(settings: Settings, db: Session | None) -> SchedulerHealth:
    """Daemon thread plus queue gauges. Does not tick due jobs."""
    enabled = settings.action_scheduler_enabled
    alive = is_scheduler_thread_alive()
    scheduled = 0
    running = 0
    dead_letter = 0
    if db is not None:
        try:
            store = SqlAlchemySchedulerStore(db)
            metrics = ActionScheduler(store=store).queue_metrics(datetime.now(UTC))
            scheduled = metrics.scheduled
            running = metrics.running
            dead_letter = metrics.dead_letter
        except Exception:  # noqa: BLE001 — health stays up if the table is missing
            pass
    if not enabled:
        status = "disabled"
        detail = "ACTION_SCHEDULER_ENABLED=false"
    elif alive:
        status = "ok"
        detail = "tick thread running"
    else:
        status = "stopped"
        detail = "tick thread is not alive"
    return SchedulerHealth(
        status=status,
        enabled=enabled,
        thread_alive=alive,
        scheduled=scheduled,
        running=running,
        dead_letter=dead_letter,
        detail=detail,
    )
