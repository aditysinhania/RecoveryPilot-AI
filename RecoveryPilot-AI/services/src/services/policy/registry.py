"""Independent policy rule registry. Order matches documented precedence."""

from __future__ import annotations

from collections.abc import Callable, Sequence
from dataclasses import dataclass

from services.policy.constants import POLICY_PRECEDENCE
from services.policy.models import PolicyContext, PolicyRuleResult
from services.policy.rules import (
    rule_already_paid,
    rule_chargeback,
    rule_churn_protection,
    rule_consent,
    rule_dnd_contact,
    rule_high_value,
    rule_mandate,
    rule_outage,
    rule_promise_to_pay,
    rule_retry_cooldown,
)

PolicyFn = Callable[[PolicyContext], PolicyRuleResult]


@dataclass(frozen=True)
class RegisteredPolicy:
    """One named rule in the registry."""

    name: str
    fn: PolicyFn


_RULES: dict[str, PolicyFn] = {
    "already_paid": rule_already_paid,
    "chargeback": rule_chargeback,
    "consent": rule_consent,
    "mandate": rule_mandate,
    "promise_to_pay": rule_promise_to_pay,
    "retry_cooldown": rule_retry_cooldown,
    "outage": rule_outage,
    "dnd_contact": rule_dnd_contact,
    "churn_protection": rule_churn_protection,
    "high_value": rule_high_value,
}


def registered_policies() -> tuple[RegisteredPolicy, ...]:
    """Return policies in evaluation-precedence order.

    Returns:
        Frozen registry entries. Unknown names in ``POLICY_PRECEDENCE`` are skipped.
    """
    rows: list[RegisteredPolicy] = []
    for name in POLICY_PRECEDENCE:
        fn = _RULES.get(name)
        if fn is not None:
            rows.append(RegisteredPolicy(name=name, fn=fn))
    return tuple(rows)


def iter_policies() -> Sequence[RegisteredPolicy]:
    """Alias for ``registered_policies`` used by the evaluator."""
    return registered_policies()
