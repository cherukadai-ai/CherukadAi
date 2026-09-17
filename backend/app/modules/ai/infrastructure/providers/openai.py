"""OpenAI-compatible provider adapters."""
from __future__ import annotations

import time
from typing import Any

from app.modules.ai.domain.configuration import AIProviderConfiguration
from app.modules.ai.domain.exceptions import AIConfigurationError, AIProviderError
from app.modules.ai.domain.models import (
    AIRequest,
    AIResponse,
    AIResponseStatus,
    AIUsage,
)
from app.modules.ai.domain.ports import (
    IAIImageAnalysisProvider,
    IAIImageGenerationProvider,
    IAITextProvider,
)
from app.modules.ai.infrastructure.providers.http import ProviderHTTPClient


class OpenAIProvider(IAITextProvider, IAIImageAnalysisProvider, IAIImageGenerationProvider):
    provider_name = "openai"

    def __init__(self, configuration: AIProviderConfiguration) -> None:
        if configuration.openai_api_key is None:
            raise AIConfigurationError("OpenAI API key is not configured.")
        self._api_key = configuration.openai_api_key.get_secret_value()
        self._configuration = configuration
        self._http = ProviderHTTPClient(
            timeout_seconds=configuration.timeout_seconds, max_retries=configuration.max_retries
        )

    async def generate_text(self, request: AIRequest) -> AIResponse:
        model = request.model or self._default_text_model()
        payload = {"model": model, "messages": [{"role": "user", "content": request.prompt}]}
        payload.update(request.parameters)
        started = time.perf_counter()
        result = await self._http.post(
            self._chat_url(model),
            headers=self._headers(),
            payload=payload,
        )
        return self._chat_response(result, model, started)

    async def analyze_image(self, request: AIRequest) -> AIResponse:
        model = request.model or self._default_text_model()
        image = request.image_url or (
            f"data:image/png;base64,{request.image_data}" if request.image_data else None
        )
        if image is None:
            raise AIProviderError("Image URL or image data is required.", code="invalid_request")
        payload = {
            "model": model,
            "messages": [{
                "role": "user",
                "content": [
                    {"type": "text", "text": request.prompt or "Describe this image."},
                    {"type": "image_url", "image_url": {"url": image}},
                ],
            }],
        }
        payload.update(request.parameters)
        started = time.perf_counter()
        result = await self._http.post(
            self._chat_url(model),
            headers=self._headers(),
            payload=payload,
        )
        return self._chat_response(result, model, started)

    async def generate_image(self, request: AIRequest) -> AIResponse:
        model = request.model or self._default_image_model()
        payload = {"model": model, "prompt": request.prompt}
        if request.image_data:
            payload["image"] = request.image_data
        payload.update(request.parameters)
        started = time.perf_counter()
        result = await self._http.post(
            self._image_url(model),
            headers=self._headers(),
            payload=payload,
        )
        return self._image_response(result, model, started)

    def _chat_response(self, result: dict[str, Any], model: str, started: float) -> AIResponse:
        choices = result.get("choices") or []
        if not choices:
            raise AIProviderError(
                "AI provider returned no choices.", code="invalid_provider_response"
            )
        message = choices[0].get("message", {})
        usage = result.get("usage", {})
        return AIResponse(
            provider=self.provider_name,
            model=result.get("model", model),
            status=AIResponseStatus.SUCCEEDED,
            content=message.get("content"),
            usage=AIUsage(
                input_tokens=usage.get("prompt_tokens"),
                output_tokens=usage.get("completion_tokens"),
                total_tokens=usage.get("total_tokens"),
                metadata=usage,
            ),
            duration_ms=round((time.perf_counter() - started) * 1000),
        )

    def _headers(self) -> dict[str, str]:
        return {"Authorization": f"Bearer {self._api_key}"}

    def _chat_url(self, model: str) -> str:
        return "https://api.openai.com/v1/chat/completions"

    def _image_url(self, model: str) -> str:
        return "https://api.openai.com/v1/images/generations"

    def _default_text_model(self) -> str:
        return self._configuration.openai_default_model

    def _default_image_model(self) -> str:
        return self._configuration.openai_image_model

    def _image_response(self, result: dict[str, Any], model: str, started: float) -> AIResponse:
        items = result.get("data") or []
        if not items:
            raise AIProviderError(
                "AI provider returned no image data.", code="invalid_provider_response"
            )
        return AIResponse(
            provider=self.provider_name,
            model=result.get("model", model),
            status=AIResponseStatus.SUCCEEDED,
            data=items,
            duration_ms=round((time.perf_counter() - started) * 1000),
        )
