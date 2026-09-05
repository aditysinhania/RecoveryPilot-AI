"""Gemini explanation agent tests. No live Gemini, Razorpay, or database."""

from __future__ import annotations

from datetime import datetime
from uuid import uuid4
from zoneinfo import ZoneInfo

from integrations.gemini.cache import ExplanationCache
from services.diagnosis.models import DiagnosisCategory, DiagnosisResult, PriorityBucket
from services.explanations.explanation_service import (
    explain_compliance,
    explain_customer_sms,
    explain_customer_whatsapp,
    explain_dashboard,
    explain_merchant,
    generate_batch_summaries,
)
from services.explanations.constants import MERCHANT_DISCLAIMER, PROMPT_VERSION
from services.explanations.fallback import fallback_merchant
from services.explanations.formatter import merchant_payload
from services.explanations.models import ExplanationContext, ExplanationSource
from services.planner.models import PlannerStrategy, RecoveryPlan
from services.policy.models import PolicyDecision, PolicyDecisionResult

IST = ZoneInfo("Asia/Kolkata")
AS_OF = datetime(2026, 9, 2, 12, 0, tzinfo=IST)


class FakeGemini:
    """Deterministic Gemini stand-in for tests."""

    def __init__(self, text: str, *, available: bool = True) -> None:
        self.text = text
        self.available = available
        self.calls = 0
        self.last_prompt = ""

    def is_available(self) -> bool:
        """Match GeminiClient.is_available."""
        return self.available

    def generate(self, prompt: str) -> str:
        """Return canned text and record the prompt."""
        self.calls += 1
        self.last_prompt = prompt
        return self.text


def _diagnosis(case_id=None) -> DiagnosisResult:
    """Minimal diagnosis for explanation tests."""
    from services.diagnosis.models import EvidenceItem

    return DiagnosisResult(
        diagnosis=DiagnosisCategory.INSUFFICIENT_FUNDS,
        confidence=0.8,
        priority_score=72.0,
        priority_bucket=PriorityBucket.HIGH,
        evidence=["UPI debit failed with insufficient funds."],
        evidence_items=[
            EvidenceItem(code="nsf", weight=0.8, message="UPI debit failed with insufficient funds.")
        ],
        triggered_rules=["insufficient_funds"],
        recommended_action_placeholder="SEND_PAYMENT_LINK",
        diagnosis_model="recovery_diagnosis_v1",
        diagnosis_version="1.0.0",
        generated_at=AS_OF,
        recovery_case_id=case_id or uuid4(),
        payment_id=uuid4(),
    )


def _policy(case_id=None) -> PolicyDecisionResult:
    """Minimal ALLOW policy for explanation tests."""
    return PolicyDecisionResult(
        policy_name="default_allow",
        decision=PolicyDecision.ALLOW,
        reason="Contact window open and retries remain.",
        evidence_codes=["contact_ok"],
        priority_score=72.0,
        decision_priority=20,
        evaluated_at=AS_OF,
        allowed_channels=["WhatsApp", "SMS", "Email"],
        blocked_channels=["Voice"],
        policy_version="recovery_policy_v1",
        triggered_policies=["contact_window"],
        failed_policies=[],
        recovery_case_id=case_id,
    )


def _plan(case_id=None) -> RecoveryPlan:
    """Minimal SEND_PAYMENT_LINK plan."""
    return RecoveryPlan(
        strategy=PlannerStrategy.SEND_PAYMENT_LINK,
        scheduled_at=AS_OF,
        reasoning="NSF with ALLOW maps to a payment link.",
        recommended_channels=["WhatsApp", "SMS"],
        fallback_strategy=PlannerStrategy.RETRY_PAYMENT,
        expected_outcome="Customer completes payment on the hosted link.",
        expected_recovery_probability=0.6,
        plan_version="recovery_planner_v1",
        planner_version="1.0.0",
        generated_at=AS_OF,
        recovery_case_id=case_id,
        estimated_recovery_value=99_900,
        timing_reason="Next business window.",
    )


def _context(*, case_id=None, first_name: str = "Adity") -> ExplanationContext:
    """Assemble engine snapshots for one explanation."""
    cid = case_id or uuid4()
    return ExplanationContext(
        diagnosis=_diagnosis(cid),
        policy=_policy(cid),
        plan=_plan(cid),
        customer_first_name=first_name,
        merchant_name="FitLife Gym",
        case_id=cid,
    )


def test_merchant_explanation() -> None:
    """Gemini JSON becomes a 2–4 sentence merchant explanation."""
    cache = ExplanationCache()
    client = FakeGemini(
        '{"explanation": "The payment failed because of insufficient funds. '
        "We will send a payment link next. The member can pay when ready. "
        'No extra charge was taken."}'
    )
    result = explain_merchant(_context(), client=client, cache=cache)
    assert result.source == ExplanationSource.GEMINI
    assert result.cached is False
    assert result.prompt_version == PROMPT_VERSION
    assert result.metadata is not None
    assert result.metadata.source == ExplanationSource.GEMINI
    assert result.metadata.cached is False
    assert result.metadata.prompt_version == PROMPT_VERSION
    assert result.generated_at == result.metadata.generated_at
    assert MERCHANT_DISCLAIMER in result.text
    assert "insufficient funds" in result.text.lower()
    assert client.calls == 1
    assert "expected_recovery_probability" not in client.last_prompt
    assert "strategy_confidence" not in client.last_prompt
    payload = merchant_payload(_context())
    assert "payment_id" not in payload
    assert "recovery_case_id" not in payload


def test_customer_sms() -> None:
    """SMS copy stays short, friendly, and includes a Hinglish placeholder."""
    cache = ExplanationCache()
    client = FakeGemini(
        '{"body": "Hi Adity, your FitLife Gym payment could not be completed. '
        'Please pay when you can. Thank you.",'
        '"hinglish_placeholder": "Namaste {first_name}, aapka {merchant} payment pending hai."}'
    )
    result = explain_customer_sms(_context(), client=client, cache=cache)
    assert result.channel == "SMS"
    assert result.source == ExplanationSource.GEMINI
    assert "Thank you" in result.body
    assert "{first_name}" in result.hinglish_placeholder
    assert "policy" not in result.body.lower()
    assert "confidence" not in result.body.lower()


def test_customer_whatsapp() -> None:
    """WhatsApp copy is a separate cache key from SMS."""
    cache = ExplanationCache()
    client = FakeGemini(
        '{"body": "Hi Adity, your FitLife Gym membership payment is pending. '
        'You can complete it using the payment link. Thank you.",'
        '"hinglish_placeholder": "Namaste {first_name}, kripya {merchant} ka ₹{amount_rupees} pay karein. Link: {payment_link}"}'
    )
    result = explain_customer_whatsapp(_context(), client=client, cache=cache)
    assert result.channel == "WhatsApp"
    assert result.source == ExplanationSource.GEMINI
    assert "payment" in result.body.lower()
    assert "{payment_link}" in result.hinglish_placeholder


def test_compliance_explanation() -> None:
    """Structured compliance fields stay on the engines even if Gemini writes copy."""
    cache = ExplanationCache()
    ctx = _context()
    client = FakeGemini(
        '{"narrative": "Diagnosis INSUFFICIENT_FUNDS. Evidence listed in input. '
        "Triggered policies include contact_window. Blocked policies include Voice. "
        'Planner strategy SEND_PAYMENT_LINK. Execution outcome not executed."}'
    )
    result = explain_compliance(ctx, client=client, cache=cache)
    assert result.source == ExplanationSource.GEMINI
    assert result.diagnosis == "INSUFFICIENT_FUNDS"
    assert result.planner_strategy == "SEND_PAYMENT_LINK"
    assert result.execution_outcome == "not executed"
    assert "UPI debit failed with insufficient funds." in result.evidence
    assert "contact_window" in result.triggered_policies
    assert any("Voice" in item for item in result.blocked_policies)


def test_dashboard_summary() -> None:
    """Dashboard summary is one short sentence; risk and next action are engine-owned."""
    cache = ExplanationCache()
    client = FakeGemini(
        '{"title": "Insufficient Funds", "summary": "Send a payment link to recover this invoice."}'
    )
    result = explain_dashboard(_context(), client=client, cache=cache)
    assert result.source == ExplanationSource.GEMINI
    assert len(result.summary) <= 160
    assert result.risk_level == "HIGH"
    assert "payment link" in result.next_action.lower()


def test_fallback_generation() -> None:
    """Unconfigured Gemini uses local templates."""
    cache = ExplanationCache()
    client = FakeGemini("ignored", available=False)
    ctx = _context()
    merchant = explain_merchant(ctx, client=client, cache=cache)
    assert merchant.source == ExplanationSource.FALLBACK
    assert merchant.prompt_version == PROMPT_VERSION
    assert merchant.metadata is not None
    assert merchant.metadata.source == ExplanationSource.FALLBACK
    assert MERCHANT_DISCLAIMER in merchant.text
    assert client.calls == 0
    assert "insufficient funds" in merchant.text.lower()
    local = fallback_merchant(ctx)
    assert local.source == ExplanationSource.FALLBACK
    sms = explain_customer_sms(ctx, client=client, cache=cache)
    assert sms.source == ExplanationSource.FALLBACK
    assert "₹" in sms.body
    assert "{first_name}" in sms.hinglish_placeholder


def test_cache_hit() -> None:
    """Second call with the same key does not hit Gemini."""
    cache = ExplanationCache()
    client = FakeGemini(
        '{"explanation": "The payment failed because of insufficient funds. '
        "We will send a payment link next. The member can pay when ready. "
        'No extra charge was taken."}'
    )
    ctx = _context()
    first = explain_merchant(ctx, client=client, cache=cache)
    second = explain_merchant(ctx, client=client, cache=cache)
    assert first.cached is False
    assert first.metadata is not None and first.metadata.cached is False
    assert second.cached is True
    assert second.metadata is not None and second.metadata.cached is True
    assert second.prompt_version == PROMPT_VERSION
    assert second.text == first.text
    assert client.calls == 1


def test_parser_failure() -> None:
    """Unparseable Gemini text falls back to the local template."""
    cache = ExplanationCache()
    client = FakeGemini("this is not json {{{")
    result = explain_merchant(_context(), client=client, cache=cache)
    assert result.source == ExplanationSource.FALLBACK
    assert client.calls == 1
    assert "insufficient funds" in result.text.lower()


def test_batch_summaries_use_cache() -> None:
    """Batch dashboard generation reuses cached cards."""
    cache = ExplanationCache()
    client = FakeGemini(
        '{"title": "Insufficient Funds", "summary": "Send a payment link to recover this invoice."}'
    )
    ctx = _context()
    first = generate_batch_summaries([ctx, ctx], client=client, cache=cache)
    assert len(first.results) == 2
    assert first.cache_hits == 1
    assert client.calls == 1
    second = generate_batch_summaries([ctx], client=client, cache=cache)
    assert second.cache_hits == 1
    assert client.calls == 1
