"""Base types for the Application layer (use cases / services).

Use cases depend only on Domain ports (interfaces) — never on SQLAlchemy models,
FastAPI, or provider SDKs directly. Concrete implementations are injected.
"""
from __future__ import annotations

from typing import Generic, TypeVar

InputT = TypeVar("InputT")
OutputT = TypeVar("OutputT")


class UseCase(Generic[InputT, OutputT]):
    """Base class for a single application use case (command or query)."""

    async def execute(self, payload: InputT) -> OutputT:  # pragma: no cover - interface
        raise NotImplementedError
