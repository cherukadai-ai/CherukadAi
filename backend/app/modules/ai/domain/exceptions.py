"""Structured errors exposed by the provider-independent AI layer."""
from __future__ import annotations


class AIError(Exception):
    def __init__(self, code: str, message: str, *, retryable: bool = False) -> None:
        super().__init__(message)
        self.code = code
        self.message = message
        self.retryable = retryable


class AIConfigurationError(AIError):
    def __init__(self, message: str) -> None:
        super().__init__("configuration_error", message)


class AIProviderError(AIError):
    def __init__(
        self, message: str, *, code: str = "provider_error", retryable: bool = False
    ) -> None:
        super().__init__(code, message, retryable=retryable)


class AITimeoutError(AIProviderError):
    def __init__(self, message: str = "AI provider request timed out.") -> None:
        super().__init__(message, code="timeout", retryable=True)
