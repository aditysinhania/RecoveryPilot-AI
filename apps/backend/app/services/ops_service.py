"""Operations snapshot for the status page and Prometheus gauges."""

from __future__ import annotations

from datetime import UTC, datetime

from services.action_orchestrator_service import get_dashboard_summary
from services.razorpay_webhook_service import build_webhook_service
from sqlalchemy.orm import Session

from app.config.settings import Settings
from app.core.metrics import (
    ACTIONS_EXECUTED,
    PAYMENT_LINKS_GAUGE,
    RETRIES_GAUGE,
    SCHEDULER_JOBS,
    _counter_total,
    http_snapshot,
)
from app.db.session import SessionLocal
from app.schemas.ops import (
    HttpSnapshot,
    OpsStatusResponse,
    ProbeComponent,
    WebhookThroughput,
)
from app.services.health_service import (
    probe_database,
    probe_gemini,
    probe_razorpay,
    probe_scheduler,
)
from app.utils.time import isoformat_now


def snapshot_runtime_gauges() -> None:
    """Refresh scheduler and action gauges from PostgreSQL. Safe no-op if DB is down."""
    db = SessionLocal()
    try:
        clock = datetime.now(UTC)
        summary = get_dashboard_summary(db, None, as_of=clock)
        queue = summary.scheduler_queue
        SCHEDULER_JOBS.labels(status="scheduled").set(queue.scheduled)
        SCHEDULER_JOBS.labels(status="running").set(queue.running)
        SCHEDULER_JOBS.labels(status="dead_letter").set(queue.dead_letter)
        PAYMENT_LINKS_GAUGE.set(summary.payment_links_sent)
        RETRIES_GAUGE.set(summary.successful_retries)
    except Exception:
        SCHEDULER_JOBS.labels(status="scheduled").set(0)
        SCHEDULER_JOBS.labels(status="running").set(0)
        SCHEDULER_JOBS.labels(status="dead_letter").set(0)
    finally:
        db.close()


def _webhook_throughput(db: Session | None) -> WebhookThroughput:
    """Inbox KPIs, or zeros when the session cannot query."""
    if db is None:
        return WebhookThroughput()
    try:
        counts = build_webhook_service(db).summary()
        return WebhookThroughput(
            received=counts.received,
            processed=counts.processed,
            replayed=counts.replayed,
            failed=counts.failed,
        )
    except Exception:  # noqa: BLE001
        return WebhookThroughput()


def _dashboard_counts(db: Session | None) -> tuple[int, int]:
    """Payment links and retries from the existing orchestrator summary."""
    if db is None:
        return 0, 0
    try:
        summary = get_dashboard_summary(db, None)
        return summary.payment_links_sent, summary.successful_retries
    except Exception:  # noqa: BLE001
        return 0, 0


def ops_status(
    settings: Settings,
    db: Session | None,
    *,
    database_ok: bool | None = None,
) -> OpsStatusResponse:
    """Aggregate probes, webhook throughput, and HTTP latency for operators."""
    if database_ok is False:
        database = ProbeComponent(
            name="database",
            status="unavailable",
            detail="PostgreSQL did not answer SELECT 1",
            mode="postgresql",
        )
    elif database_ok is True:
        database = ProbeComponent(
            name="database",
            status="ok",
            detail="connected",
            mode="postgresql",
        )
    else:
        database = probe_database()
    scheduler = probe_scheduler(settings, db)
    gemini = probe_gemini(settings)
    razorpay = probe_razorpay(settings)
    api = ProbeComponent(name="api", status="ok", detail="process up", mode=settings.app_env)
    webhooks = _webhook_throughput(db)
    links, retries = _dashboard_counts(db)
    http = HttpSnapshot.model_validate(http_snapshot())
    overall = "ok"
    if database.status != "ok":
        overall = "degraded"
    elif scheduler.status not in {"ok", "disabled"}:
        overall = "degraded"
    return OpsStatusResponse(
        status=overall,
        environment=settings.app_env,
        version=settings.app_version,
        api_version=settings.api_version,
        build_sha=settings.build_sha,
        app_name=settings.app_name,
        timestamp=isoformat_now(),
        api=api,
        database=database,
        scheduler=scheduler,
        gemini=gemini,
        razorpay=razorpay,
        webhooks=webhooks,
        http=http,
        payment_links_sent=links,
        successful_retries=retries,
        recovery_actions_executed=_counter_total(ACTIONS_EXECUTED),
    )
