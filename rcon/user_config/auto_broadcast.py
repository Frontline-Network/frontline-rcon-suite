from __future__ import annotations

import re
from typing import ClassVar, Iterable, Literal, TypedDict

from pydantic import BaseModel, Field, field_validator, model_validator

from rcon.user_config.utils import BaseUserConfig, _listType, key_check, set_user_config


class AutoBroadcastType(TypedDict):
    enabled: bool
    randomize: bool
    messages: Iterable[str | AutoBroadcastMessageType]


class AutoBroadcastMessageType(TypedDict, total=False):
    id: str
    title: str
    enabled: bool
    time_sec: int
    message: str
    min_players: int
    max_players: int
    pause_during_seeding: bool


class AutoBroadcastMessage(BaseModel):
    """A scheduled in-game campaign.

    The original auto-broadcast format only contained ``time_sec`` and
    ``message``.  All additional fields have conservative defaults so existing
    installations keep their exact behaviour when the richer campaign editor
    is introduced.
    """

    id: str = Field(default="", max_length=64)
    title: str = Field(default="", max_length=80)
    enabled: bool = Field(default=True, strict=True)
    time_sec: int = Field(ge=1)
    message: str
    min_players: int = Field(default=0, ge=0, le=100)
    max_players: int = Field(default=100, ge=0, le=100)
    pause_during_seeding: bool = Field(default=False, strict=True)

    @model_validator(mode="after")
    def validate_player_range(self):
        if self.max_players < self.min_players:
            raise ValueError("max_players must be greater than or equal to min_players")
        return self


class RawAutoBroadCastMessage(BaseModel):
    pattern: ClassVar = re.compile(r"(\d+) (.+)")
    value: str

    @staticmethod
    def split(value):
        return value.split(" ", 1)

    @property
    def time_and_message(self):
        time, message = self.split(self.value)
        return time, message

    @field_validator("value")
    @classmethod
    def validiate_time_and_message(cls, v):
        if match := re.match(cls.pattern, v):
            time, message = match.groups()
            return v
        else:
            raise ValueError(
                "Broacast message must be tuples (<int: seconds>, <str: message>)"
            )


class AutoBroadcastUserConfig(BaseUserConfig):
    enabled: bool = Field(default=False, strict=True, title="Enable", description="Enable auto broadcasts")
    randomize: bool = Field(default=False, strict=True, title="Randomize messages", description="Set broadcasts in random order")
    messages: list[AutoBroadcastMessage] = Field(default_factory=list, title="Messages", description="A list of dicts with `time_sec` (length in seconds the broadcast is set for) and `message` (the broadcast message) keys")

    @staticmethod
    def save_to_db(values: AutoBroadcastType, dry_run=False):
        key_check(
            AutoBroadcastType.__required_keys__,
            AutoBroadcastType.__optional_keys__,
            values.keys(),
        )

        raw_messages = values.get("messages")
        _listType(values=raw_messages)  # type: ignore

        validated_messages = []
        raw_message: str
        for raw_message in raw_messages:
            if isinstance(raw_message, dict):
                # The campaign editor sends structured objects.  Pydantic also
                # accepts legacy objects containing only time_sec and message.
                validated_messages.append(AutoBroadcastMessage.model_validate(raw_message))
            # The UI passes these in as strings
            else:
                raw_message = raw_message.replace("\\n", "\n")
                time, message = RawAutoBroadCastMessage(
                    value=raw_message
                ).time_and_message
                validated_messages.append(
                    AutoBroadcastMessage(time_sec=int(time), message=message)
                )

        validated_conf = AutoBroadcastUserConfig(
            enabled=values.get("enabled"),
            randomize=values.get("randomize"),
            messages=validated_messages,
        )

        if not dry_run:
            set_user_config(AutoBroadcastUserConfig.KEY(), validated_conf)
