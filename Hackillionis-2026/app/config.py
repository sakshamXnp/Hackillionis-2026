"""Application configuration using Pydantic Settings."""

from functools import lru_cache
from typing import Literal

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",  # pydantic-settings dotenv support
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "Payment Rules Engine API"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Database
    database_url: str = "sqlite+aiosqlite:///./payment_rules.db"
    echo_sql: bool = False

    # API
    api_v1_prefix: str = "/api/v1"

    # Capital One Nessie API (from .env: CAPITAL_ONE_API_KEY, CAPITAL_ONE_BASE_URL)
    capital_one_api_key: str
    capital_one_base_url: str = "http://api.nessieisreal.com"


@lru_cache
def get_settings() -> Settings:
    """Return cached settings instance."""
    return Settings()
