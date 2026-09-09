"""Centralized application configuration.

All configuration is sourced from environment variables (12-factor). Never hardcode
secrets here — this module only defines shape, defaults, and validation.
"""
from functools import lru_cache
from typing import Annotated, Literal

from pydantic import Field, SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    # --- General ---
    app_name: str = "CherukadAI Platform"
    environment: Literal["local", "dev", "staging", "production", "test"] = "local"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

    # --- Security ---
    secret_key: str = Field(default="CHANGE_ME_INSECURE_DEFAULT_FOR_LOCAL_DEV_ONLY")
    session_cookie_name: str = "cherukadai_session"
    session_ttl_seconds: int = 60 * 60 * 12  # 12 hours
    allowed_origins: Annotated[list[str], NoDecode] = ["http://localhost:3000"]

    # --- Database ---
    database_url: str = Field(
        default="postgresql+asyncpg://cherukadai:cherukadai@localhost:5432/cherukadai"
    )
    database_pool_size: int = 10
    database_max_overflow: int = 5
    database_echo: bool = False

    # --- Redis ---
    redis_url: str = Field(default="redis://localhost:6379/0")

    # --- Celery ---
    celery_broker_url: str = Field(default="redis://localhost:6379/1")
    celery_result_backend: str = Field(default="redis://localhost:6379/2")

    # --- Azure Blob Storage (abstraction target; no real secrets) ---
    azure_storage_connection_string: str | None = None
    azure_storage_container: str = "cherukadai-files"

    # --- AI Providers (references only; real keys come from secret store) ---
    openai_api_key: SecretStr | None = None
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: SecretStr | None = None
    openai_default_model: str = "gpt-4o-mini"
    azure_openai_default_model: str = "gpt-4o-mini"
    openai_image_model: str = "gpt-image-1"
    azure_openai_image_model: str = "gpt-image-1"
    ai_timeout_seconds: float = Field(default=60.0, gt=0, le=300)
    ai_max_retries: int = Field(default=2, ge=0, le=5)

    # --- Logging ---
    log_level: str = "INFO"
    log_json: bool = True

    # --- First-time setup ---
    super_admin_setup_token: str | None = None

    # --- Authentication / account protection ---
    password_min_length: int = 12
    max_failed_login_attempts: int = 5
    account_lockout_seconds: int = 15 * 60  # 15 minutes
    login_rate_limit_attempts: int = 10
    login_rate_limit_window_seconds: int = 5 * 60  # 5 minutes

    @model_validator(mode="before")
    @classmethod
    def _strip_string_values(cls, data: object) -> object:
        if not isinstance(data, dict):
            return data
        cleaned: dict[str, object] = {}
        for key, value in data.items():
            if isinstance(value, str):
                cleaned[key] = value.strip()
            else:
                cleaned[key] = value
        return cleaned

    @field_validator("allowed_origins", mode="before")
    @classmethod
    def _split_origins(cls, value: str | list[str]) -> list[str]:
        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @field_validator("super_admin_setup_token", mode="before")
    @classmethod
    def _blank_setup_token_is_unset(cls, value: str | None) -> str | None:
        if isinstance(value, str) and not value.strip():
            return None
        return value

    @property
    def is_production(self) -> bool:
        return self.environment == "production"


@lru_cache
def get_settings() -> Settings:
    return Settings()
