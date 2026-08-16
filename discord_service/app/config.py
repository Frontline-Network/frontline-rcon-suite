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
    player_name_model: str = "gpt-5.4-nano"
    moderation_model: str = "omni-moderation-latest"
    prompt_version: str = "moderation-v1"
    codex_enabled: bool = True
    codex_binary: str = "codex"
    codex_auth_root: str = "/var/lib/frontline-codex"
    codex_request_timeout_seconds: int = Field(default=90, ge=10, le=300)
    rate_limit_per_minute: int = Field(default=120, ge=1, le=10000)
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
