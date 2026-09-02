"""Canonical domain enums shared by ORM models and Pydantic schemas."""

from __future__ import annotations

from enum import StrEnum


class PaymentStatus(StrEnum):
    """Lifecycle of a Razorpay payment attempt."""

    PENDING = "PENDING"
    AUTHORIZED = "AUTHORIZED"
    CAPTURED = "CAPTURED"
    FAILED = "FAILED"
    REFUNDED = "REFUNDED"
    CANCELLED = "CANCELLED"
    AT_RISK = "AT_RISK"
    RECOVERED = "RECOVERED"


class FailureReason(StrEnum):
    """Root-cause classification used to pick a recovery playbook."""

    INSUFFICIENT_FUNDS = "INSUFFICIENT_FUNDS"
    BANK_TIMEOUT = "BANK_TIMEOUT"
    UPI_FAILURE = "UPI_FAILURE"
    CARD_EXPIRED = "CARD_EXPIRED"
    MANDATE_REVOKED = "MANDATE_REVOKED"
    CUSTOMER_CANCELLED = "CUSTOMER_CANCELLED"
    DISPUTE = "DISPUTE"
    ALREADY_PAID = "ALREADY_PAID"
    UNKNOWN = "UNKNOWN"


class RecoveryStatus(StrEnum):
    """State of one recovery journey for a failed or at-risk payment."""

    OPEN = "OPEN"
    DIAGNOSED = "DIAGNOSED"
    WAITING_RETRY = "WAITING_RETRY"
    WAITING_PROMISE = "WAITING_PROMISE"
    RECOVERED = "RECOVERED"
    STOPPED = "STOPPED"
    ESCALATED = "ESCALATED"
    CLOSED = "CLOSED"


class RecoveryActionType(StrEnum):
    """Bounded intervention the agent may schedule or execute."""

    RETRY_PAYMENT = "RETRY_PAYMENT"
    GENERATE_PAYMENT_LINK = "GENERATE_PAYMENT_LINK"
    SWITCH_PAYMENT_METHOD = "SWITCH_PAYMENT_METHOD"
    WAIT_FOR_PAYDAY = "WAIT_FOR_PAYDAY"
    PROMISE_TO_PAY = "PROMISE_TO_PAY"
    STOP_RECOVERY = "STOP_RECOVERY"
    ESCALATE_TO_AGENT = "ESCALATE_TO_AGENT"
    NO_ACTION = "NO_ACTION"


class PolicyDecision(StrEnum):
    """Gate applied before any money-moving or customer-facing action."""

    ALLOW = "ALLOW"
    BLOCK = "BLOCK"
    ESCALATE = "ESCALATE"


class CustomerSegment(StrEnum):
    """Merchant-facing cohort used for priority and tone."""

    NEW = "NEW"
    ACTIVE = "ACTIVE"
    LOYAL = "LOYAL"
    AT_RISK = "AT_RISK"
    HIGH_VALUE = "HIGH_VALUE"
    CHURN_RISK = "CHURN_RISK"


class MandateStatus(StrEnum):
    """UPI Autopay / e-mandate state on a subscription."""

    PENDING = "PENDING"
    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    REVOKED = "REVOKED"
    EXPIRED = "EXPIRED"


class SubscriptionStatus(StrEnum):
    """Billing relationship state independent of a single payment attempt."""

    ACTIVE = "ACTIVE"
    PAUSED = "PAUSED"
    PAST_DUE = "PAST_DUE"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"


class ConsentStatus(StrEnum):
    """Customer permission to be contacted for recovery."""

    PENDING = "PENDING"
    GRANTED = "GRANTED"
    WITHDRAWN = "WITHDRAWN"


class BillingFrequency(StrEnum):
    """How often a subscription is billed."""

    DAILY = "DAILY"
    WEEKLY = "WEEKLY"
    MONTHLY = "MONTHLY"
    QUARTERLY = "QUARTERLY"
    YEARLY = "YEARLY"


class PaymentMethod(StrEnum):
    """Instrument used or preferred for a charge."""

    UPI = "UPI"
    CARD = "CARD"
    NETBANKING = "NETBANKING"
    WALLET = "WALLET"
    EMI = "EMI"
    MANDATE = "MANDATE"


class ExecutionStatus(StrEnum):
    """Whether a scheduled recovery action has run."""

    SCHEDULED = "SCHEDULED"
    RUNNING = "RUNNING"
    SUCCEEDED = "SUCCEEDED"
    FAILED = "FAILED"
    SKIPPED = "SKIPPED"
    CANCELLED = "CANCELLED"


class PromiseStatus(StrEnum):
    """Lifecycle of a customer promise-to-pay."""

    OPEN = "OPEN"
    FULFILLED = "FULFILLED"
    BROKEN = "BROKEN"
    CANCELLED = "CANCELLED"


class ActorType(StrEnum):
    """Who produced an audit event."""

    SYSTEM = "SYSTEM"
    AI_AGENT = "AI_AGENT"
    POLICY_ENGINE = "POLICY_ENGINE"
    MERCHANT_USER = "MERCHANT_USER"
    CUSTOMER = "CUSTOMER"
    SIMULATOR = "SIMULATOR"


class AuditEventType(StrEnum):
    """Replayable event kinds stored on the compliance trail."""

    CASE_OPENED = "CASE_OPENED"
    DIAGNOSIS_COMPLETED = "DIAGNOSIS_COMPLETED"
    POLICY_EVALUATED = "POLICY_EVALUATED"
    ACTION_SCHEDULED = "ACTION_SCHEDULED"
    ACTION_EXECUTED = "ACTION_EXECUTED"
    ACTION_SKIPPED = "ACTION_SKIPPED"
    PROMISE_RECORDED = "PROMISE_RECORDED"
    PROMISE_FULFILLED = "PROMISE_FULFILLED"
    PROMISE_BROKEN = "PROMISE_BROKEN"
    PAYMENT_CAPTURED = "PAYMENT_CAPTURED"
    RECOVERY_STOPPED = "RECOVERY_STOPPED"
    ESCALATED = "ESCALATED"
    CASE_CLOSED = "CASE_CLOSED"
