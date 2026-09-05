"""Domain and infrastructure exceptions with HTTP status mapping."""

from __future__ import annotations

_DB_UNAVAILABLE = (
    "Can't reach PostgreSQL. Start it with docker compose up postgres, then try again."
)
_AUTH_SCHEMA_MISSING = (
    "Auth tables are missing. Start PostgreSQL and restart the API so "
    "merchant_users and auth_sessions can be created."
)


class ApplicationException(Exception):
    """Base error for RecoveryPilot API handlers."""

    def __init__(
        self,
        message: str,
        *,
        code: str = "application_error",
        status_code: int = 500,
    ) -> None:
        super().__init__(message)
        self.message = message
        self.code = code
        self.status_code = status_code


_DB_UNAVAILABLE = (
    "Can't reach PostgreSQL. Start it with docker compose up postgres, then try again."
)
_AUTH_SCHEMA_MISSING = (
    "Auth tables are missing. Start PostgreSQL and restart the API so "
    "merchant_users and auth_sessions can be created."
)


class DatabaseUnavailableError(ApplicationException):
    """PostgreSQL is unreachable or the session cannot be opened."""

    def __init__(
        self,
        message: str = _DB_UNAVAILABLE,
        *,
        code: str = "database_unavailable",
    ) -> None:
        super().__init__(message, code=code, status_code=503)


def auth_schema_missing_error() -> DatabaseUnavailableError:
    """503 when merchant_users / auth_sessions have not been created."""
    return DatabaseUnavailableError(_AUTH_SCHEMA_MISSING, code="auth_schema_missing")


class MerchantNotFoundError(ApplicationException):
    """No merchant row exists for the given id."""

    def __init__(self, message: str = "Merchant not found") -> None:
        super().__init__(message, code="merchant_not_found", status_code=404)


class RecoveryNotFoundError(ApplicationException):
    """A recovery case id was not found."""

    def __init__(self, message: str = "Recovery case not found") -> None:
        super().__init__(message, code="recovery_case_not_found", status_code=404)


class InvalidFilterError(ApplicationException):
    """A queue filter value is not an allowed enum, band, or number."""

    def __init__(self, message: str = "Invalid filter") -> None:
        super().__init__(message, code="invalid_filter", status_code=400)


class InvalidDateRangeError(ApplicationException):
    """``date_from`` is after ``date_to``."""

    def __init__(self, message: str = "date_from must be on or before date_to") -> None:
        super().__init__(message, code="invalid_date_range", status_code=400)


class AuditEventNotFoundError(ApplicationException):
    """No audit trail exists for the requested recovery case."""

    def __init__(self, message: str = "Audit event not found") -> None:
        super().__init__(message, code="audit_event_not_found", status_code=404)


class CorrelationNotFoundError(ApplicationException):
    """No audit rows match the requested correlation id."""

    def __init__(self, message: str = "Correlation id not found") -> None:
        super().__init__(message, code="correlation_not_found", status_code=404)


class InvalidAuditFilterError(ApplicationException):
    """An audit explorer filter value cannot be interpreted."""

    def __init__(self, message: str = "Invalid audit filter") -> None:
        super().__init__(message, code="invalid_audit_filter", status_code=400)


class ActionNotFoundError(ApplicationException):
    """No recovery_actions row matches the requested execution id."""

    def __init__(self, message: str = "Action execution not found") -> None:
        super().__init__(message, code="action_execution_not_found", status_code=404)


class UnauthorizedError(ApplicationException):
    """Missing or invalid bearer token."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, code="unauthorized", status_code=401)


class InvalidCredentialsError(ApplicationException):
    """Login failed. Message is generic so emails are not enumerated."""

    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(message, code="invalid_credentials", status_code=401)


class ConflictError(ApplicationException):
    """Unique constraint, typically a taken email."""

    def __init__(self, message: str = "Resource already exists", *, code: str = "conflict") -> None:
        super().__init__(message, code=code, status_code=409)


class InvalidWebhookSignatureError(ApplicationException):
    """Razorpay HMAC signature did not match RAZORPAY_WEBHOOK_SECRET."""

    def __init__(self, message: str = "Invalid Razorpay webhook signature") -> None:
        super().__init__(message, code="invalid_webhook_signature", status_code=401)


class PolicyViolationError(ApplicationException):
    """A policy engine gate blocked an action. Placeholder until Phase 4B."""

    def __init__(self, message: str = "Policy blocked this action") -> None:
        super().__init__(message, code="policy_violation", status_code=403)


class ValidationException(ApplicationException):
    """Caller sent a payload the API cannot accept."""

    def __init__(self, message: str = "Request validation failed") -> None:
        super().__init__(message, code="validation_error", status_code=422)
