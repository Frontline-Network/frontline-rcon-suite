"""Lossless handoff of legacy Redis webhook payloads to a durable outbox.

A staged payload stays at the list head until the caller has committed it to
SQL. Its stable random token is the SQL import idempotency key. The stage has
no expiry: a database outage must not remove the only retained copy of work.
All consumers of the old destructive queue protocol must be stopped before
enabling this importer.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
import hashlib
import uuid

import redis


# Keep this namespace outside whs:* so old queue discovery cannot consume it.
PREFIX = "wh_legacy_v1"


@dataclass(frozen=True, slots=True)
class Stage:
    token: str
    raw: bytes = field(repr=False)


_STAGE_NEXT = """
local queue_type = redis.call('TYPE', KEYS[1]).ok
local stage_type = redis.call('TYPE', KEYS[2]).ok
local registry_type = redis.call('TYPE', KEYS[3]).ok
if queue_type ~= 'none' and queue_type ~= 'list' then
    return redis.error_reply('legacy webhook queue has wrong type')
end
if stage_type ~= 'none' and stage_type ~= 'hash' then
    return redis.error_reply('legacy webhook stage has wrong type')
end
if registry_type ~= 'none' and registry_type ~= 'set' then
    return redis.error_reply('legacy webhook registry has wrong type')
end
if stage_type == 'hash' then
    local token = redis.call('HGET', KEYS[2], 'token')
    local raw = redis.call('HGET', KEYS[2], 'raw')
    if token == false or token == '' or raw == false then
        return redis.error_reply('legacy webhook stage is incomplete')
    end
    redis.call('SADD', KEYS[3], KEYS[1])
    return {token, raw}
end
local raw = redis.call('LINDEX', KEYS[1], 0)
if raw == false then
    redis.call('SREM', KEYS[3], KEYS[1])
    return false
end
redis.call('HSET', KEYS[2], 'token', ARGV[1], 'raw', raw)
redis.call('SADD', KEYS[3], KEYS[1])
return {ARGV[1], raw}
"""


_ACK_STAGE = """
local queue_type = redis.call('TYPE', KEYS[1]).ok
local stage_type = redis.call('TYPE', KEYS[2]).ok
local registry_type = redis.call('TYPE', KEYS[3]).ok
if queue_type ~= 'none' and queue_type ~= 'list' then
    return redis.error_reply('legacy webhook queue has wrong type')
end
if stage_type ~= 'none' and stage_type ~= 'hash' then
    return redis.error_reply('legacy webhook stage has wrong type')
end
if registry_type ~= 'none' and registry_type ~= 'set' then
    return redis.error_reply('legacy webhook registry has wrong type')
end
if stage_type == 'none' then
    return 0
end
local token = redis.call('HGET', KEYS[2], 'token')
local raw = redis.call('HGET', KEYS[2], 'raw')
if token == false or token == '' or raw == false then
    return redis.error_reply('legacy webhook stage is incomplete')
end
if token ~= ARGV[1] then
    return 0
end
local head = redis.call('LINDEX', KEYS[1], 0)
if head == false or head ~= raw then
    return 0
end
redis.call('LPOP', KEYS[1])
redis.call('DEL', KEYS[2])
redis.call('SREM', KEYS[3], KEYS[1])
return 1
"""


def _queue_id(queue_id: str | bytes) -> str:
    try:
        text = queue_id.decode("utf-8") if isinstance(queue_id, bytes) else queue_id
        if not isinstance(text, str) or not text or len(text.encode("utf-8")) > 4096:
            raise ValueError
    except (UnicodeError, ValueError):
        raise ValueError("Invalid legacy webhook queue identifier") from None
    return text


def registry_key() -> str:
    return f"{PREFIX}:queues"


def stage_key(queue_id: str | bytes) -> str:
    queue_id = _queue_id(queue_id)
    digest = hashlib.sha256(queue_id.encode("utf-8")).hexdigest()
    return f"{PREFIX}:stage:{digest}"


def stage_next(red: redis.Redis, queue_id: str | bytes) -> Stage | None:
    """Read or create a stable stage without removing the legacy list head."""
    queue_id = _queue_id(queue_id)
    reply = red.register_script(_STAGE_NEXT)(
        keys=[queue_id, stage_key(queue_id), registry_key()],
        args=[uuid.uuid4().hex],
    )
    if reply is None:
        return None
    if not isinstance(reply, (list, tuple)) or len(reply) != 2:
        raise ValueError("Invalid legacy webhook stage response")
    token, raw = reply
    if isinstance(token, bytes):
        try:
            token = token.decode("ascii")
        except UnicodeError:
            raise ValueError("Invalid legacy webhook stage response") from None
    if isinstance(raw, str):
        raw = raw.encode("utf-8")
    if not isinstance(token, str) or not token or not isinstance(raw, bytes):
        raise ValueError("Invalid legacy webhook stage response")
    return Stage(token=token, raw=raw)


def ack_stage(red: redis.Redis, queue_id: str | bytes, token: str) -> bool:
    """Retire a SQL-committed stage only while its original head still matches.

    A stale token or externally changed list returns False and retains the
    stage. It must never remove a different message to force forward progress.
    """
    queue_id = _queue_id(queue_id)
    if not isinstance(token, str) or not token:
        return False
    return bool(red.register_script(_ACK_STAGE)(
        keys=[queue_id, stage_key(queue_id), registry_key()], args=[token]
    ))


def staged_queues(red: redis.Redis, limit: int = 100) -> list[str]:
    """Discover unfinished handoffs incrementally with a bounded result list."""
    if not isinstance(limit, int) or not 0 <= limit <= 1000:
        raise ValueError("Legacy webhook discovery limit must be between 0 and 1000")
    if limit == 0:
        return []
    found: set[str] = set()
    for queue in red.sscan_iter(registry_key(), count=min(limit, 100)):
        found.add(_queue_id(queue))
        if len(found) >= limit:
            break
    return sorted(found)


def import_queue(
    red: redis.Redis,
    queue_id: str | bytes,
    persist: Callable[[Stage], object],
    limit: int = 20,
) -> int:
    """Commit up to ``limit`` staged payloads before acknowledging Redis.

    ``persist`` must return only after SQL has committed, including an
    idempotent replay of ``legacy:<stage.token>``. It must raise on failure.
    """
    if not isinstance(limit, int) or not 0 <= limit <= 1000:
        raise ValueError("Legacy webhook import limit must be between 0 and 1000")
    queue_id = _queue_id(queue_id)
    transferred = 0
    for _ in range(limit):
        stage = stage_next(red, queue_id)
        if stage is None:
            break
        persist(stage)
        if not ack_stage(red, queue_id, stage.token):
            break
        transferred += 1
    return transferred
