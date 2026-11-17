from datetime import datetime
from enum import Enum

import os
import pydantic
from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer

from django.conf import settings as django_settings
from rcon.types import GameEnum

_standalone_channel_layer = None


def _get_barricade_channel_layer():
    """Resolve Channels lazily without configuring global Django settings."""
    if django_settings.configured or os.getenv("DJANGO_SETTINGS_MODULE"):
        return get_channel_layer()

    global _standalone_channel_layer
    if _standalone_channel_layer is None:
        from channels_redis.core import RedisChannelLayer

        _standalone_channel_layer = RedisChannelLayer(
            hosts=[{"address": os.getenv("HLL_REDIS_URL")}]
        )
    return _standalone_channel_layer

GROUP_NAME = "barricade"


class ClientRequestType(str, Enum):
    BAN_PLAYERS = "ban_players"
    UNBAN_PLAYERS = "unban_players"
    NEW_REPORT = "new_report"


class ServerRequestType(str, Enum):
    SCAN_PLAYERS = "scan_players"


class RequestBody(pydantic.BaseModel):
    id: int
    request: ClientRequestType | ServerRequestType
    payload: dict | None = None

    def response_ok(self, payload: dict | None = None):
        return ResponseBody(id=self.id, response=payload)

    def response_error(self, error: str, **kwargs: str):
        return ResponseBody(
            id=self.id, response={"error": error, **kwargs}, failed=True
        )


class ResponseBody(pydantic.BaseModel):
    id: int
    request: None = None
    response: dict | None
    failed: bool = False


class UnbanPlayersRequestConfigPayload(pydantic.BaseModel):
    banlist_id: str
    game: str | None = None


class BanPlayersRequestConfigPayload(UnbanPlayersRequestConfigPayload):
    reason: str


class BanPlayersRequestPayload(pydantic.BaseModel):
    player_ids: dict[str, str | None]
    config: BanPlayersRequestConfigPayload


class ScanPlayersRequestPayload(pydantic.BaseModel):
    player_ids: list[str]
    game: str


class UnbanPlayersRequestPayload(pydantic.BaseModel):
    # Even though in theory these can all be converted to ints, we should safely
    # filter out all invalid record IDs later.
    record_ids: list[str] = pydantic.Field(alias="ban_ids")
    config: UnbanPlayersRequestConfigPayload


class NewReportRequestPayloadPlayer(pydantic.BaseModel):
    player_id: str
    player_name: str
    bm_rcon_url: str | None


class NewReportRequestPayload(pydantic.BaseModel):
    game: str | None = None
    created_at: datetime
    body: str
    reasons: list[str]
    attachment_urls: list[str]
    players: list[NewReportRequestPayloadPlayer]


class BarricadeRequestError(Exception):
    def __init__(self, error: str, **kwargs: str) -> None:
        self.error = error
        self.kwargs = kwargs

    def __str__(self) -> str:
        return self.error


def barricade_game_for_server() -> str:
    """Map the configured game to Barricade's public protocol values."""
    game = GameEnum(os.getenv('HLL_GAME') or GameEnum.HLL_WW2)
    return 'HLLV' if game == GameEnum.HLL_VIETNAM else 'HLL'


def validate_barricade_game(game: str | None) -> None:
    """Reject an explicitly different game; retain legacy peers without one."""
    if game is not None and game != barricade_game_for_server():
        raise BarricadeRequestError('Request game does not match this server')


def send_to_barricade(request_type: ServerRequestType, payload: dict | None):
    channel_layer = _get_barricade_channel_layer()
    async_to_sync(channel_layer.group_send)(
        GROUP_NAME,
        {
            "type": "handle_broadcast",
            "request_type": request_type.value,
            "payload": payload,
        },
    )
