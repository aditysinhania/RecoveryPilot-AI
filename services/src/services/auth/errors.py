"""Domain errors for merchant authentication. Mapped to HTTP in the adapter."""

from __future__ import annotations


class AuthError(Exception):
    """Base auth domain error."""

    def __init__(self, message: str, *, code: str = "auth_error") -> None:
        super().__init__(message)
        self.message = message
        self.code = code


class EmailTakenError(AuthError):
    """Signup email already exists."""

    def __init__(self, message: str = "An account with this email already exists") -> None:
        super().__init__(message, code="email_taken")


class InvalidCredentialsError(AuthError):
    """Login email or password did not match."""

    def __init__(self, message: str = "Invalid email or password") -> None:
        super().__init__(message, code="invalid_credentials")


class UnauthorizedError(AuthError):
    """Missing, expired, or revoked token."""

    def __init__(self, message: str = "Authentication required") -> None:
        super().__init__(message, code="unauthorized")


class WeakPasswordError(AuthError):
    """Password does not meet policy."""

    def __init__(self, message: str = "Password does not meet policy") -> None:
        super().__init__(message, code="weak_password")


class OnboardingError(AuthError):
    """Onboarding step is out of order or invalid."""

    def __init__(self, message: str = "Complete the previous onboarding step first") -> None:
        super().__init__(message, code="onboarding_invalid")
