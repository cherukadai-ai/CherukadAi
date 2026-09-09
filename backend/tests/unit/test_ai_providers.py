import uuid

import pytest

from app.modules.ai.application.service import AIExecutionService
from app.modules.ai.domain.configuration import AIProviderConfiguration
from app.modules.ai.domain.exceptions import AITimeoutError
from app.modules.ai.domain.models import AIRequest, AIResponse, AIResponseStatus, AIUsage


class FakeTextProvider:
    provider_name = "fake"

    async def generate_text(self, request: AIRequest) -> AIResponse:
        return AIResponse(
            provider="fake",
            model="fake-model",
            status=AIResponseStatus.SUCCEEDED,
            content=request.prompt.upper(),
            usage=AIUsage(total_tokens=3),
        )


class TimingOutProvider:
    async def generate_text(self, request: AIRequest) -> AIResponse:
        raise AITimeoutError()


def make_request(provider: str = "fake") -> AIRequest:
    return AIRequest(
        organisation_id=uuid.uuid4(), user_id=uuid.uuid4(), provider=provider, prompt="hello"
    )


@pytest.mark.asyncio
async def test_execution_service_normalizes_provider_response():
    response = await AIExecutionService({"fake": FakeTextProvider()}).execute(make_request())

    assert response.succeeded
    assert response.content == "HELLO"
    assert response.usage.total_tokens == 3


@pytest.mark.asyncio
async def test_execution_service_normalizes_timeout():
    response = await AIExecutionService({"fake": TimingOutProvider()}).execute(make_request())

    assert response.status == AIResponseStatus.TIMED_OUT
    assert response.error_code == "timeout"


def test_provider_configuration_masks_secrets():
    configuration = AIProviderConfiguration(openai_api_key="secret-value")

    assert "secret-value" not in repr(configuration)
    assert configuration.openai_api_key.get_secret_value() == "secret-value"
