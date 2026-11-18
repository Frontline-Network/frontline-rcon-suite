"""Short-lived aggregate journal observations, not a game-log completeness proof.

Experimental evidence used only by the opt-in Barricade path.
"""
import json
import math
from dataclasses import dataclass

from rcon.player_presence import redis_time, snapshot_key

TTL_SECONDS = 45
MAX_AGE_SECONDS = 30
MAX_READ_SECONDS = 10
_STORE_NEWER = """
local previous = redis.call('GET', KEYS[1])
if previous then
  local ok, value = pcall(cjson.decode, previous)
  if ok and type(value) == 'table' and type(value.poll_started_at) == 'number'
      and value.poll_started_at >= tonumber(ARGV[1]) then return 0 end
end
redis.call('SET', KEYS[1], ARGV[2], 'EX', ARGV[3])
return 1
"""
_INVALIDATE = """
local clock = redis.call('TIME')
local stamp = tonumber(clock[1]) + tonumber(clock[2]) / 1000000
local previous = redis.call('GET', KEYS[1])
if previous then
  local ok, value = pcall(cjson.decode, previous)
  if ok and type(value) == 'table' and type(value.poll_started_at) == 'number'
      and value.poll_started_at > stamp then stamp = value.poll_started_at end
end
local tombstone = '{"version":0,"poll_started_at":' .. string.format('%.6f', stamp) .. '}'
redis.call('SET', KEYS[1], tombstone, 'EX', ARGV[1])
return 1
"""


@dataclass(frozen=True)
class JournalObservation:
    poll_started_at: float
    poll_finished_at: float
    started_at: float
    finished_at: float
    pending: int
    unpublished_anonymous: int


def observation_key(scope: str, server_number: int) -> str:
    # Reuse the namespace validation used by presence snapshots.
    snapshot_key(scope, server_number)
    return f'frontline:session-journal-observation:v1:{scope}:{server_number}'


def invalidate(red, *, scope: str, server_number: int) -> None:
    """Invalidate prior evidence and fence out older in-flight polls."""
    red.eval(_INVALIDATE, 1, observation_key(scope, server_number), TTL_SECONDS)


def validate(payload, *, server_number: int, now: float) -> JournalObservation | None:
    if (not isinstance(payload, dict) or type(payload.get('version')) is not int or payload['version'] != 1 or
            type(server_number) is not int or not 1 <= server_number <= 32 or
            type(payload.get('server_number')) is not int or payload['server_number'] != server_number or
            type(now) not in (int, float) or not math.isfinite(now)):
        return None
    poll_start, poll_end = payload.get('poll_started_at'), payload.get('poll_finished_at')
    start, end = payload.get('started_at'), payload.get('finished_at')
    pending, anonymous = payload.get('pending'), payload.get('unpublished_anonymous')
    if (any(type(value) not in (int, float) or not math.isfinite(value)
            for value in (poll_start, poll_end, start, end)) or
            not 0 < poll_start <= poll_end <= start <= end <= now or
            end - start > MAX_READ_SECONDS or now - poll_start > MAX_AGE_SECONDS or
            type(pending) is not int or pending < 0 or type(anonymous) is not int or anonymous < 0):
        return None
    return JournalObservation(poll_start, poll_end, start, end, pending, anonymous)


def publish(red, journal, *, scope: str, server_number: int, poll_started_at: float, poll_finished_at: float) -> bool:
    key = observation_key(scope, server_number)
    start = redis_time(red)
    pending, anonymous = journal.pending_counts(server_number)
    end = redis_time(red)
    payload = {'version': 1, 'server_number': server_number, 'started_at': start, 'finished_at': end,
               'poll_started_at': poll_started_at, 'poll_finished_at': poll_finished_at,
               'pending': pending, 'unpublished_anonymous': anonymous}
    if validate(payload, server_number=server_number, now=end) is None:
        raise ValueError('Invalid local journal observation')
    return bool(red.eval(_STORE_NEWER, 1, key, poll_started_at, json.dumps(payload, separators=(',', ':')), TTL_SECONDS))


def read(red, *, scope: str, server_number: int) -> JournalObservation | None:
    key = observation_key(scope, server_number)
    now = redis_time(red)
    raw = red.get(key)
    try:
        payload = json.loads(raw) if raw is not None else None
    except (ValueError, TypeError, UnicodeDecodeError):
        return None
    return validate(payload, server_number=server_number, now=now)
