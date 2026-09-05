"""Typed explanation outputs. Gemini never chooses recovery actions."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Self
from uuid import UUID

from pydantic import BaseModel, Field, model_validator

from services.diagnosis.models import DiagnosisResult
from services.executor.models import ExecutionResult
from services.explanations.constants import PROMPT_VERSION
from services.planner.models import RecoveryPlan
from services.policy.models import PolicyDecisionResult


class ExplanationType(StrEnum):
    """Cache and prompt selector. One mode per call."""

    MERCHANT = "MERCHANT"
    CUSTOMER_WHATSAPP = "CUSTOMER_WHATSAPP"
    CUSTOMER_SMS = "CUSTOMER_SMS"
    CUSTOMER_EMAIL = "CUSTOMER_EMAIL"
    COMPLIANCE = "COMPLIANCE"
    DASHBOARD = "DASHBOARD"


class ExplanationSource(StrEnum):
    """Whether copy came from Gemini or the local template."""

    GEMINI = "gemini"
    FALLBACK = "fallback"


class ExplanationMetadata(BaseModel):
    """Provenance for one explanation. Same shape on every mode."""

    source: ExplanationSource
    cached: bool = False
    generated_at: datetime
    prompt_version: str = PROMPT_VERSION


class _WithMetadata(BaseModel):
    """Mixin that keeps ``metadata`` aligned with top-level provenance fields."""

    source: ExplanationSource
    cached: bool = False
    generated_at: datetime
    prompt_version: str = PROMPT_VERSION
    metadata: ExplanationMetadata | None = None

    @model_validator(mode="after")
    def _sync_metadata(self) -> Self:
        """Fill ``metadata`` from source / cached / generated_at / prompt_version."""
        version = self.prompt_version or PROMPT_VERSION
        self.prompt_version = version
        self.metadata = ExplanationMetadata(
            source=self.source,
            cached=self.cached,
            generated_at=self.generated_at,
            prompt_version=version,
        )
        return self


class ExplanationContext(BaseModel):
    """Engine outputs plus optional display fields. No ORM."""

    diagnosis: DiagnosisResult
    policy: PolicyDecisionResult
    plan: RecoveryPlan
    execution: ExecutionResult | None = None
    customer_first_name: str = ""
    merchant_name: str = "FitLife Gym"
    case_id: UUID | None = None


class MerchantExplanation(_WithMetadata):
    """2–4 sentence merchant-facing explanation plus a confidence disclaimer."""

    text: str
    explanation_type: ExplanationType = ExplanationType.MERCHANT
    case_id: UUID | None = None


class CustomerMessage(_WithMetadata):
    """Outbound payment copy for one channel. Not sent by this package."""

    channel: str
    language: str = "en"
    body: str
    hinglish_placeholder: str = ""
    explanation_type: ExplanationType
    case_id: UUID | None = None


class ComplianceExplanation(_WithMetadata):
    """Audit-ready reasoning. Structured fields always come from the engines."""

    diagnosis: str
    evidence: list[str] = Field(default_factory=list)
    triggered_policies: list[str] = Field(default_factory=list)
    blocked_policies: list[str] = Field(default_factory=list)
    planner_strategy: str
    execution_outcome: str
    narrative: str
    explanation_type: ExplanationType = ExplanationType.COMPLIANCE
    case_id: UUID | None = None


class DashboardSummary(_WithMetadata):
    """One dashboard card. ``summary`` is a single sentence, max 160 chars."""

    title: str
    summary: str
    risk_level: str
    next_action: str
    explanation_type: ExplanationType = ExplanationType.DASHBOARD
    case_id: UUID | None = None


class BatchDashboardResult(BaseModel):
    """Dashboard cards for many cases."""

    results: list[DashboardSummary]
    cache_hits: int = 0
    fallbacks: int = 0
