from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, field_validator, model_validator

from rcon.user_config.utils import BaseUserConfig, set_user_config


class AutobalancerMessages(BaseModel):
    volunteer_request: str = Field(
        default=(
            "Die Teams sind unausgeglichen. Freiwilliger Wechsel zu {target_team}: "
            "Schreibe innerhalb von {seconds} Sekunden !balance."
        )
    )
    volunteer_registered: str = Field(
        default="Danke! Deine freiwillige Meldung gilt für diesen Balance-Vorfall."
    )
    candidate_selected: str = Field(
        default=(
            "Du wurdest für den Teamausgleich zu {target_team} ausgewählt. "
            "Der Wechsel erfolgt nach deinem nächsten Tod; danach bist du "
            "{cooldown_maps} Karten geschützt."
        )
    )
    switch_completed: str = Field(
        default=(
            "Danke für deine Mithilfe. Du wurdest zu {target_team} verschoben und "
            "bist nun {cooldown_maps} Karten vor einem weiteren "
            "Autobalance-Wechsel geschützt."
        )
    )

    @model_validator(mode="after")
    def validate_templates(self):
        try:
            self.volunteer_request.format(target_team="Axis", seconds=30)
            self.volunteer_registered.format()
            self.candidate_selected.format(target_team="Axis", cooldown_maps=3)
            self.switch_completed.format(target_team="Axis", cooldown_maps=3)
        except (KeyError, IndexError, ValueError) as exc:
            raise ValueError(f"Ungültiger Platzhalter in Nachrichtenvorlage: {exc}")
        return self


class AutobalancerUserConfig(BaseUserConfig):
    mode: Literal["disabled", "shadow", "manual", "auto"] = Field(
        default="disabled",
        description="disabled, shadow, manual or auto. Upstream defaults to disabled.",
    )
    poll_interval_seconds: int = Field(default=5, ge=2, le=60)
    target_difference: int = Field(default=2, ge=0, le=10)
    minimum_players: int = Field(default=40, ge=0, le=100)
    stable_difference_seconds: int = Field(default=45, ge=5, le=600)
    volunteer_phase_seconds: int = Field(default=30, ge=0, le=300)
    map_start_grace_minutes: int = Field(default=5, ge=0, le=60)
    map_end_guard_minutes: int = Field(default=10, ge=0, le=60)
    candidate_timeout_seconds: int = Field(default=180, ge=15, le=900)
    manual_proposal_timeout_seconds: int = Field(default=120, ge=15, le=900)
    connection_grace_seconds: int = Field(default=120, ge=0, le=1800)
    cooldown_maps: int = Field(default=3, ge=0, le=20)
    max_switches_per_incident: int = Field(default=3, ge=1, le=10)
    death_event_max_age_seconds: int = Field(default=5, ge=1, le=30)
    switch_confirmation_timeout_seconds: int = Field(default=15, ge=5, le=60)
    history_server_numbers: list[int] = Field(default_factory=list)
    volunteer_command: str = Field(default="!balance", min_length=2, max_length=32)
    messages: AutobalancerMessages = Field(default_factory=AutobalancerMessages)

    @field_validator("volunteer_command")
    @classmethod
    def validate_volunteer_command(cls, value: str) -> str:
        value = value.strip()
        if not value.startswith("!") or any(character.isspace() for character in value):
            raise ValueError("volunteer_command muss ein einzelner !Chatbefehl sein")
        return value

    @model_validator(mode="after")
    def validate_windows(self):
        if self.target_difference < 0:
            raise ValueError("target_difference must be non-negative")
        if self.max_switches_per_incident < 1:
            raise ValueError("max_switches_per_incident must be at least one")
        return self

    @staticmethod
    def save_to_db(values: dict, dry_run: bool = False):
        validated = AutobalancerUserConfig.model_validate(values)
        if not dry_run:
            set_user_config(AutobalancerUserConfig.KEY(), validated)
        return True
