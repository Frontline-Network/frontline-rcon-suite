from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_prefix="DISCORD_SERVICE_", extra="ignore")

    database_url: str = "sqlite:///./discord-service.sqlite"
    secret: str = Field(default="development-only-change-me-32chars", min_length=32)
    discord_bot_token: str = ""
    discord_public_key: str = ""
    discord_install_url: str = ""
    allowed_crcon_hosts: str = ""
    openai_api_key: str = ""
    ai_model: str = "gpt-5.6-luna"
    moderation_model: str = "omni-moderation-latest"
    prompt_version: str = "moderation-v1"
    rate_limit_per_minute: int = Field(default=120, ge=1, le=10000)
    monthly_token_quota: int = Field(default=0, ge=0)
    dry_run: bool = False

    def crcon_host_allowlist(self) -> set[str]:
        return {
            value.strip().lower()
            for value in self.allowed_crcon_hosts.split(",")
            if value.strip()
        }


@lru_cache
def get_settings() -> Settings:
    return Settings()
