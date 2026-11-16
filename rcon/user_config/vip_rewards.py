"""Additional VIP rewards. Seed-VIP remains a separate policy."""

from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo
from uuid import uuid4
import re

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from rcon.user_config.utils import BaseUserConfig, set_user_config


class RewardRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    hours: float = Field(default=2, gt=0, le=8760)
    limit: int = Field(default=1, ge=1, le=1000)
    limit_period: Literal["rolling_day", "day", "week", "month"] = "rolling_day"


class RoundRule(RewardRule):
    minutes: int = Field(default=30, ge=1)
    fraction: float = Field(default=0.7, gt=0, le=1)
    limit: int = Field(default=2, ge=1, le=1000)


class WeeklyRule(RewardRule):
    hours: float = Field(default=6, gt=0, le=8760)
    days: int = Field(default=3, ge=1, le=7)
    minutes: int = Field(default=30, ge=1)


class WeeklySupportRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    points: int = Field(default=5000, ge=1, le=100000000, strict=True)
    hours: float = Field(default=6, gt=0, le=8760)


class Milestone(BaseModel):
    model_config = ConfigDict(extra="forbid")
    play_hours: int = Field(gt=0)
    hours: float = Field(gt=0, le=8760)


class MilestoneRule(BaseModel):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    milestones: list[Milestone] = Field(
        default_factory=lambda: [
            Milestone(play_hours=10, hours=4),
            Milestone(play_hours=50, hours=8),
            Milestone(play_hours=100, hours=12),
        ]
    )

    @field_validator("milestones")
    @classmethod
    def unique(cls, values):
        if len({x.play_hours for x in values}) != len(values):
            raise ValueError("Spielzeit-Meilensteine müssen eindeutig sein")
        return values


class BalanceRule(RewardRule):
    minutes: int = Field(default=15, ge=1)
    difference: int = Field(default=4, ge=2, le=50)
    signup_minutes: int = Field(default=5, ge=1, le=30)


class EventRule(RewardRule):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=120)
    start: datetime
    end: datetime
    minutes: int = Field(default=60, ge=1)
    hours: float = Field(default=4, gt=0, le=8760)

    @model_validator(mode="after")
    def window(self):
        if (
            self.start.tzinfo is None
            or self.end.tzinfo is None
            or self.end <= self.start
        ):
            raise ValueError("Zeitraum benötigt Zeitzone und Ende nach Beginn")
        return self


class ChallengeRule(RewardRule):
    id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,64}$")
    name: str = Field(min_length=1, max_length=120)
    weapons: list[str] = Field(default_factory=list)
    kills: int = Field(default=10, ge=1)
    period: Literal["day", "week", "fixed"] = "day"
    start: datetime | None = None
    end: datetime | None = None

    @model_validator(mode="after")
    def window(self):
        if self.period == "fixed":
            if (
                not self.start
                or not self.end
                or not self.start.tzinfo
                or not self.end.tzinfo
                or self.end <= self.start
            ):
                raise ValueError(
                    "Feste Challenge benötigt einen gültigen Zeitraum mit Zeitzone"
                )
        if self.enabled and not self.weapons:
            raise ValueError("Bitte mindestens eine Waffe für die aktive Challenge auswählen")
        if any(not w.strip() for w in self.weapons):
            raise ValueError("Leere Waffennamen sind nicht erlaubt")
        return self


class VipRewardsUserConfig(BaseUserConfig):
    model_config = ConfigDict(extra="forbid")
    enabled: bool = False
    revision: str = Field(
        default="", max_length=64, json_schema_extra={"readOnly": True}
    )
    dry_run: bool = True
    pause_during_seeding: bool = True
    daily_hours: float = Field(default=24, gt=0, le=8760)
    timezone: str = "Europe/Berlin"
    notify_player: bool = True
    message_language: Literal["de", "en", "fr"] = "de"
    status_command: str = "!rewards"
    excluded_player_ids: list[str] = Field(default_factory=list)
    opponent_cooldown_minutes: int = Field(default=30, ge=1)
    melee: RewardRule = Field(default_factory=lambda: RewardRule(limit=3))
    round: RoundRule = Field(default_factory=RoundRule)
    weekly: WeeklyRule = Field(default_factory=WeeklyRule)
    weekly_support: WeeklySupportRule = Field(default_factory=WeeklySupportRule)
    milestones: MilestoneRule = Field(default_factory=MilestoneRule)
    balance: BalanceRule = Field(default_factory=BalanceRule)
    events: list[EventRule] = Field(default_factory=list, max_length=100)
    challenges: list[ChallengeRule] = Field(default_factory=list, max_length=100)

    def policy_signature(self):
        # Message language does not change eligibility. Excluding the new field
        # also preserves signatures created before the language setting existed.
        return self.model_dump_json(exclude={"message_language"})

    @field_validator("status_command")
    @classmethod
    def valid_status_command(cls, value):
        value = value.strip().casefold()
        if value and not re.fullmatch(r"![a-z][a-z0-9_-]{0,31}", value):
            raise ValueError("Statusbefehl: ein !Befehl ohne Leerzeichen oder leer zum Abschalten")
        if value in {"!balance", "!admin", "!yes", "!no", "!vip"}:
            raise ValueError("Dieser Befehl ist bereits für eine andere Funktion reserviert")
        return value

    @field_validator("timezone")
    @classmethod
    def valid_zone(cls, value):
        try:
            ZoneInfo(value)
        except (KeyError, ValueError):
            raise ValueError("Unbekannte Zeitzone")
        return value

    @field_validator("excluded_player_ids")
    @classmethod
    def valid_ids(cls, values):
        values = list(dict.fromkeys(v.strip() for v in values if v.strip()))
        if any(
            not re.fullmatch(r"(?:[0-9]{17}|[a-fA-F0-9]{32})", value)
            for value in values
        ):
            raise ValueError(
                "Ausschlüsse benötigen eine Steam-ID oder eine 32-stellige Spieler-ID"
            )
        return values

    @model_validator(mode="after")
    def unique_ids(self):
        for rules in (self.events, self.challenges):
            if len({r.id for r in rules}) != len(rules):
                raise ValueError("Event-/Challenge-IDs müssen eindeutig sein")
        return self

    @staticmethod
    def save_to_db(values, dry_run=False):
        config = VipRewardsUserConfig.model_validate(values)
        if config.status_command:
            from rcon.vip_rewards.service import status_command_conflict
            if status_command_conflict(config.status_command):
                raise ValueError("Statusbefehl wird bereits von einer anderen Funktion verwendet")
        if not dry_run:
            config.revision = uuid4().hex
            set_user_config(VipRewardsUserConfig.KEY(), config.model_dump(mode="json"))
