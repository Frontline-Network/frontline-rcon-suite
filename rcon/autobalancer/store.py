from __future__ import annotations

import hashlib
import json
import logging
import uuid
from datetime import datetime
from typing import Any

from rcon.cache_utils import get_redis_client
from rcon.utils import get_server_number

logger = logging.getLogger(__name__)

RENEW_LEADER_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('expire', KEYS[1], ARGV[2])
end
return 0
"""

RELEASE_LEADER_SCRIPT = """
if redis.call('get', KEYS[1]) == ARGV[1] then
    return redis.call('del', KEYS[1])
end
return 0
"""


class AutobalancerStore:
    """Namespaced Redis state shared by log hooks, API workers and the leader."""

    def __init__(self, redis_client=None, server_number: int | str | None = None):
        self.red = redis_client or get_redis_client()
        self.server_number = str(server_number or get_server_number())
        self.prefix = f"autobalancer:{self.server_number}"

    def key(self, suffix: str) -> str:
        return f"{self.prefix}:{suffix}"

    def load_state(self) -> dict[str, Any]:
        raw = self.red.get(self.key("state"))
        return json.loads(raw) if raw else {}

    def save_state(self, state: dict[str, Any], ttl: int = 8 * 3600) -> None:
        self.red.set(self.key("state"), json.dumps(state, default=str), ex=ttl)

    def clear_runtime_state(self, preserve_cursor: bool = True) -> None:
        keys = [
            self.key("state"),
            self.key("status"),
            self.key("memberships"),
            self.key("armed_player"),
            self.key("active"),
        ]
        if not preserve_cursor:
            keys.append(self.key("event_cursor"))
        self.red.delete(*keys)

    def save_status(self, status: dict[str, Any]) -> None:
        self.red.set(self.key("status"), json.dumps(status, default=str), ex=60)

    def load_status(self) -> dict[str, Any]:
        raw = self.red.get(self.key("status"))
        return (
            json.loads(raw)
            if raw
            else {
                "mode": "disabled",
                "phase": "idle",
                "block_reasons": [
                    "Autobalancer-Dienst liefert keinen aktuellen Status"
                ],
            }
        )

    def set_active(self, active: bool) -> None:
        if active:
            self.red.set(self.key("active"), "1", ex=30)
        else:
            self.red.delete(self.key("active"))

    def is_active(self) -> bool:
        return bool(self.red.exists(self.key("active")))

    def arm_player(self, player_id: str | None) -> None:
        if player_id:
            self.red.set(self.key("armed_player"), player_id, ex=15 * 60)
        else:
            self.red.delete(self.key("armed_player"))

    def is_armed_player(self, player_id: str | None) -> bool:
        return bool(player_id and self.red.get(self.key("armed_player")) == player_id)

    def acquire_leader(self, token: str, ttl: int = 30) -> bool:
        return bool(self.red.set(self.key("leader"), token, nx=True, ex=ttl))

    def renew_leader(self, token: str, ttl: int = 30) -> bool:
        return bool(
            self.red.eval(RENEW_LEADER_SCRIPT, 1, self.key("leader"), token, ttl)
        )

    def release_leader(self, token: str) -> None:
        self.red.eval(RELEASE_LEADER_SCRIPT, 1, self.key("leader"), token)

    def acquire_execution(self, token: str, ttl: int = 30) -> bool:
        return bool(self.red.set(self.key("execution"), token, nx=True, ex=ttl))

    def release_execution(self, token: str) -> None:
        self.red.eval(RELEASE_LEADER_SCRIPT, 1, self.key("execution"), token)

    def publish_event(self, event_type: str, payload: dict[str, Any]) -> str | None:
        canonical = json.dumps(
            {"type": event_type, **payload}, sort_keys=True, default=str
        )
        event_key = (
            payload.get("event_id")
            or hashlib.sha256(canonical.encode("utf-8")).hexdigest()
        )
        if not self.red.set(self.key(f"event_seen:{event_key}"), "1", nx=True, ex=3600):
            return None
        return self.red.xadd(
            self.key("events"),
            {"type": event_type, "payload": canonical},
            maxlen=2000,
            approximate=True,
        )

    def read_events(self, count: int = 100) -> list[dict[str, Any]]:
        cursor = self.red.get(self.key("event_cursor")) or "0-0"
        streams = self.red.xread({self.key("events"): cursor}, count=count, block=1)
        result: list[dict[str, Any]] = []
        for _, entries in streams:
            for stream_id, fields in entries:
                payload = json.loads(fields["payload"])
                payload["type"] = fields["type"]
                payload["stream_id"] = stream_id
                result.append(payload)
                cursor = stream_id
        return result

    def acknowledge_events(self, events: list[dict[str, Any]]) -> None:
        """Advance the durable cursor only after the service persisted its state."""
        if events and events[-1].get("stream_id"):
            self.red.set(self.key("event_cursor"), events[-1]["stream_id"])

    def track_squad_memberships(
        self,
        round_id: str,
        memberships: dict[str, str | None],
        now: datetime,
    ) -> dict[str, int]:
        raw = self.red.get(self.key("memberships"))
        stored = json.loads(raw) if raw else {"round_id": round_id, "players": {}}
        if stored.get("round_id") != round_id:
            stored = {"round_id": round_id, "players": {}}
        players = stored["players"]
        now_ts = int(now.timestamp())
        current_ids = set(memberships)
        for stale_id in set(players) - current_ids:
            players.pop(stale_id, None)
        durations: dict[str, int] = {}
        for player_id, squad_key in memberships.items():
            previous = players.get(player_id)
            if not previous or previous.get("squad_key") != squad_key:
                previous = {"squad_key": squad_key, "joined_at": now_ts}
                players[player_id] = previous
            durations[player_id] = max(0, now_ts - int(previous["joined_at"]))
        self.red.set(self.key("memberships"), json.dumps(stored), ex=8 * 3600)
        return durations


def new_instance_token() -> str:
    return uuid.uuid4().hex
