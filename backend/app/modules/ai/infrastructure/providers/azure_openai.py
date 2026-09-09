"""Azure OpenAI adapter using the same provider-independent contracts."""
from __future__ import annotations

from urllib.parse import quote

from app.modules.ai.domain.configuration import AIProviderConfiguration
from app.modules.ai.domain.exceptions import AIConfigurationError
from app.modules.ai.infrastructure.providers.openai import OpenAIProvider


class AzureOpenAIProvider(OpenAIProvider):
    provider_name = "azure_openai"

    def __init__(self, configuration: AIProviderConfiguration) -> None:
        if configuration.azure_openai_api_key is None:
            raise AIConfigurationError("Azure OpenAI API key is not configured.")
        if not configuration.azure_openai_endpoint:
            raise AIConfigurationError("Azure OpenAI endpoint is not configured.")
        self._api_key = configuration.azure_openai_api_key.get_secret_value()
        self._endpoint = configuration.azure_openai_endpoint.rstrip("/")
        self._configuration = configuration
        from app.modules.ai.infrastructure.providers.http import ProviderHTTPClient

        self._http = ProviderHTTPClient(
            timeout_seconds=configuration.timeout_seconds, max_retries=configuration.max_retries
        )

    def _headers(self) -> dict[str, str]:
        return {"api-key": self._api_key}

    def _chat_url(self, model: str) -> str:
        deployment = quote(model or self._configuration.azure_openai_default_model, safe="")
        return (
            f"{self._endpoint}/openai/deployments/{deployment}/chat/completions"
            "?api-version=2024-10-21"
        )

    def _image_url(self, model: str) -> str:
        deployment = quote(model or self._configuration.azure_openai_image_model, safe="")
        return (
            f"{self._endpoint}/openai/deployments/{deployment}/images/generations"
            "?api-version=2024-10-21"
        )

    def _default_text_model(self) -> str:
        return self._configuration.azure_openai_default_model

    def _default_image_model(self) -> str:
        return self._configuration.azure_openai_image_model
