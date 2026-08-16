"""Shared moderation contracts and the privacy-preserving local prefilter.

The game chat is untrusted data.  These types deliberately contain no tools,
credentials, URLs, or executable commands; a model can only return a validated
recommendation that CRCON may later present to a human moderator.
"""

from __future__ import annotations

import hashlib
import re
import unicodedata
from datetime import datetime
from enum import StrEnum
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator


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


class DiscordActor(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    discord_id: str = Field(min_length=1, max_length=32, pattern=r"^[0-9]+$")
    display_name: str = Field(min_length=1, max_length=128)
    role_ids: list[str] = Field(default_factory=list, max_length=100)

    @field_validator("role_ids")
    @classmethod
    def valid_role_ids(cls, values: list[str]) -> list[str]:
        if any(not re.fullmatch(r"[0-9]+", value) for value in values):
            raise ValueError("Discord role IDs must be numeric")
        return list(dict.fromkeys(values))


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
    hard_rule_ids: set[str] = Field(default_factory=set, max_length=250)
    custom_terms: list[str] = Field(default_factory=list, max_length=500)
    exceptions: list[str] = Field(default_factory=list, max_length=500)
    custom_regexes: list[str] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def thresholds_are_ordered(self):
        if self.shadow_threshold > self.alert_threshold:
            raise ValueError("shadow_threshold must not exceed alert_threshold")
        for expression in self.custom_regexes:
            if len(expression) > 300:
                raise ValueError("Custom regular expressions are limited to 300 chars")
            re.compile(expression, re.IGNORECASE)
        return self


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
        if self.suggested_action == SuggestedAction.TEMP_BAN:
            if self.suggested_duration_hours is None:
                raise ValueError("Temp bans require a suggested duration")
        elif self.suggested_duration_hours is not None:
            raise ValueError("Only temp bans may include a duration")
        return self


class ModerationFeedback(BaseModel):
    model_config = ConfigDict(extra="forbid")

    incident_id: str = Field(min_length=1, max_length=36)
    analysis_id: str = Field(min_length=1, max_length=36)
    actor: DiscordActor
    decision: Literal["accepted", "rejected", "overridden"]
    actual_action: SuggestedAction
    reason: str | None = Field(default=None, max_length=1000)


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


class DiscordInteractionRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    interaction_id: str = Field(min_length=1, max_length=32, pattern=r"^[0-9]+$")
    installation_id: str = Field(min_length=1, max_length=64)
    guild_id: str = Field(min_length=1, max_length=32, pattern=r"^[0-9]+$")
    channel_id: str = Field(min_length=1, max_length=32, pattern=r"^[0-9]+$")
    incident_id: str = Field(min_length=1, max_length=36)
    incident_revision: int = Field(ge=1)
    actor: DiscordActor
    operation: Literal[
        "claim",
        "unclaim",
        "resolve",
        "dismiss",
        "select_subject",
        "prepare_action",
        "feedback",
    ]
    payload: dict = Field(default_factory=dict)


class PreparedDestructiveAction(BaseModel):
    model_config = ConfigDict(extra="forbid")

    preparation_id: str = Field(min_length=1, max_length=36)
    incident_id: str = Field(min_length=1, max_length=36)
    incident_revision: int = Field(ge=1)
    action: SuggestedAction
    reason: str = Field(min_length=1, max_length=2000)
    preview: str = Field(min_length=1, max_length=2000)
    confirmation_token: str = Field(min_length=32, max_length=255)
    expires_at: datetime


_LEET_TRANSLATION = str.maketrans(
    {"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "7": "t", "8": "b"}
)


def normalize_candidate(value: str) -> str:
    value = unicodedata.normalize("NFKD", value.casefold()).translate(_LEET_TRANSLATION)
    value = "".join(char for char in value if not unicodedata.combining(char))
    value = re.sub(r"(.)\1{2,}", r"\1\1", value)
    return " ".join(re.sub(r"[^\w]+", " ", value).split())


class LocalPrefilterResult(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    suspicious: bool
    hard_hit: bool
    matched_rule_ids: list[str]
    fingerprint: str
    normalized_text: str


def prefilter_candidate(text: str, policy: ModerationPolicy) -> LocalPrefilterResult:
    normalized = normalize_candidate(text)[:4000]
    fingerprint = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    normalized_exceptions = {
        normalize_candidate(value) for value in policy.exceptions if value.strip()
    }
    if any(
        exception and exception in normalized for exception in normalized_exceptions
    ):
        return LocalPrefilterResult(
            suspicious=False,
            hard_hit=False,
            matched_rule_ids=[],
            fingerprint=fingerprint,
            normalized_text=normalized,
        )

    matched: list[str] = []
    compact_repetitions = lambda value: re.sub(r"(.)\1+", r"\1", value)
    for index, term in enumerate(policy.custom_terms):
        candidate = normalize_candidate(term)
        if candidate and (
            candidate in normalized
            or compact_repetitions(candidate) in compact_repetitions(normalized)
        ):
            matched.append(f"custom_term:{index}")
    for index, expression in enumerate(policy.custom_regexes):
        if re.search(expression, normalized, re.IGNORECASE):
            matched.append(f"custom_regex:{index}")

    hard_hit = bool(policy.hard_rule_ids.intersection(matched))
    return LocalPrefilterResult(
        suspicious=bool(matched),
        hard_hit=hard_hit,
        matched_rule_ids=matched,
        fingerprint=fingerprint,
        normalized_text=normalized,
    )


def analysis_visibility(
    analysis: ModerationAnalysis, policy: ModerationPolicy
) -> Literal["incident", "shadow", "ignore"]:
    if analysis.hard_hit or policy.hard_rule_ids.intersection(analysis.rule_ids):
        return "incident"
    if analysis.source == ModerationSource.REPORT:
        return "incident"
    if analysis.risk_score >= policy.alert_threshold:
        return "incident"
    if analysis.risk_score >= policy.shadow_threshold:
        return "shadow"
    return "ignore"


def validate_analysis_policy(
    analysis: ModerationAnalysis,
    policy: ModerationPolicy,
    *,
    expected_source: ModerationSource | None = None,
) -> None:
    """Revalidate centrally produced output at CRCON's trust boundary."""

    if expected_source is not None and analysis.source != expected_source:
        raise ValueError("Moderation analysis source does not match its job")
    if analysis.source not in policy.enabled_sources:
        raise ValueError("Moderation source is disabled by the active policy")
    if (
        analysis.policy_profile_id != policy.profile_id
        or analysis.policy_version != policy.version
    ):
        raise ValueError("Moderation analysis used a stale policy profile")
