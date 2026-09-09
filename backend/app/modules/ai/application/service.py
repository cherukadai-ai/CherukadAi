"""Application service for provider-independent AI execution."""
from __future__ import annotations

import time
from collections.abc import Mapping

from app.modules.ai.domain.exceptions import AIError
from app.modules.ai.domain.models import (
    AIRequest,
    AIRequestType,
    AIResponse,
    AIResponseStatus,
)
from app.modules.ai.domain.ports import (
    IAIImageAnalysisProvider,
    IAIImageGenerationProvider,
    IAITextProvider,
)


class AIExecutionService:
    def __init__(self, providers: Mapping[str, object]) -> None:
        self._providers = providers

    async def execute(self, request: AIRequest) -> AIResponse:
        provider = self._providers.get(request.provider)
        if provider is None:
            return AIResponse(
                provider=request.provider,
                model=request.model or "unknown",
                status=AIResponseStatus.FAILED,
                error_code="provider_not_configured",
                error_message="Requested AI provider is not configured.",
            )
        started = time.perf_counter()
        try:
            if request.request_type == AIRequestType.TEXT:
                response = await self._as_text_provider(provider).generate_text(request)
            elif request.request_type == AIRequestType.IMAGE_ANALYSIS:
                response = await self._as_analysis_provider(provider).analyze_image(request)
            else:
                response = await self._as_generation_provider(provider).generate_image(request)
            return response
        except AIError as exc:
            status = (
                AIResponseStatus.TIMED_OUT
                if exc.code == "timeout"
                else AIResponseStatus.FAILED
            )
            return AIResponse(
                provider=request.provider,
                model=request.model or "unknown",
                status=status,
                duration_ms=round((time.perf_counter() - started) * 1000),
                error_code=exc.code,
                error_message=exc.message,
            )

    @staticmethod
    def _as_text_provider(provider: object) -> IAITextProvider:
        return provider  # type: ignore[return-value]

    @staticmethod
    def _as_analysis_provider(provider: object) -> IAIImageAnalysisProvider:
        return provider  # type: ignore[return-value]

    @staticmethod
    def _as_generation_provider(provider: object) -> IAIImageGenerationProvider:
        return provider  # type: ignore[return-value]
