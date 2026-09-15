"""Server-local opt-in. No automatic activation or kick on upgrade."""

import logging
from typing import ClassVar, Literal
from pydantic import ConfigDict, Field
from rcon.user_config.utils import BaseUserConfig


class LeadershipVoteUserConfig(BaseUserConfig):
    MISSING_CONFIG_LOG_LEVEL: ClassVar[int] = logging.DEBUG
    model_config = ConfigDict(extra="forbid", strict=True)
    enabled: bool = False
    mode: Literal["dry_run", "active"] = "dry_run"
    confirmation_seconds: int = Field(default=60, ge=30, le=180)
    warning_seconds: int = Field(default=60, ge=30, le=180)
    duration_seconds: int = Field(default=120, ge=60, le=300)
    minimum_participants: int = Field(default=3, ge=3, le=50)
    leadership_seconds: int = Field(default=300, ge=300, le=1800)
    team_gap_seconds: int = Field(default=600, ge=600, le=3600)
    target_cooldown_seconds: int = Field(default=1800, ge=1800, le=86400)

    def required(self, count):
        return count // 2 + 1

    @staticmethod
    def save_to_db(values, dry_run=False):
        config = LeadershipVoteUserConfig.model_validate(values)
        if not dry_run:
            from rcon.leadership_vote.storage import configure
            from rcon.utils import get_server_number

            configure(int(get_server_number()), config, actor="system:config")
