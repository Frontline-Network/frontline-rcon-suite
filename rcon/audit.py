import json
import logging
from typing import List

from redis import BlockingConnectionPool, Redis

from rcon.cache_utils import get_redis_pool
from rcon.rcon import get_rcon
from rcon.types import AdminUserType

logger = logging.getLogger(__name__)

HEARTBEAT_KEY_PREFIX = "heartbeat_"
HEARTBEAT_REGISTRY_KEY = "online_mod_heartbeat_registry"
HEARTBEAT_REGISTRY_SENTINEL = "__initialized__"
KNOWN_MODS_KEY = "mods"
PLAYER_ID = "player_id"

RED_POOL = None


def _red():
    # poor man's singleton
    red = get_redis_pool()
    global RED_POOL
    if not RED_POOL:
        RED_POOL = BlockingConnectionPool(max_connections=4)

    return Redis(connection_pool=red)


def _heartbeat_key(uniqueid):
    return f"{HEARTBEAT_KEY_PREFIX}{uniqueid}"


def heartbeat(username, player_id, timeout=120):
    red = _red()
    heartbeat_key = _heartbeat_key(username)
    with red.pipeline() as pipe:
        pipe.setex(
            heartbeat_key,
            timeout,
            json.dumps(dict(username=username, player_id=player_id)),
        )
        pipe.sadd(HEARTBEAT_REGISTRY_KEY, heartbeat_key)
        result = pipe.execute()
    return bool(result[0])


# This exists only no to create a weird interdependancy / tight coupling with the API layer.
# Ideally we'd extract the services (i.e. broadcast, logs_event, etc) in a separated package, and let them
# use a service account to talk the the API.
def set_registered_mods(moderators_name_steamids: List[tuple]):
    red = _red()

    logger.warning("Registering mods: %s", moderators_name_steamids)

    red.delete("moderators")
    for k, v in moderators_name_steamids:
        red.hset("moderators", k, v)


def online_mods() -> list[AdminUserType]:
    red = _red()
    registered = {
        value.decode() if isinstance(value, bytes) else str(value)
        for value in red.smembers(HEARTBEAT_REGISTRY_KEY)
    }

    if HEARTBEAT_REGISTRY_SENTINEL not in registered:
        # Existing deployments can have up to two minutes of live heartbeat
        # keys that predate the registry. Import them once, then every producer
        # maintains the bounded set directly and the read path never scans the
        # shared Redis database again.
        registered.update(
            value.decode() if isinstance(value, bytes) else str(value)
            for value in red.scan_iter(
                match=f"{HEARTBEAT_KEY_PREFIX}*",
                count=500,
            )
        )
        red.sadd(
            HEARTBEAT_REGISTRY_KEY,
            HEARTBEAT_REGISTRY_SENTINEL,
            *registered,
        )

    heartbeat_keys = sorted(registered - {HEARTBEAT_REGISTRY_SENTINEL})
    if not heartbeat_keys:
        return []

    values = red.mget(heartbeat_keys)
    expired_keys = [
        heartbeat_key
        for heartbeat_key, value in zip(heartbeat_keys, values)
        if value is None
    ]
    if expired_keys:
        red.srem(HEARTBEAT_REGISTRY_KEY, *expired_keys)

    return [json.loads(value) for value in values if value is not None]


def ingame_mods(rcon=None) -> list[AdminUserType]:
    red = _red()
    mods = red.hgetall("moderators") or {}

    if not mods:
        return []

    rcon = rcon or get_rcon()
    players = rcon.get_players()
    mods_ids = set(v.decode() for v in mods.values())
    ig_mods: list[AdminUserType] = []
    for player in players:
        if player[PLAYER_ID] in mods_ids:
            ig_mods.append({"username": player["name"], PLAYER_ID: player[PLAYER_ID]})

    return ig_mods


if __name__ == "__main__":
    heartbeat("test", "42")
    online = online_mods()
    print("online: ", online)
    set_registered_mods([("bla", "76561197984877751")])
    print(ingame_mods())
