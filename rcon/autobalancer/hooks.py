from __future__ import annotations

import logging
import re

from rcon.logs.loop import (
    on_chat,
    on_kill,
    on_match_end,
    on_match_start,
    on_team_switch,
    on_tk,
)
from rcon.user_config.autobalancer import AutobalancerUserConfig

from .store import AutobalancerStore

logger = logging.getLogger(__name__)

TEAM_SWITCH_PLAYER_ID = re.compile(r"\((?:Allies|Axis)/([^)]+)\)\s*->")


def _store() -> AutobalancerStore | None:
    try:
        return AutobalancerStore()
    except Exception:
        logger.exception("Autobalancer Redis store is unavailable")
        return None


def _publish(event_type: str, struct_log, **payload) -> None:
    store = _store()
    if store is None:
        return
    try:
        store.publish_event(
            event_type,
            {
                "event_id": str(
                    struct_log.get("raw") or struct_log.get("timestamp_ms")
                ),
                "timestamp_ms": struct_log.get("timestamp_ms"),
                **payload,
            },
        )
    except Exception:
        logger.exception("Unable to publish autobalancer %s event", event_type)


@on_chat
def autobalancer_volunteer(rcon, struct_log):
    store = _store()
    if store is None or not store.is_active():
        return
    state = store.load_state()
    if state.get("phase") != "volunteer":
        return
    config = AutobalancerUserConfig.load_from_db()
    message = str(struct_log.get("sub_content") or struct_log.get("message") or "")
    if message.strip().casefold() != config.volunteer_command.casefold():
        return
    _publish(
        "volunteer",
        struct_log,
        player_id=struct_log.get("player_id_1"),
        player_name=struct_log.get("player_name_1"),
        incident_id=state.get("incident_id"),
    )


def _death(struct_log) -> None:
    victim_id = struct_log.get("player_id_2")
    store = _store()
    if store is None or not store.is_armed_player(victim_id):
        return
    _publish(
        "death",
        struct_log,
        player_id=victim_id,
        player_name=struct_log.get("player_name_2"),
    )


@on_kill
def autobalancer_kill(rcon, struct_log):
    _death(struct_log)


@on_tk
def autobalancer_team_kill(rcon, struct_log):
    _death(struct_log)


@on_team_switch
def autobalancer_team_switch(rcon, struct_log):
    store = _store()
    if store is None or not store.is_active():
        return
    player_name = str(struct_log.get("player_name_1") or "").strip()
    player_id = struct_log.get("player_id_1")
    if not player_id and (match := TEAM_SWITCH_PLAYER_ID.search(player_name)):
        player_id = match.group(1)
        player_name = player_name[: match.start()].strip()
    _publish(
        "team_switch",
        struct_log,
        player_id=player_id,
        player_name=player_name,
        message=struct_log.get("message"),
    )


@on_match_start
def autobalancer_match_start(rcon, struct_log):
    store = _store()
    if store is not None and store.is_active():
        _publish("match_start", struct_log)


@on_match_end
def autobalancer_match_end(rcon, struct_log):
    store = _store()
    if store is not None and store.is_active():
        _publish("match_end", struct_log)
