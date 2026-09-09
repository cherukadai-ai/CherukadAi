"""Server-side AI provider configuration."""
from __future__ import annotations

from pydantic import BaseModel, ConfigDict, SecretStr


class AIProviderConfiguration(BaseModel):
    """Runtime configuration; secret values are write-only in representations."""

    model_config = ConfigDict(extra="forbid")

    openai_api_key: SecretStr | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: SecretStr | None = None
    openai_default_model: str = "gpt-4o-mini"
    azure_openai_default_model: str = "gpt-4o-mini"
    openai_image_model: str = "gpt-image-1"
    azure_openai_image_model: str = "gpt-image-1"
    timeout_seconds: float = 60.0
    max_retries: int = 2

    @classmethod
    def from_settings(cls, settings: object) -> AIProviderConfiguration:
        return cls(
            openai_api_key=getattr(settings, "openai_api_key", None),
            azure_openai_endpoint=getattr(settings, "azure_openai_endpoint", None),
            azure_openai_api_key=getattr(settings, "azure_openai_api_key", None),
            openai_default_model=getattr(settings, "openai_default_model", "gpt-4o-mini"),
            azure_openai_default_model=getattr(
                settings, "azure_openai_default_model", "gpt-4o-mini"
            ),
            openai_image_model=getattr(settings, "openai_image_model", "gpt-image-1"),
            azure_openai_image_model=getattr(
                settings, "azure_openai_image_model", "gpt-image-1"
            ),
            timeout_seconds=getattr(settings, "ai_timeout_seconds", 60.0),
            max_retries=getattr(settings, "ai_max_retries", 2),
        )
