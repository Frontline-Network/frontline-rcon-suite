"""Narrow, non-executable AI report interpretation; mirrored by CRCON."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator


class ReportReasonDecision(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    rule: Literal["communication", "teamkills", "cheating", "manual"]
    target_kind: Literal["player", "squad", "commander", "none"]
    target_text: str = Field(max_length=255)
    allegation_excerpt: str = Field(max_length=1000)
    unambiguous: bool
    uncertainties: list[Annotated[str, Field(max_length=250)]] = Field(max_length=8)
    rationale: str = Field(min_length=1, max_length=500)


class ReportReasonRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)

    installation_id: str = Field(min_length=1, max_length=64)
    incident_id: str = Field(min_length=1, max_length=36)
    server_number: int = Field(ge=1, le=10000)
    message: str = Field(min_length=1, max_length=4000)
    # Handles/roles only, no platform IDs or account history for the model.
    roster: list[dict[str, str]] = Field(max_length=150)
    reporter_name: str = Field(max_length=255)
    reporter_team: str = Field(max_length=32)
    ai_provider: Literal["api_key", "codex"]
    ai_model: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9._:-]+$")
    api_key: str | None = Field(default=None, min_length=20, max_length=500, repr=False)

    @field_validator("roster")
    @classmethod
    def bounded_public_roster(cls, value):
        allowed = {"name", "team", "role", "squad"}
        if any(
            set(row) - allowed or any(len(v) > 255 for v in row.values())
            for row in value
        ):
            raise ValueError("Only bounded public roster fields are allowed")
        return value
