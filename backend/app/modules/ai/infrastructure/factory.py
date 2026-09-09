"""Composition root for configured AI providers."""
from __future__ import annotations

from app.core.config import Settings
from app.modules.ai.domain.configuration import AIProviderConfiguration
from app.modules.ai.infrastructure.providers.azure_openai import AzureOpenAIProvider
from app.modules.ai.infrastructure.providers.openai import OpenAIProvider


def build_ai_providers(settings: Settings) -> dict[str, object]:
    configuration = AIProviderConfiguration.from_settings(settings)
    providers: dict[str, object] = {}
    if configuration.openai_api_key is not None:
        providers["openai"] = OpenAIProvider(configuration)
    if configuration.azure_openai_api_key is not None and configuration.azure_openai_endpoint:
        providers["azure_openai"] = AzureOpenAIProvider(configuration)
    return providers
