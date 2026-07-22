"""Typed application configuration."""

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Environment-backed settings used by the application."""

    app_name: str = "FastAPI AI Cloud Security Incident Response System"
    app_description: str = "API for ingesting and managing cloud security alerts."
    app_version: str = "0.1.0"
    environment: str = "development"
    debug: bool = False
    api_v1_prefix: str = "/api/v1"

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
