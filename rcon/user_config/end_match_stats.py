import logging
import os
from typing import ClassVar
from typing import Literal

from pydantic import ConfigDict, Field, model_validator

from rcon.user_config.utils import BaseUserConfig, set_user_config
from rcon.utils import get_server_number


def default_enabled():
    servers = {item.strip() for item in os.getenv("FRONTLINE_END_MATCH_STATS_SERVERS", "").split(",")}
    return str(get_server_number()) in servers


class EndMatchStatsUserConfig(BaseUserConfig):
    model_config = ConfigDict(extra="forbid")
    MISSING_CONFIG_LOG_LEVEL: ClassVar[int] = logging.DEBUG
    enabled: bool = Field(default_factory=default_enabled, strict=True)
    language: Literal["en", "de", "fr", "es", "ru", "pt", "pl", "zh"] = "en"
    title: str = Field(default="", max_length=60)
    kills: bool = Field(default=True, strict=True)
    defense: bool = Field(default=True, strict=True)
    support: bool = Field(default=True, strict=True)
    combat: bool = Field(default=False, strict=True)
    offense: bool = Field(default=False, strict=True)
    vehicles_destroyed: bool = Field(default=False, strict=True)
    teamplay: bool = Field(default=False, strict=True)
    offdef: bool = Field(default=False, strict=True)
    kd: bool = Field(default=False, strict=True)
    kpm: bool = Field(default=False, strict=True)
    include_players: bool = Field(default=True, strict=True)
    include_squads: bool = Field(default=False, strict=True)
    unit_types: list[Literal["commander", "infantry", "armor", "artillery", "recon"]] = Field(default_factory=lambda: ["commander", "infantry", "armor", "artillery", "recon"], min_length=1)
    top_count: int = Field(default=1, ge=1, le=3)
    message_gap_seconds: int = Field(default=15, ge=5, le=30)
    support_multiplier: float = Field(default=1.5, ge=0, le=5, allow_inf_nan=False)
    defense_multiplier: float = Field(default=1.5, ge=0, le=5, allow_inf_nan=False)

    @model_validator(mode="after")
    def check_categories(self):
        if self.enabled and not any((self.kills, self.defense, self.support, self.combat, self.offense, self.vehicles_destroyed, self.teamplay, self.offdef, self.kd, self.kpm)):
            raise ValueError("Select at least one statistic when enabled")
        if self.enabled and not (self.include_players or self.include_squads):
            raise ValueError("Select players or squads when enabled")
        if "\n" in self.title or "\r" in self.title:
            raise ValueError("Title must be a single line")
        return self

    @staticmethod
    def save_to_db(values, dry_run=False):
        config = EndMatchStatsUserConfig.model_validate(values)
        if not dry_run:
            set_user_config(EndMatchStatsUserConfig.KEY(), config.model_dump())
