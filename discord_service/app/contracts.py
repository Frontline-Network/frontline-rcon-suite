"""Wire contracts mirrored from CRCON; schema_version guards compatibility."""

from __future__ import annotations

from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, model_validator


class ModerationSource(StrEnum):
    REPORT = "report"
    CHAT = "ai_chat"
    PLAYER_NAME = "ai_player_name"


class ModerationSeverity(StrEnum):
    NONE = "none"
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class SuggestedAction(StrEnum):
    NONE = "none"
    MESSAGE = "message"
    PUNISH = "punish"
    KICK = "kick"
    TEMP_BAN = "temp_ban"
    PERMA_BAN = "perma_ban"
    BLACKLIST = "blacklist"
    REMOVE_FROM_SQUAD = "remove_from_squad"
    DISBAND_SQUAD = "disband_squad"
    MANUAL_REVIEW = "manual_review"


class ModerationPolicy(BaseModel):
    model_config = ConfigDict(extra="forbid")
    profile_id: str = Field(default="frontline-default", min_length=1, max_length=64)
    version: str = Field(default="1", min_length=1, max_length=32)
    language: Literal["de", "en"] = "de"
    enabled_sources: set[ModerationSource] = Field(
        default_factory=lambda: set(ModerationSource)
    )
    alert_threshold: float = Field(default=0.90, ge=0, le=1)
    shadow_threshold: float = Field(default=0.70, ge=0, le=1)
    hard_rule_ids: set[str] = Field(default_factory=set)
    custom_terms: list[str] = Field(default_factory=list)
    exceptions: list[str] = Field(default_factory=list)
    custom_regexes: list[str] = Field(default_factory=list)


class ModerationAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")
    source: ModerationSource
    affected_player_ids: list[str] = Field(default_factory=list, max_length=20)
    categories: list[str] = Field(default_factory=list, max_length=20)
    rule_ids: list[str] = Field(default_factory=list, max_length=20)
    severity: ModerationSeverity
    risk_score: float = Field(ge=0, le=1)
    rationale: str = Field(min_length=1, max_length=1000)
    relevant_excerpts: list[str] = Field(default_factory=list, max_length=5)
    suggested_action: SuggestedAction
    suggested_duration_hours: int | None = Field(default=None, ge=1, le=8760)
    duration_rationale: str | None = Field(default=None, max_length=500)
    suggested_player_response: str | None = Field(default=None, max_length=500)
    model_version: str = Field(min_length=1, max_length=100)
    prompt_version: str = Field(min_length=1, max_length=64)
    policy_profile_id: str = Field(min_length=1, max_length=64)
    policy_version: str = Field(min_length=1, max_length=32)
    hard_hit: bool = False

    @model_validator(mode="after")
    def duration_matches_action(self):
        if (
            self.suggested_action == SuggestedAction.TEMP_BAN
            and self.suggested_duration_hours is None
        ):
            raise ValueError("Temp bans require a duration")
        if (
            self.suggested_action != SuggestedAction.TEMP_BAN
            and self.suggested_duration_hours is not None
        ):
            raise ValueError("Only temp bans may include a duration")
        return self


class IncidentEventEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1"] = "1"
    installation_id: str = Field(min_length=1, max_length=64)
    event_id: int = Field(ge=1)
    event_type: str = Field(pattern=r"^[a-z_]+$", max_length=32)
    incident_id: str = Field(min_length=1, max_length=36)
    incident_revision: int = Field(ge=1)
    occurred_at: datetime
    server_number: int = Field(ge=1)
    server_name: str = Field(min_length=1, max_length=255)
    game: Literal["hll", "hll_vietnam"]
    incident: dict
    analysis: ModerationAnalysis | None = None


class ModerationAnalysisJobEnvelope(BaseModel):
    model_config = ConfigDict(extra="forbid")
    schema_version: Literal["1"] = "1"
    installation_id: str = Field(min_length=1, max_length=64)
    job_id: str = Field(min_length=1, max_length=36)
    source: Literal[ModerationSource.CHAT, ModerationSource.PLAYER_NAME]
    server_number: int = Field(ge=1)
    player_id: str | None = Field(default=None, max_length=100)
    player_name: str | None = Field(default=None, max_length=255)
    candidate_text: str = Field(min_length=1, max_length=4000)
    matched_rule_ids: list[str] = Field(default_factory=list, max_length=100)
    policy: ModerationPolicy
    shadow_only: bool = True
    created_at: datetime
