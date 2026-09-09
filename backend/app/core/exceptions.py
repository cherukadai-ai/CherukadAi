"""Application-wide exception hierarchy.

Domain/Application layers raise these instead of HTTPException so business logic
stays framework-agnostic. The API layer maps them to responses centrally.
"""
from __future__ import annotations


class AppError(Exception):
    """Base class for all handled application errors."""

    status_code: int = 500
    error_code: str = "internal_error"

    def __init__(self, message: str | None = None, **details: object) -> None:
        self.message = message or self.__class__.__doc__ or self.error_code
        self.details = details
        super().__init__(self.message)


class NotFoundError(AppError):
    """The requested resource was not found."""

    status_code = 404
    error_code = "not_found"


class ValidationAppError(AppError):
    """The request failed domain validation."""

    status_code = 422
    error_code = "validation_error"


class UnauthorizedError(AppError):
    """Authentication is required or has failed."""

    status_code = 401
    error_code = "unauthorized"


class ForbiddenError(AppError):
    """The caller is authenticated but not permitted to perform this action."""

    status_code = 403
    error_code = "forbidden"


class ConflictError(AppError):
    """The request conflicts with the current state of the resource."""

    status_code = 409
    error_code = "conflict"


class RateLimitExceededError(AppError):
    """The caller has exceeded the allowed request rate for this action."""

    status_code = 429
    error_code = "rate_limit_exceeded"


class FeatureDisabledError(ForbiddenError):
    """The requested AI feature is not enabled for this organisation."""

    error_code = "feature_disabled"


class TenantMismatchError(ForbiddenError):
    """The requested resource does not belong to the caller's organisation."""

    error_code = "tenant_mismatch"
