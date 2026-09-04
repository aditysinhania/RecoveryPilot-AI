"""Domain and infrastructure exceptions with HTTP status mapping."""

from __future__ import annotations


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


class DatabaseUnavailableError(ApplicationException):
    """PostgreSQL is unreachable or the session cannot be opened."""

    def __init__(self, message: str = "PostgreSQL is unavailable") -> None:
        super().__init__(message, code="database_unavailable", status_code=503)


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


class PolicyViolationError(ApplicationException):
    """A policy engine gate blocked an action. Placeholder until Phase 4B."""

    def __init__(self, message: str = "Policy blocked this action") -> None:
        super().__init__(message, code="policy_violation", status_code=403)


class ValidationException(ApplicationException):
    """Caller sent a payload the API cannot accept."""

    def __init__(self, message: str = "Request validation failed") -> None:
        super().__init__(message, code="validation_error", status_code=422)
