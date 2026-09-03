from __future__ import annotations

import re
import uuid
from typing import ClassVar, Iterable, Literal, TypedDict

from pydantic import BaseModel, Field, field_validator, model_validator

from rcon.user_config.utils import BaseUserConfig, _listType, key_check, set_user_config


class AutoBroadcastRequiredType(TypedDict):
    enabled: bool
    randomize: bool
    messages: Iterable[str | AutoBroadcastMessageType]


class VipLifecycleMessagesType(TypedDict, total=False):
    unverified: str
    trial_active: str
    trial_expiring: str
    trial_expired: str


class VipLifecycleConfigType(TypedDict, total=False):
    enabled: bool
    server_family: Literal["hll", "hll_vietnam"]
    expiry_window_hours: int
    unverified_cooldown_days: int
    status_cache_seconds: int
    test_mode: bool
    messages: VipLifecycleMessagesType


class AutoBroadcastType(AutoBroadcastRequiredType, total=False):
    player_message_interval_sec: int
    player_message_gap_sec: int
    vip_lifecycle: VipLifecycleConfigType


class VipLifecycleMessages(BaseModel):
    unverified: str = (
        "Volle Server? Sichere dir einmalig 7 Tage VIP gratis – bevorzugter "
        "Zugang, kein Abo: fln.gg/vip"
    )
    trial_active: str = (
        "Mit VIP kommst du bei vollen Servern bevorzugt in die Warteschlange. "
        "Deine Laufzeit und Angebote findest du unter fln.gg/vip"
    )
    trial_expiring: str = (
        "Dein Gratis-VIP endet bald – verlängere ab 4,99 € für 30 Tage. "
        "Kein Abo: fln.gg/vip"
    )
    trial_expired: str = (
        "Dein Gratis-VIP ist abgelaufen. Vietnam-VIP gibt es für 30, 90, 180 "
        "oder 365 Tage – ohne Abo: fln.gg/vip"
    )


class VipLifecycleConfig(BaseModel):
    """Status-driven, personal VIP communication.

    The feature is deliberately disabled by default. Existing campaign
    installations therefore keep their behaviour until an administrator has
    configured the authenticated WordPress status endpoint and enables it.
    """

    enabled: bool = Field(default=False, strict=True)
    server_family: Literal["hll", "hll_vietnam"] = "hll_vietnam"
    expiry_window_hours: int = Field(default=48, ge=1, le=168)
    unverified_cooldown_days: int = Field(default=7, ge=1, le=90)
    status_cache_seconds: int = Field(default=60, ge=30, le=900)
    test_mode: bool = Field(default=False, strict=True)
    messages: VipLifecycleMessages = Field(default_factory=VipLifecycleMessages)


class AutoBroadcastMessageType(TypedDict, total=False):
    id: str
    title: str
    enabled: bool
    time_sec: int
    message: str
    min_players: int
    max_players: int
    pause_during_seeding: bool
    delivery_mode: Literal["broadcast", "player_message"]
    min_session_minutes: int
    recipient_group: Literal["all", "vip", "non_vip"]


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
    delivery_mode: Literal["broadcast", "player_message"] = "broadcast"
    min_session_minutes: int = Field(default=5, ge=1, le=1440)
    recipient_group: Literal["all", "vip", "non_vip"] = "all"

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
    enabled: bool = Field(
        default=False, strict=True, title="Enable", description="Enable auto broadcasts"
    )
    randomize: bool = Field(
        default=False,
        strict=True,
        title="Randomize messages",
        description="Set broadcasts in random order",
    )
    messages: list[AutoBroadcastMessage] = Field(
        default_factory=list,
        title="Messages",
        description="A list of dicts with `time_sec` (length in seconds the broadcast is set for) and `message` (the broadcast message) keys",
    )
    player_message_interval_sec: int = Field(default=10, ge=5, le=300)
    player_message_gap_sec: int = Field(default=300, ge=60, le=3600)
    vip_lifecycle: VipLifecycleConfig = Field(default_factory=VipLifecycleConfig)

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
        campaign_ids: set[str] = set()
        raw_message: str
        for raw_message in raw_messages:
            if isinstance(raw_message, dict):
                # The campaign editor sends structured objects.  Pydantic also
                # accepts legacy objects containing only time_sec and message.
                campaign = AutoBroadcastMessage.model_validate(raw_message)
            # The UI passes these in as strings
            else:
                raw_message = raw_message.replace("\\n", "\n")
                time, message = RawAutoBroadCastMessage(
                    value=raw_message
                ).time_and_message
                campaign = AutoBroadcastMessage(time_sec=int(time), message=message)

            if not campaign.id:
                campaign.id = f"campaign-{uuid.uuid4()}"
            if campaign.id in campaign_ids:
                raise ValueError(f"Campaign ids must be unique: {campaign.id}")
            campaign_ids.add(campaign.id)
            validated_messages.append(campaign)

        validated_conf = AutoBroadcastUserConfig(
            enabled=values.get("enabled"),
            randomize=values.get("randomize"),
            messages=validated_messages,
            player_message_interval_sec=values.get("player_message_interval_sec", 10),
            player_message_gap_sec=values.get("player_message_gap_sec", 300),
            vip_lifecycle=values.get("vip_lifecycle", {}),
        )

        if not dry_run:
            set_user_config(AutoBroadcastUserConfig.KEY(), validated_conf)
