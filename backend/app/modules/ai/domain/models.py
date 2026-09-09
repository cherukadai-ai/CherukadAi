"""Provider-independent AI request and response contracts."""
from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any


class AIProviderName(StrEnum):
    OPENAI = "openai"
    AZURE_OPENAI = "azure_openai"


class AIRequestType(StrEnum):
    TEXT = "text"
    IMAGE_ANALYSIS = "image_analysis"
    IMAGE_GENERATION = "image_generation"


class AIResponseStatus(StrEnum):
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    TIMED_OUT = "timed_out"


def utcnow() -> datetime:
    return datetime.now(UTC)


@dataclass(frozen=True)
class AIRequest:
    organisation_id: uuid.UUID
    user_id: uuid.UUID
    project_id: uuid.UUID | None = None
    feature_id: uuid.UUID | None = None
    workflow_id: uuid.UUID | None = None
    provider: str = AIProviderName.OPENAI
    prompt: str = ""
    image_url: str | None = None
    image_data: str | None = None
    model: str | None = None
    parameters: dict[str, Any] = field(default_factory=dict)
    request_type: AIRequestType = AIRequestType.TEXT


@dataclass(frozen=True)
class AIUsage:
    input_tokens: int | None = None
    output_tokens: int | None = None
    total_tokens: int | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass(frozen=True)
class AIResponse:
    provider: str
    model: str
    status: AIResponseStatus
    content: str | None = None
    data: list[dict[str, Any]] = field(default_factory=list)
    usage: AIUsage = field(default_factory=AIUsage)
    duration_ms: int = 0
    error_code: str | None = None
    error_message: str | None = None
    created_at: datetime = field(default_factory=utcnow)

    @property
    def succeeded(self) -> bool:
        return self.status == AIResponseStatus.SUCCEEDED
