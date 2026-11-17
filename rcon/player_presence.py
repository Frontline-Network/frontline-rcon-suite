"""Validate bounded, cross-server player observations without inferring absence."""

from __future__ import annotations

from dataclasses import dataclass
import hashlib
import json
import logging
import math
import os
import threading
import time
from typing import Any, Iterable

from sqlalchemy.engine import make_url


MAX_PLAYERS = 250
MAX_OBSERVATION_SECONDS = 10.0
SNAPSHOT_TTL_SECONDS = 45
MAX_SNAPSHOT_AGE_SECONDS = 30.0
POLL_INTERVAL_SECONDS = 15.0
FAILURE_LOG_INTERVAL_SECONDS = 300.0
logger = logging.getLogger(__name__)

_STORE_IF_NEWER = """
local previous = redis.call('GET', KEYS[1])
if previous then
  local ok, decoded = pcall(cjson.decode, previous)
  if ok and type(decoded) == 'table' and type(decoded.started_at) == 'number'
      and decoded.started_at >= tonumber(ARGV[1]) then
    return 0
  end
end
redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
return 1
"""


@dataclass(frozen=True)
class PresenceWindow:
    """The server observed a player at some instant within this interval."""

    earliest: float
    latest: float


def validated_observation(
    payload: Any, *, server_number: int, now: float, max_age: float
) -> tuple[PresenceWindow, tuple[str, ...]] | None:
    """Accept only a fresh complete roster; invalid data conveys no presence."""
    if (
        type(server_number) is not int or not 1 <= server_number <= 32
        or not isinstance(payload, dict) or type(payload.get('version')) is not int
        or payload['version'] != 1
        or type(payload.get('server_number')) is not int
        or payload['server_number'] != server_number
        or not isinstance(payload.get('players'), list)
        or len(payload['players']) > MAX_PLAYERS
        or type(now) not in (int, float) or type(max_age) not in (int, float)
        or not math.isfinite(now) or not math.isfinite(max_age) or max_age <= 0
    ):
        return None
    start, end = payload.get('started_at'), payload.get('finished_at')
    if (type(start) not in (int, float) or type(end) not in (int, float)
            or not math.isfinite(start) or not math.isfinite(end)):
        return None
    if not (0 < start <= end <= now and end - start <= MAX_OBSERVATION_SECONDS
            and now - start <= max_age):
        return None
    players = payload['players']
    if any(not isinstance(pid, str) or not pid.strip() or pid != pid.strip()
           or len(pid) > 100 for pid in players):
        return None
    if len(set(players)) != len(players):
        return None
    return PresenceWindow(start, end), tuple(players)


def merge_observations(
    observations: Iterable[tuple[PresenceWindow, Iterable[str]]],
) -> dict[str, PresenceWindow]:
    """Bound each player's latest sighting across independently observed servers."""
    result: dict[str, PresenceWindow] = {}
    for window, players in observations:
        for player_id in players:
            previous = result.get(player_id)
            result[player_id] = (
                PresenceWindow(max(previous.earliest, window.earliest),
                               max(previous.latest, window.latest))
                if previous is not None else window
            )
    return result


def database_scope(database_url: str) -> str:
    """Separate snapshots for different databases without exposing credentials."""
    url = make_url(database_url)
    if not url.drivername.startswith('postgresql') or not url.host or not url.database:
        raise ValueError('A network PostgreSQL database is required for shared presence')
    identity = url.set(password=None).render_as_string(hide_password=True)
    return hashlib.sha256(identity.encode('utf-8')).hexdigest()


def snapshot_key(scope: str, server_number: int) -> str:
    if (len(scope) != 64 or any(c not in '0123456789abcdef' for c in scope)
            or type(server_number) is not int or not 1 <= server_number <= 32):
        raise ValueError('Invalid presence namespace or server number')
    return f'frontline:player-presence:v1:{scope}:{server_number}'


def redis_time(red) -> float:
    seconds, microseconds = red.time()
    return int(seconds) + int(microseconds) / 1_000_000


def capture_observation(red, api, *, scope: str, server_number: int) -> bool:
    """Publish one complete game-server roster, never a failed/partial result."""
    key = snapshot_key(scope, server_number)
    started = redis_time(red)
    with api.without_retries():
        pairs = api.get_player_ids()
    finished = redis_time(red)
    if (not isinstance(pairs, list)
            or any(not isinstance(pair, tuple) or len(pair) != 2 for pair in pairs)):
        raise ValueError('Invalid roster')
    payload = {'version': 1, 'server_number': server_number,
               'started_at': started, 'finished_at': finished,
               'players': [pair[1] for pair in pairs]}
    if validated_observation(payload, server_number=server_number, now=finished,
                             max_age=MAX_SNAPSHOT_AGE_SECONDS) is None:
        raise ValueError('Incomplete or delayed roster')
    encoded = json.dumps(payload, separators=(',', ':'), ensure_ascii=False)
    return bool(red.eval(_STORE_IF_NEWER, 1, key, started, encoded, SNAPSHOT_TTL_SECONDS))


def read_observations(red, *, scope: str, server_numbers: Iterable[int]):
    """Return fresh sightings and the servers that actually supplied a roster."""
    servers = tuple(server_numbers)
    if len(set(servers)) != len(servers):
        raise ValueError('Duplicate server number')
    keys = [snapshot_key(scope, server) for server in servers]
    now = redis_time(red)
    values = red.mget(keys) if keys else []
    observations, available = [], set()
    for server, raw in zip(servers, values):
        if raw is None:
            continue
        try:
            payload = json.loads(raw)
        except (TypeError, ValueError, UnicodeDecodeError):
            continue
        valid = validated_observation(payload, server_number=server, now=now,
                                      max_age=MAX_SNAPSHOT_AGE_SECONDS)
        if valid is not None:
            observations.append(valid)
            available.add(server)
    return merge_observations(observations), available


def read_other_servers(server_number: int):
    from rcon.cache_utils import get_redis_client

    scope = database_scope(os.environ['HLL_DB_URL'])
    red = get_redis_client(global_pool=True)
    if abs(redis_time(red) - time.time()) > 2:
        raise ValueError('Presence clock is not aligned with this server')
    return read_observations(red, scope=scope,
                             server_numbers=(n for n in range(1, 33) if n != server_number))


def run_loop(red, api, *, scope: str, server_number: int, stop_event) -> None:
    """Collect read-only observations; a failed poll never refreshes the TTL."""
    last_failure_type = None
    last_failure_log_at = None
    while not stop_event.is_set():
        try:
            capture_observation(red, api, scope=scope, server_number=server_number)
            if last_failure_type is not None:
                logger.info('Player presence observation recovered')
                last_failure_type, last_failure_log_at = None, None
        except Exception as exc:
            # Neither roster contents nor connection details belong in logs.
            failure_type = type(exc).__name__
            now = time.monotonic()
            if (failure_type != last_failure_type or last_failure_log_at is None
                    or now - last_failure_log_at >= FAILURE_LOG_INTERVAL_SECONDS):
                logger.warning('Player presence observation unavailable (%s)', failure_type)
                last_failure_log_at = now
            last_failure_type = failure_type
        if stop_event.wait(POLL_INTERVAL_SECONDS):
            return


def run(stop_event=None) -> None:
    from rcon.cache_utils import get_redis_client
    from rcon.rcon import get_rcon
    from rcon.utils import get_server_number

    stop_event = stop_event or threading.Event()
    while not stop_event.is_set():
        try:
            scope = database_scope(os.environ['HLL_DB_URL'])
            red = get_redis_client(global_pool=True)
            run_loop(red, get_rcon(), scope=scope, server_number=int(get_server_number()),
                     stop_event=stop_event)
            return
        except Exception as exc:
            # Unsupported or incomplete installations degrade to local history.
            # Do not restart the entire service repeatedly or expose credentials.
            logger.warning('Player presence initialization unavailable (%s)', type(exc).__name__)
            if stop_event.wait(FAILURE_LOG_INTERVAL_SECONDS):
                return
