from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="CALLBACK_SERVICE_", extra="ignore")

    database_url: str = "sqlite:///./callback-service.sqlite"
    admin_token: str = Field(default="development-admin-change-me-32chars", min_length=32)
    discord_token: str = Field(default="development-discord-change-me-32chars", min_length=32)
    rate_limit_per_minute: int = Field(default=240, ge=1, le=10000)
    max_body_bytes: int = Field(default=262144, ge=1024, le=1048576)
    connect_timeout_seconds: float = Field(default=5, ge=1, le=30)
    request_timeout_seconds: float = Field(default=15, ge=2, le=60)
    allow_private_targets: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
