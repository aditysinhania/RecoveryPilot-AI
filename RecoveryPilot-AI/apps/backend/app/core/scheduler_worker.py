"""Background tick for WAIT_FOR_PAYDAY, HONOUR_PROMISE_TO_PAY, and backoff retries."""

from __future__ import annotations

import logging
import threading

from app.config.settings import Settings
from app.db.session import SessionLocal

logger = logging.getLogger(__name__)

_stop = threading.Event()
_thread: threading.Thread | None = None


def _tick_once() -> None:
    """Open a session, run due work, commit. Never raises to the worker loop."""
    from integrations.razorpay import RazorpaySandboxClient
    from services.action_orchestrator_service import tick_due
    from services.razorpay_actions.service import RazorpayActionService

    session = SessionLocal()
    try:
        client = RazorpaySandboxClient.from_settings()
        tick_due(session, RazorpayActionService(client))
        session.commit()
    except Exception as exc:  # noqa: BLE001 — worker must keep running
        session.rollback()
        logger.info("scheduler.tick.failed", extra={"error_type": type(exc).__name__})
    finally:
        session.close()


def _loop(interval_seconds: int) -> None:
    """Sleep/tick until ``stop_scheduler`` is called."""
    logger.info("scheduler.loop.start", extra={"interval_seconds": interval_seconds})
    while not _stop.wait(interval_seconds):
        _tick_once()
    logger.info("scheduler.loop.stop")


def start_scheduler(settings: Settings, *, database_ok: bool) -> None:
    """Start the daemon tick thread when enabled and Postgres is reachable."""
    global _thread
    if not settings.action_scheduler_enabled:
        logger.info("scheduler.disabled")
        return
    if not database_ok:
        logger.info("scheduler.skipped_no_database")
        return
    if _thread is not None and _thread.is_alive():
        return
    session = SessionLocal()
    try:
        from services.scheduler.sqlalchemy_store import ensure_scheduler_jobs_table

        ensure_scheduler_jobs_table(session)
        session.commit()
    except Exception as exc:  # noqa: BLE001 — table may already exist via Alembic
        session.rollback()
        logger.info("scheduler.table.ensure_failed", extra={"error_type": type(exc).__name__})
    finally:
        session.close()
    _stop.clear()
    _thread = threading.Thread(
        target=_loop,
        args=(max(5, int(settings.action_scheduler_interval_seconds)),),
        name="action-scheduler",
        daemon=True,
    )
    _thread.start()
    logger.info("scheduler.started")


def stop_scheduler() -> None:
    """Signal the tick thread to exit."""
    global _thread
    _stop.set()
    if _thread is not None:
        _thread.join(timeout=2)
        _thread = None
