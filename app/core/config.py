"""Typed application configuration."""

from functools import lru_cache
from typing import Self

from pydantic import SecretStr, field_validator, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings used by the application."""

    app_name: str = "FastAPI AI Cloud Security Incident Response System"
    app_description: str = "API for ingesting and managing cloud security alerts."
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"
    api_key: SecretStr = SecretStr("local-development-api-key")
    jwt_secret: SecretStr = SecretStr(
        "local-development-jwt-secret-change-me",
    )
    access_token_minutes: int = 60
    rate_limit_requests: int = 120
    rate_limit_window_seconds: int = 60
    openai_api_key: SecretStr | None = None
    openai_model: str = "gpt-4.1-mini"
    openai_base_url: str = "https://api.openai.com/v1"
    ai_request_timeout_seconds: float = 20.0

    model_config = SettingsConfigDict(
        env_file=".env",
        env_prefix="CIR_",
        extra="ignore",
    )

    database_url: str = (
        "postgresql+asyncpg://"
        "incident_app:local-development-only@"
        "localhost:5434/incident_response"
    )

    @field_validator("openai_api_key", mode="before")
    @classmethod
    def empty_ai_key_is_unconfigured(cls, value: object) -> object:
        """Treat an empty environment variable as disabled AI triage."""
        return None if value == "" else value

    @model_validator(mode="after")
    def reject_default_key_outside_development(self) -> Self:
        """Prevent accidental deployment with the documented local key."""
        if self.environment.lower() not in {"development", "test"} and (
            self.api_key.get_secret_value() == "local-development-api-key"
            or self.jwt_secret.get_secret_value()
            == "local-development-jwt-secret-change-me"
        ):
            raise ValueError(
                "CIR_API_KEY and CIR_JWT_SECRET must be changed outside development",
            )
        return self


@lru_cache
def get_settings() -> Settings:
    """Return one cached settings object for dependency injection."""
    return Settings()
