"""Identity-specific errors mapped to HTTP responses by the API layer."""
from __future__ import annotations

from app.core.exceptions import ForbiddenError, UnauthorizedError


class SetupAlreadyCompletedError(ForbiddenError):
    """Initial setup has already been completed; the endpoint is permanently closed."""

    error_code = "setup_already_completed"


class InvalidSetupTokenError(ForbiddenError):
    """The provided first-time setup token is missing or invalid."""

    error_code = "invalid_setup_token"


class InvalidCredentialsError(UnauthorizedError):
    """Email/password combination is not valid.

    Deliberately generic so the response never reveals whether the email exists.
    """

    error_code = "invalid_credentials"


class AccountDisabledError(ForbiddenError):
    """The account has been disabled by an administrator."""

    error_code = "account_disabled"


class AccountLockedError(ForbiddenError):
    """The account is temporarily locked after too many failed login attempts."""

    error_code = "account_locked"
