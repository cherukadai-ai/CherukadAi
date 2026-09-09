"""Provider interfaces. Application code depends only on these protocols."""
from __future__ import annotations

from typing import Protocol

from app.modules.ai.domain.models import AIRequest, AIResponse


class IAIProvider(Protocol):
    @property
    def provider_name(self) -> str: ...


class IAITextProvider(IAIProvider, Protocol):
    async def generate_text(self, request: AIRequest) -> AIResponse: ...


class IAIImageAnalysisProvider(IAIProvider, Protocol):
    async def analyze_image(self, request: AIRequest) -> AIResponse: ...


class IAIImageGenerationProvider(IAIProvider, Protocol):
    async def generate_image(self, request: AIRequest) -> AIResponse: ...
