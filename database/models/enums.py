"""PostgreSQL native enums wired from shared StrEnum values."""

from __future__ import annotations

from enum import StrEnum

from sqlalchemy import Enum as SAEnum

from shared.enums import (
    ActorType,
    AuditEventType,
    BillingFrequency,
    ConsentStatus,
    CustomerSegment,
    ExecutionStatus,
    FailureReason,
    MandateStatus,
    PaymentMethod,
    PaymentStatus,
    PolicyDecision,
    PromiseStatus,
    RecoveryActionType,
    RecoveryStatus,
    SubscriptionStatus,
)

__all__ = [
    "ActorType",
    "AuditEventType",
    "BillingFrequency",
    "ConsentStatus",
    "CustomerSegment",
    "ExecutionStatus",
    "FailureReason",
    "MandateStatus",
    "PaymentMethod",
    "PaymentStatus",
    "PolicyDecision",
    "PromiseStatus",
    "RecoveryActionType",
    "RecoveryStatus",
    "SubscriptionStatus",
    "actor_type_enum",
    "audit_event_type_enum",
    "billing_frequency_enum",
    "consent_status_enum",
    "customer_segment_enum",
    "execution_status_enum",
    "failure_reason_enum",
    "mandate_status_enum",
    "payment_method_enum",
    "payment_status_enum",
    "pg_enum",
    "policy_decision_enum",
    "promise_status_enum",
    "recovery_action_type_enum",
    "recovery_status_enum",
    "subscription_status_enum",
]


def pg_enum(enum_cls: type[StrEnum], name: str) -> SAEnum:
    """Build a native PostgreSQL ENUM column type from a StrEnum class."""
    return SAEnum(
        enum_cls,
        name=name,
        native_enum=True,
        values_callable=lambda members: [item.value for item in members],
        validate_strings=True,
    )


payment_status_enum = pg_enum(PaymentStatus, "payment_status")
failure_reason_enum = pg_enum(FailureReason, "failure_reason")
recovery_status_enum = pg_enum(RecoveryStatus, "recovery_status")
recovery_action_type_enum = pg_enum(RecoveryActionType, "recovery_action_type")
policy_decision_enum = pg_enum(PolicyDecision, "policy_decision")
customer_segment_enum = pg_enum(CustomerSegment, "customer_segment")
mandate_status_enum = pg_enum(MandateStatus, "mandate_status")
subscription_status_enum = pg_enum(SubscriptionStatus, "subscription_status")
consent_status_enum = pg_enum(ConsentStatus, "consent_status")
billing_frequency_enum = pg_enum(BillingFrequency, "billing_frequency")
payment_method_enum = pg_enum(PaymentMethod, "payment_method")
execution_status_enum = pg_enum(ExecutionStatus, "execution_status")
promise_status_enum = pg_enum(PromiseStatus, "promise_status")
actor_type_enum = pg_enum(ActorType, "actor_type")
audit_event_type_enum = pg_enum(AuditEventType, "audit_event_type")
