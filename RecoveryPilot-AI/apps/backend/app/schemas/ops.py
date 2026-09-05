"""HTTP DTOs for health probes and the operations snapshot."""

from __future__ import annotations

from pydantic import BaseModel, Field


class ProbeComponent(BaseModel):
    """One dependency probe."""

    name: str
    status: str
    detail: str = ""
    mode: str | None = None


class SchedulerHealth(BaseModel):
    """Action-scheduler daemon + queue snapshot."""

    status: str
    enabled: bool = False
    thread_alive: bool = False
    scheduled: int = 0
    running: int = 0
    dead_letter: int = 0
    detail: str = ""


class WebhookThroughput(BaseModel):
    """Inbox counts used by the operations page."""

    received: int = 0
    processed: int = 0
    replayed: int = 0
    failed: int = 0


class HttpSnapshot(BaseModel):
    """In-process HTTP traffic for the operations page."""

    request_count: int = 0
    latency_p50_ms: float = 0
    latency_p95_ms: float = 0


class OpsStatusResponse(BaseModel):
    """Aggregated production-readiness snapshot for the Operations Status page."""

    status: str
    environment: str
    version: str
    api_version: str
    build_sha: str
    app_name: str
    timestamp: str
    api: ProbeComponent
    database: ProbeComponent
    scheduler: SchedulerHealth
    gemini: ProbeComponent
    razorpay: ProbeComponent
    webhooks: WebhookThroughput = Field(default_factory=WebhookThroughput)
    http: HttpSnapshot = Field(default_factory=HttpSnapshot)
    payment_links_sent: int = 0
    successful_retries: int = 0
    recovery_actions_executed: int = 0
