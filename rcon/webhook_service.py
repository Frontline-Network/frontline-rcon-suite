import asyncio
import hashlib
import math
import os
import random
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from enum import StrEnum
from logging import getLogger
from typing import TypedDict

import httpx
import orjson
import pydantic
import redis
import redis.exceptions
from discord_webhook import AsyncDiscordWebhook, DiscordWebhookDict
from pydantic import BaseModel, Field

from rcon.cache_utils import construct_redis_url, get_redis_client
from rcon import webhook_legacy, webhook_outbox
from rcon.utils import get_server_number

logger = getLogger(__name__)

# TODO: Support editing existing messages; this can only add
# new ones, so we can't use it for scorebot yet

TRANSIENT_IDENTIFIER = "transient_identifier"
TRANSIENT_IDENTIFIER_BYTES = b"transient_identifier"

PREFIX = "whs"
OUTBOX_WAKEUPS_KEY = "whs_outbox:wakeups"
OUTBOX_POLL_SECONDS = 1.0
DELIVERY_TIMEOUT_SECONDS = 20.0
DELIVERY_LEASE_SECONDS = 120
MAX_DELIVERY_TASKS = 8
LEGACY_IMPORT_BATCH = 20
_next_wakeup_warning_at = 0.0
_next_wakeup_attempt_at = 0.0
_wakeup_lock = threading.Lock()
BUCKET_ID = f"{PREFIX}"
WH_ID_TO_RATE_LIMIT_BUCKET = f"{PREFIX}:wh_id_rl_bucket"
BUCKET_RL = f"{PREFIX}:rl"
BUCKET_RL_COUNT = f"{BUCKET_RL}:count"
RATE_LIMIT_LOCK_WAIT_MS = f"{PREFIX}:metrics:rate_limit_lock_wait_ms"
RATE_LIMIT_LOCK_WAIT_COUNT = f"{PREFIX}:metrics:rate_limit_lock_wait_count"
RATE_LIMIT_LOCK_METRICS_TTL_SECS = 60 * 60

GLOBAL_RATE_LIMIT = f"{PREFIX}:global_rl"
GLOBAL_RATE_LIMIT_RESET_AFTER = f"{GLOBAL_RATE_LIMIT}:reset_after"
# Track HTTP 401/403 errors by webhook ID
WEBHOOK_ERRORS = f"{PREFIX}:errors"

# Track failed message (HTTP 404 errors) by message ID
MESSAGE_DOES_NOT_EXIST = f"{PREFIX}:message_404"

DEFAULT_GLOBAL_RETRY_AFTER_SECS = 5 * 60

# Discord response headers
X_RATELIMIT_BUCKET = "x-ratelimit-bucket"
X_RATELIMIT_REMAINING = "x-ratelimit-remaining"
X_RATELIMIT_LIMIT = "x-ratelimit-limit"
X_RATELIMIT_RESET = "x-ratelimit-reset"
X_RATELIMIT_RESET_AFTER = "x-ratelimit-reset-after"


# Allow users to tune their local rate limit window if they really want to
try:
    LOCAL_RL_RESET_AFTER = int(os.getenv("HLL_WH_SERVICE_RL_RESET_SECS"))
except (ValueError, TypeError):
    LOCAL_RL_RESET_AFTER = 3

try:
    LOCAL_RL_REQUESTS_PER = int(os.getenv("HLL_WH_SERVICE_RL_REQUESTS_PER", 5))
except (ValueError, TypeError):
    LOCAL_RL_REQUESTS_PER = 5

# Tracks the number of rate limited requests in the last N seconds
try:
    BUCKET_RL_COUNT_RESET_SECS = int(os.getenv("HLL_WH_SERVICE_RL_RESET_SECS"))
except (ValueError, TypeError):
    BUCKET_RL_COUNT_RESET_SECS = 60 * 10


# This bounds Redis UUID wakeup hints, not accepted message payloads. SQL owns
# the complete backlog while a consumer or Redis is unavailable.
try:
    WH_MAX_QUEUE_LENGTH = int(os.getenv("HLL_WH_MAX_QUEUE_LENGTH"))
except (ValueError, TypeError):
    WH_MAX_QUEUE_LENGTH = 150

try:
    HLL_WH_LOOP_SLEEP_TIME = float(os.getenv("HLL_WH_LOOP_SLEEP_TIME"))
except (ValueError, TypeError):
    HLL_WH_LOOP_SLEEP_TIME = 0.006

try:
    HLL_WH_IDLE_SLEEP_TIME = float(os.getenv("HLL_WH_IDLE_SLEEP_TIME"))
except (ValueError, TypeError):
    HLL_WH_IDLE_SLEEP_TIME = 0.1

# Queue contents still get checked every service loop. Redis key discovery is
# intentionally slower because newly created webhook queues can tolerate this
# small delay and SCAN is otherwise executed hundreds of times per second.
QUEUE_KEY_REFRESH_INTERVAL_SECS = 1.0
QUEUE_REGISTRY_SUFFIX = "queue_registry"
QUEUE_REGISTRY_SENTINEL = "__initialized__"
EMPTY_DEQUEUE_COUNT = f"{PREFIX}:metrics:empty_dequeues"
DEAD_LETTER_QUEUE = f"{PREFIX}:dead_letter"

# Retained SQL review entries do not expire. The legacy archive constants only
# describe old Redis data during upgrade; accepted new payloads are never trimmed.
try:
    WH_MAX_RETRY_ATTEMPTS = int(os.getenv("HLL_WH_MAX_RETRY_ATTEMPTS", 5))
except (ValueError, TypeError):
    WH_MAX_RETRY_ATTEMPTS = 5

try:
    WH_MAX_MESSAGE_AGE_SECS = int(os.getenv("HLL_WH_MAX_MESSAGE_AGE_SECS", 60 * 60))
except (ValueError, TypeError):
    WH_MAX_MESSAGE_AGE_SECS = 60 * 60

try:
    WH_DEAD_LETTER_TTL_SECS = int(os.getenv("HLL_WH_DEAD_LETTER_TTL_SECS", 30 * 24 * 60 * 60))
except (ValueError, TypeError):
    WH_DEAD_LETTER_TTL_SECS = 30 * 24 * 60 * 60

try:
    WH_DEAD_LETTER_MAX_LENGTH = int(os.getenv("HLL_WH_DEAD_LETTER_MAX_LENGTH", 500))
except (ValueError, TypeError):
    WH_DEAD_LETTER_MAX_LENGTH = 500

# Global data structures to support associating hooks with locks.  Discord can
# report the same bucket for different webhook URLs after either URL has
# already been used, so this registry must be canonical by bucket ID.
_RATE_LIMIT_BUCKETS: dict[str, asyncio.Lock] = {}
_SHARED_LOCK: asyncio.Lock | None = None


def set_message_edit_404_failure(
    red: redis.StrictRedis,
    message_id: str,
    prefix: str = MESSAGE_DOES_NOT_EXIST,
    value: bool = True,
    ttl=120,
) -> None:
    """Set a flag in redis for a message ID to communicate back to a sender that the message does not exist"""
    red.set(f"{prefix}:{message_id}", b"1" if value else b"0", ex=ttl)


def get_message_edit_404_failure(
    message_id: str,
    red: redis.StrictRedis | None = None,
    prefix: str = MESSAGE_DOES_NOT_EXIST,
) -> bool:
    """Check if a specific message ID received an HTTP 404 error from Discord"""
    # Allows easier usage for enqueing from different services/sections of CRCON
    if red is None:
        url = construct_redis_url(db_number=0)
        red = get_redis_client(redis_url=url, decode_responses=False, global_pool=True)
    return red.get(f"{prefix}:{message_id}") == b"1"




def handle_webhook_not_found(
    red: redis.StrictRedis,
    queue_id: str,
    payload: DiscordWebhookDict,
    webhook_type: "WebhookType",
    webhook_id: str,
) -> None:
    """Record a Discord 404; accepted payloads remain in the SQL review archive."""
    message_id = payload.get("message_id")
    if message_id:
        set_message_edit_404_failure(red=red, message_id=message_id)

    set_webhook_error(
        red=red,
        webhook_id=webhook_id,
        webhook_type=webhook_type,
        _404=True,
    )


def get_shared_lock() -> asyncio.Lock:
    """Singleton instance for our shared lock that is used before a rate limit bucket is determined"""
    global _SHARED_LOCK
    if _SHARED_LOCK is None:
        _SHARED_LOCK = asyncio.Lock()
        logger.debug("Creating shared lock %s", _SHARED_LOCK)

    return _SHARED_LOCK


class WebhookType(StrEnum):
    """The type of service the webhook is for (discord, etc.)"""

    DISCORD = "discord"


class DiscordErrorResponse(TypedDict):
    """Discord will return 401 for invalid webhook IDs; 403 for invalid tokens"""

    http_401: bool
    http_403: bool
    http_404: bool


class WebhookMessageType(StrEnum):
    """The underlying type a webhook message is for (log, audit, scoreboard, etc.)

    This allows us to selectively remove messages from a queue
    """

    # TODO: Add the other log types in a more general fashion
    LOG_LINE = "log_line"
    LOG_LINE_CHAT = "log_line_chat"
    LOG_LINE_KILL = "log_line_kill"
    LOG_LINE_TEAMKILL = "log_line_teamkill"
    ADMIN_PING = "admin_ping"
    SCOREBOARD = "scoreboard"
    AUDIT = "audit"
    OTHER = "other"


@dataclass
class QueueParts:
    """The individual components of a queue ID key"""

    prefix: str
    server_number: str
    wh_type: WebhookType
    msg_type: WebhookMessageType
    id: str


@dataclass
class TransientMessageParts:
    """The individual components of a transient message key"""

    prefix: str
    server_number: str
    wh_type: WebhookType
    msg_type: WebhookMessageType
    id: str
    message_group_key: str


class QueueStatus(TypedDict):
    """Overview of a message queue"""

    server_number: int
    id: str
    webhook_type: WebhookType
    message_type: WebhookMessageType
    length: int
    rate_limit_bucket: str | None
    rate_limited: bool
    redis_key: str


class TransientMessageStatus(TypedDict):
    """Overview of a transient message"""

    server_number: int
    id: str
    webhook_type: WebhookType
    message_type: WebhookMessageType
    rate_limit_bucket: str | None
    rate_limited: bool
    message_key: str
    redis_key: str


class DeadLetterStatus(TypedDict):
    """Redacted operator-facing state for a failed webhook delivery.

    The actual message remains in SQL so it can be retried, but its payload
    may contain a Discord webhook token and must never be returned by the API.
    """

    id: str
    server_number: int
    webhook_type: WebhookType
    message_type: WebhookMessageType
    retry_attempts: int
    reason: str
    failed_at: datetime


class WebhookMessage(BaseModel):
    """Accepted webhook payload stored durably before a delivery is scheduled."""

    server_number: int = Field(description="The server that generated this message")
    discardable: bool = Field(
        default=False,
        description="Use for messages that don't need to be retried (scorebot, etc)",
    )
    edit: bool = Field(
        default=False,
        description="Edit an existing message; the ID field must already be set in the payload",
    )

    sent_at: datetime = Field(
        default_factory=lambda: datetime.now(tz=timezone.utc),
        description="The original UTC time the message was attempted to be sent",
    )
    retry_attempts: int = Field(
        default=0,
        ge=0,
        description="The number of retry attempts if the message was rate limited",
    )
    payload_type: None = Field(
        default=None,
        description="For future use for bundling similar types of messages",
    )

    # TODO: support other types of webhooks in the future
    webhook_type: WebhookType = Field(description="The type of webhook (discord, etc.)")
    message_type: WebhookMessageType = Field()

    payload: DiscordWebhookDict = Field(
        description="The parameters that will be used to construct the webhook of appropriate type by the service"
    )


class DeadLetterWebhookMessage(BaseModel):
    """A retryable failed message kept outside the live delivery queues."""

    id: str = Field(default_factory=lambda: uuid.uuid4().hex)
    message: WebhookMessage
    source_queue_id: str
    reason: str
    failed_at: datetime = Field(default_factory=lambda: datetime.now(tz=timezone.utc))


class DiscordRateLimitData(BaseModel):
    """Discord rate limit header data"""

    webhook_type: WebhookType | None = Field(default=None)
    id: str | None = Field(default=None)
    remaining_requests: int | None = Field(default=None)
    reset_after_secs: int | None = Field(default=None)
    reset_timestamp: int | None = Field(default=None)
    rate_limited: bool = Field(default=False)


def update_bucket_rate_limit(
    red: redis.StrictRedis,
    bucket_id: str,
    webhook_type: WebhookType,
    prefix: str = BUCKET_RL_COUNT,
    reset_seconds: int = BUCKET_RL_COUNT_RESET_SECS,
):
    """If a bucket is rate limited; set a key in a Redis hash that will expire

    This allows us to easily track the number of rate limits in the last N seconds
    by simply counting the number of entries in the hash
    """
    hash_name = f"{prefix}:{webhook_type}:{bucket_id}"
    # We can set this to whatever; we're just counting the number of hash entries
    # but using the timestamp should make it unique
    key = str(datetime.now().timestamp())
    value = "1"
    red.hset(hash_name, key, value)
    red.hexpire(hash_name, reset_seconds, key)


def count_bucket_rate_limits(
    red: redis.StrictRedis, bucket_id: str, prefix: str = BUCKET_RL_COUNT
) -> int:
    """The rate limit bucket hash length; the number of times it was rate limited in the window"""
    hash_name = f"{prefix}:{bucket_id}"
    return red.hlen(hash_name)  # type: ignore


def is_bucket_local_rate_limited(
    red: redis.StrictRedis,
    bucket_id: str,
    webhook_type: WebhookType | None,
    seconds: int = LOCAL_RL_RESET_AFTER,
    requests_per: int = LOCAL_RL_REQUESTS_PER,
    prefix: str = BUCKET_RL,
) -> bool:
    """Track our local rate limit (fixed window) per bucket to reduce external rate limiting

    This uses a fixed window rate limit algorithm
    """
    key = f"{prefix}:{webhook_type}:{bucket_id}"
    limited: bool = True
    try:
        res: bytes = red.get(key)  # type: ignore
        value = int(res.decode())
    except (TypeError, AttributeError):
        value = 0

    if value < requests_per:
        pipe = red.pipeline()
        limited = False
        pipe.incr(key)
        pipe.expire(key, seconds)
        pipe.execute()

    return limited


def is_globally_rate_limited(red: redis.StrictRedis) -> bool:
    """Check Redis to determine if we are globally rate limited"""
    limit = get_global_rate_limit_reset_after(red=red)

    return limit is not None


def get_global_rate_limit_reset_after(red: redis.StrictRedis) -> datetime | None:
    """Return the datetime the global rate limit expires at if any"""
    limit: datetime | None = None

    try:
        raw: bytes = red.get(GLOBAL_RATE_LIMIT_RESET_AFTER)  # type: ignore
        limit = datetime.fromtimestamp(float(raw.decode()))
    except (AttributeError, TypeError) as e:
        logger.debug("Unable to parse the global rate limit reset after time: %s", e)

    return limit


def set_global_rate_limit_reset_after(red: redis.StrictRedis, limit: float) -> None:
    """Set the timestamp the global rate limit expires in Redis"""
    seconds = limit - datetime.now().timestamp()
    if seconds > 0:
        pipe = red.pipeline()
        pipe.set(GLOBAL_RATE_LIMIT_RESET_AFTER, limit)
        pipe.expire(GLOBAL_RATE_LIMIT_RESET_AFTER, time=int(seconds))
        pipe.execute()


def get_webhook_rate_limit_bucket(
    red: redis.StrictRedis,
    queue_id: str,
    hash_name: str = WH_ID_TO_RATE_LIMIT_BUCKET,
) -> str | None:
    """Get the Discord rate limit bucket a webhook is associated with"""
    # There is a very low but non 0 chance of colliding on queue IDs
    # between services once we expand to support other webhook types than Discord
    # but for now to simplify the service without having to pass in details
    # of the message that we don't know when we GET it, skip the webhook type
    res: bytes = red.hget(hash_name, f"{queue_id}")  # type: ignore
    return res.decode() if res else None


def set_webhook_rate_limit_bucket(
    red: redis.StrictRedis,
    bucket_id: str,
    queue_id: str,
    hash_name: str = WH_ID_TO_RATE_LIMIT_BUCKET,
) -> None:
    """Associate a queue ID with its rate limit bucket"""
    logger.debug("Setting %s to %s", queue_id, bucket_id)
    red.hset(hash_name, queue_id, bucket_id)


def get_rate_limit_bucket_data(
    red: redis.StrictRedis, bucket_id: str, prefix: str = BUCKET_ID
) -> DiscordRateLimitData:
    """Return the data for a specific rate limit bucket"""
    name = f"{prefix}:{bucket_id}"
    raw_value = red.get(name)
    if raw_value is None:
        return DiscordRateLimitData()
    else:
        return DiscordRateLimitData.model_validate_json(orjson.loads(raw_value))  # type: ignore


def set_rate_limit_bucket_data(
    red: redis.StrictRedis, bucket: DiscordRateLimitData, prefix: str = BUCKET_ID
) -> None:
    """Set the data for a specific rate limit bucket"""
    # There is a very low but non 0 chance of colliding on rate limit bucket IDs
    # between services once we expand to support other webhook types than Discord
    # but for now to simplify the service without having to pass in details
    # of the message that we don't know when we GET it, skip the webhook type
    name = f"{prefix}:{bucket.id}"
    red.set(name, orjson.dumps(bucket.model_dump_json()))


def get_or_create_bucket_lock(bucket_id: str) -> asyncio.Lock:
    """Return the canonical in-process lock for a Discord rate-limit bucket.

    This function has no await point, so the lookup-and-create sequence is
    atomic within a webhook-service worker process.
    """
    global _RATE_LIMIT_BUCKETS
    lock = _RATE_LIMIT_BUCKETS.get(bucket_id)
    if lock is None:
        lock = asyncio.Lock()
        _RATE_LIMIT_BUCKETS[bucket_id] = lock
    return lock


def get_bucket_lock(
    red: redis.StrictRedis,
    bucket_id: str,
) -> tuple[DiscordRateLimitData, asyncio.Lock]:
    """Get rate-limit data and the canonical lock for a known bucket."""
    bucket_data = get_rate_limit_bucket_data(red=red, bucket_id=bucket_id)
    return bucket_data, get_or_create_bucket_lock(bucket_id=bucket_id)


def set_bucket_data(
    red: redis.StrictRedis, bucket: DiscordRateLimitData, lock: asyncio.Lock
) -> None:
    """Persist bucket data without replacing its canonical lock."""
    logger.debug("Updating bucket data: %s", bucket)

    if bucket.id:
        canonical_lock = get_or_create_bucket_lock(bucket_id=bucket.id)
        if canonical_lock is not lock:
            logger.debug("Retaining canonical rate-limit lock for bucket %s", bucket.id)
        set_rate_limit_bucket_data(red=red, bucket=bucket)
    else:
        logger.error("Received a None bucket ID: %s", bucket)


def record_bucket_lock_wait(
    red: redis.StrictRedis,
    bucket_id: str,
    wait_seconds: float,
    prefix: str = RATE_LIMIT_LOCK_WAIT_MS,
) -> None:
    """Record contended Discord bucket-lock waits as bounded Redis metrics."""
    if wait_seconds <= 0:
        return

    wait_ms = max(1, math.ceil(wait_seconds * 1000))
    pipe = red.pipeline()
    pipe.hincrby(prefix, bucket_id, wait_ms)
    pipe.hincrby(RATE_LIMIT_LOCK_WAIT_COUNT, bucket_id, 1)
    pipe.expire(prefix, RATE_LIMIT_LOCK_METRICS_TTL_SECS)
    pipe.expire(RATE_LIMIT_LOCK_WAIT_COUNT, RATE_LIMIT_LOCK_METRICS_TTL_SECS)
    pipe.execute()


def set_webhook_error(
    red: redis.StrictRedis,
    webhook_id: str,
    webhook_type: WebhookType,
    auth_401: bool = False,
    auth_403: bool = False,
    _404: bool = False,
    prefix: str = WEBHOOK_ERRORS,
):
    """Store the last error received for a webhook; cleared after a successful request"""
    key = f"{prefix}:{webhook_type}:{webhook_id}"
    # can't send a bool to redis
    payload: DiscordErrorResponse = {
        "http_401": int(auth_401),  # type: ignore
        "http_403": int(auth_403),  # type: ignore
        "http_404": int(_404),  # type: ignore
    }
    red.hset(key, mapping=payload)  # type: ignore


def get_webhook_error(
    red: redis.StrictRedis,
    webhook_id: str,
    webhook_type: WebhookType,
    prefix: str = WEBHOOK_ERRORS,
) -> DiscordErrorResponse:
    """Retrieve the current webhook error response for a webhook"""
    # TODO: likely have to tweak this when we support other webhook types in the future
    key = f"{prefix}:{webhook_type}:{webhook_id}"
    raw: dict[bytes, int] = red.hgetall(key)  # type: ignore
    values: DiscordErrorResponse = {
        "http_401": True if raw.get(b"http_401") == b"1" else False,
        "http_403": True if raw.get(b"http_403") == b"1" else False,
        "http_404": True if raw.get(b"http_404") == b"1" else False,
    }
    return values


def clear_webhook_errors(
    red: redis.StrictRedis, webhook_id: str, webhook_type: WebhookType
):
    """Reset the errors (HTTP 401/403) for a webhook ID"""
    # TODO: likely have to tweak this when we support other webhook types in the future
    set_webhook_error(
        red=red,
        webhook_id=webhook_id,
        webhook_type=webhook_type,
        auth_401=False,
        auth_403=False,
    )


def enqueue_transient_message(
    message: WebhookMessage,
    message_group_key: str,
    red: redis.StrictRedis | None = None,
    prefix: str = PREFIX,
    transient_identifier: str = TRANSIENT_IDENTIFIER,
    ttl: int = 120,
):
    """Accept a WebhookMessage and message_group_key to only store the most recent update

    This method should only be used for types of messages that are transient
    and impermanent; such as a Scoreboard message update. These messages are
    not stored as a queue; enqueueing future messages will overwrite any past ones
    use `enqueue_message` for messages that should be stored in a queue so they are
    # all (attempted but not guaranteed) to be sent to the remote service (Discord, etc.)
    """
    if not isinstance(message, WebhookMessage):
        raise ValueError("Expected a WebhookMessage")
    key = f"{prefix}:{get_server_number()}:{transient_identifier}:{message.webhook_type}:{message.message_type}:{message.payload['webhook_id']}:{message_group_key}"
    delivery_id = webhook_outbox.enqueue(
        key, message.model_dump_json().encode(), message.server_number,
        coalesce=True, message_type=str(message.message_type),
        webhook_type=str(message.webhook_type), created_at=message.sent_at,
        initial_attempts=message.retry_attempts,
    )
    _wake_outbox(delivery_id, red)
    return delivery_id


def enqueue_message(
    message: WebhookMessage, red: redis.StrictRedis | None = None, prefix: str = PREFIX
):
    """Commit a WebhookMessage to SQL, then send an optional bounded Redis hint.

    Queues are independently tracked by the webhook ID (Discord snowflake)
    """
    if not isinstance(message, WebhookMessage):
        raise ValueError("Expected a WebhookMessage")
    queue_id = f"{prefix}:{get_server_number()}:{message.webhook_type}:{message.message_type}:{message.payload['webhook_id']}"
    delivery_id = webhook_outbox.enqueue(
        queue_id, message.model_dump_json().encode(), message.server_number,
        message_type=str(message.message_type), webhook_type=str(message.webhook_type),
        created_at=message.sent_at, initial_attempts=message.retry_attempts,
    )
    _wake_outbox(delivery_id, red)
    return delivery_id


def _wake_outbox(delivery_id: str, red=None) -> None:
    """Wakeups are bounded hints; the committed SQL row is authoritative."""
    global _next_wakeup_warning_at, _next_wakeup_attempt_at
    if time.monotonic() < _next_wakeup_attempt_at or not _wakeup_lock.acquire(blocking=False):
        return
    try:
        if red is None:
            red = get_redis_client(redis_url=construct_redis_url(0), decode_responses=False, global_pool=True)
        pipe = red.pipeline()
        pipe.rpush(OUTBOX_WAKEUPS_KEY, delivery_id)
        pipe.ltrim(OUTBOX_WAKEUPS_KEY, -max(1, WH_MAX_QUEUE_LENGTH), -1)
        pipe.expire(OUTBOX_WAKEUPS_KEY, 300)
        pipe.execute()
        _next_wakeup_attempt_at = 0.0
    except (redis.exceptions.RedisError, OSError, ValueError):
        _next_wakeup_attempt_at = time.monotonic() + 1.0
        if time.monotonic() >= _next_wakeup_warning_at:
            _next_wakeup_warning_at = time.monotonic() + 30
            logger.warning("Redis wakeup unavailable; webhook remains in the durable outbox")
    finally:
        _wakeup_lock.release()


def construct_webhook(
    payload: DiscordWebhookDict, webhook_type: WebhookType
) -> AsyncDiscordWebhook:
    if webhook_type == WebhookType.DISCORD:
        unpacked: DiscordWebhookDict = payload  # type: ignore
        wh = AsyncDiscordWebhook(**unpacked)
    else:
        raise TypeError(f"{webhook_type} is an unsupported webhook type")

    return wh


def unpack_message(raw_message: bytes) -> WebhookMessage:
    value = orjson.loads(raw_message)
    return (WebhookMessage.model_validate_json(value) if isinstance(value, str)
            else WebhookMessage.model_validate(value))


def _message_age_seconds(message: WebhookMessage) -> float:
    sent_at = message.sent_at
    if sent_at.tzinfo is None:
        sent_at = sent_at.replace(tzinfo=timezone.utc)
    return max(0.0, (datetime.now(tz=timezone.utc) - sent_at).total_seconds())


def _dead_letter_status(entry: DeadLetterWebhookMessage) -> DeadLetterStatus:
    """Return metadata that is safe to show to a CRCON administrator."""
    return {
        "id": entry.id,
        "server_number": entry.message.server_number,
        "webhook_type": entry.message.webhook_type,
        "message_type": entry.message.message_type,
        "retry_attempts": entry.message.retry_attempts,
        "reason": entry.reason,
        "failed_at": entry.failed_at,
    }


def move_to_dead_letter(message, queue_id, reason, red=None) -> DeadLetterStatus:
    """Retain failures durably; archive capacity never discards accepted messages."""
    entry = DeadLetterWebhookMessage(message=message, source_queue_id=queue_id, reason=reason)
    webhook_outbox.enqueue(
        queue_id, message.model_dump_json().encode(), message.server_number,
        public_id=entry.id, initial_status="review", reason=reason,
        created_at=entry.failed_at, message_type=str(message.message_type),
        webhook_type=str(message.webhook_type), initial_attempts=message.retry_attempts,
    )
    logger.warning("Webhook delivery retained for operator review")
    return _dead_letter_status(entry)


def get_dead_letter_messages(red=None, limit=100) -> list[DeadLetterStatus]:
    if red is None:
        red = get_redis_client(decode_responses=False, global_pool=True)
    try:
        _import_legacy_dead_letters(red, limit=min(500, max(1, limit)))
    except redis.exceptions.RedisError:
        logger.warning("Legacy webhook archive unavailable; showing durable review records")
    return webhook_outbox.list_review(limit=max(1, min(limit, 1000)))


def retry_dead_letter_message(dead_letter_id: str, red=None) -> bool:
    """An operator retry atomically requeues the same retained SQL message."""
    if red is None:
        red = get_redis_client(decode_responses=False, global_pool=True)
    if webhook_outbox.lookup(dead_letter_id) is None:
        try:
            _import_legacy_dead_letters(red, limit=500)
        except redis.exceptions.RedisError:
            logger.warning("Legacy webhook archive unavailable")
    accepted = webhook_outbox.retry_review(dead_letter_id)
    if accepted:
        _wake_outbox(dead_letter_id, red)
    return accepted


def record_empty_dequeue(red: redis.StrictRedis, queue_id: str) -> None:
    """Record a harmless dequeue race without trying to parse ``None`` as JSON."""

    red.incr(EMPTY_DEQUEUE_COUNT)
    logger.debug("Skipping empty webhook dequeue from %s", queue_id)


def get_empty_dequeue_count(red: redis.StrictRedis) -> int:
    """Return the installation-wide count of dequeue races skipped safely."""

    raw_count = red.get(EMPTY_DEQUEUE_COUNT)
    try:
        return int(raw_count or 0)
    except (TypeError, ValueError):
        logger.warning("Invalid empty-dequeue metric value: %r", raw_count)
        return 0


def _persist_legacy_payload(queue_id: str, raw: bytes, occurrence: str, *, transient=False):
    """Keep exact bytes for idempotent import, including malformed payloads."""
    try:
        message = unpack_message(raw)
    except (ValueError, TypeError, pydantic.ValidationError):
        return webhook_outbox.enqueue(
            queue_id, raw, dedupe_key=occurrence, legacy=True,
            initial_status="review", reason="invalid_legacy_payload",
        )
    return webhook_outbox.enqueue(
        queue_id, raw, message.server_number, dedupe_key=occurrence, legacy=True,
        coalesce=transient, message_type=str(message.message_type),
        webhook_type=str(message.webhook_type), created_at=message.sent_at,
        initial_attempts=message.retry_attempts,
    )


def _clear_legacy_reset_if_empty(red, queue_id):
    generation = webhook_outbox.get_legacy_review_generation(queue_id)
    if (generation is not None and not red.exists(queue_id)
            and not red.exists(webhook_legacy.stage_key(queue_id))):
        webhook_outbox.clear_legacy_review(queue_id, expected_generation=generation)


def _import_legacy_queue(red, queue_id: str, *, limit=LEGACY_IMPORT_BATCH) -> int:
    """The old Redis payload stays in place until SQL has committed."""
    if TRANSIENT_IDENTIFIER in queue_id and red.type(queue_id) in (b"string", "string"):
        raw = red.get(queue_id)
        if raw is None:
            return 0
        if isinstance(raw, str):
            raw = raw.encode("utf-8")
        occurrence = "transient:" + hashlib.sha256(queue_id.encode() + b"\0" + raw).hexdigest()
        delivery_id = _persist_legacy_payload(queue_id, raw, occurrence, transient=True)
        removed = red.eval(
            "if redis.call('GET',KEYS[1]) == ARGV[1] then "
            "redis.call('DEL',KEYS[1]); redis.call('SREM',KEYS[2],KEYS[1]); return 1 end; return 0",
            2, queue_id, get_queue_registry_key(), raw,
        )
        if removed:
            webhook_outbox.acknowledge_source(delivery_id)
            _clear_legacy_reset_if_empty(red, queue_id)
        return int(bool(removed))
    imported = 0
    for _ in range(limit):
        stage = webhook_legacy.stage_next(red, queue_id)
        if stage is None:
            break
        delivery_id = _persist_legacy_payload(
            queue_id, stage.raw, "legacy:" + stage.token,
            transient=TRANSIENT_IDENTIFIER in queue_id,
        )
        if not webhook_legacy.ack_stage(red, queue_id, stage.token):
            logger.warning("Legacy webhook head changed; retained stage requires review")
            break
        webhook_outbox.acknowledge_source(delivery_id)
        imported += 1
    if imported:
        _clear_legacy_reset_if_empty(red, queue_id)
    return imported


def _import_legacy_dead_letters(red, *, limit=LEGACY_IMPORT_BATCH):
    """Archive entries become durable before their expiring Redis copy is removed."""
    for _ in range(limit):
        stage = webhook_legacy.stage_next(red, DEAD_LETTER_QUEUE)
        if stage is None:
            break
        raw = stage.raw
        try:
            document = orjson.loads(raw)
            if (not isinstance(document, dict) or not document.get("id")
                    or "failed_at" not in document
                    or not isinstance(document.get("message"), dict)
                    or "sent_at" not in document["message"]):
                raise ValueError("Legacy archive lacks stable identity or time")
            entry = DeadLetterWebhookMessage.model_validate_json(raw)
            delivery_id = webhook_outbox.enqueue(
                entry.source_queue_id, entry.message.model_dump_json().encode(),
                entry.message.server_number, public_id=entry.id,
                dedupe_key="legacy-deadletter:" + entry.id, legacy=True,
                initial_status="review", reason=entry.reason,
                created_at=entry.failed_at, message_type=str(entry.message.message_type),
                webhook_type=str(entry.message.webhook_type), initial_attempts=entry.message.retry_attempts,
            )
        except (ValueError, TypeError, pydantic.ValidationError):
            # Invalid archival bytes are still preserved and visible.
            occurrence = "legacy-archive:" + stage.token
            delivery_id = webhook_outbox.enqueue(
                "whs:unknown:unknown:unknown:archive", raw,
                dedupe_key=occurrence, legacy=True, initial_status="review",
                reason="invalid_legacy_archive",
            )
        removed = webhook_legacy.ack_stage(red, DEAD_LETTER_QUEUE, stage.token)
        if not removed:
            break
        webhook_outbox.acknowledge_source(delivery_id)


def _best_effort_redis(function, *args, **kwargs):
    try:
        return function(*args, **kwargs)
    except redis.exceptions.RedisError:
        logger.warning("Optional webhook Redis metadata update unavailable")
        return None


def _response_bucket(response, previous):
    """Discord error responses and successful responses may omit rate headers."""
    data = previous.model_copy()
    headers = response.headers
    if headers.get(X_RATELIMIT_BUCKET):
        data.id = headers[X_RATELIMIT_BUCKET]
    try:
        remaining = int(headers[X_RATELIMIT_REMAINING])
        if remaining >= 0:
            data.remaining_requests = remaining
    except (KeyError, ValueError, TypeError):
        pass
    try:
        reset = float(headers[X_RATELIMIT_RESET_AFTER])
        if math.isfinite(reset) and 0 <= reset <= 86400:
            data.reset_after_secs = math.ceil(reset)
            data.reset_timestamp = math.ceil(datetime.now(timezone.utc).timestamp() + reset)
    except (KeyError, ValueError, TypeError):
        pass
    return data


def _retry_delay(response, bucket):
    try:
        body = response.json()
        delay = float(body.get("retry_after"))
        if math.isfinite(delay) and 0 <= delay <= 86400:
            return max(0.1, delay)
    except (ValueError, TypeError, AttributeError):
        pass
    return max(1.0, float(bucket.reset_after_secs or DEFAULT_GLOBAL_RETRY_AFTER_SECS))


async def dequeue_message(
    red: redis.StrictRedis, client: httpx.AsyncClient, queue_id: str,
    bucket_data: DiscordRateLimitData | None, lock: asyncio.Lock,
):
    """Claim SQL work; HTTP confirmation precedes optional Redis bookkeeping."""
    bucket_data = bucket_data or DiscordRateLimitData()
    async with lock:
        # Mixed-version upgrades retain the old occurrence until the SQL commit.
        await asyncio.to_thread(_import_legacy_queue, red, queue_id)
        # Never overtake an older, not-yet-imported Redis head.
        if red.exists(queue_id):
            return False
        claim = await asyncio.to_thread(
            webhook_outbox.claim, queue_id, lease_seconds=DELIVERY_LEASE_SECONDS,
        )
        if claim is None:
            return False
        started = False
        settled = False

        async def finish(status, reason=None, retry_after_seconds=0):
            nonlocal settled
            committed = await asyncio.to_thread(
                webhook_outbox.finish, claim.id, claim.token, status=status,
                reason=reason, retry_after_seconds=retry_after_seconds,
            )
            if not committed:
                logger.warning("Webhook ownership changed; retained outcome requires review")
            settled = True
            return committed

        try:
            try:
                message = unpack_message(claim.payload)
                if (_message_age_seconds(message) >= WH_MAX_MESSAGE_AGE_SECS
                        and not claim.allow_expired):
                    await finish("review", "message_expired")
                    return True
                wh = construct_webhook(payload=message.payload, webhook_type=message.webhook_type)
                # The application owns retry accounting and the durable state.
                wh.rate_limit_retry = False
            except (ValueError, TypeError, pydantic.ValidationError):
                await finish("review", "invalid_payload")
                return True

            # Read the current limit under the bucket lock, before sending.
            now = datetime.now(timezone.utc).timestamp()
            if is_globally_rate_limited(red):
                reset = get_global_rate_limit_reset_after(red)
                delay = max(0.1, min(86400.0, reset.timestamp() - now if reset else 0.1))
                await finish("retry", "global_rate_limit", delay)
                return True
            if bucket_data.id:
                bucket_data = get_rate_limit_bucket_data(red, bucket_data.id)
                if (bucket_data.rate_limited and bucket_data.reset_timestamp
                        and bucket_data.reset_timestamp + 1 > now):
                    await finish("retry", "bucket_rate_limit",
                                 min(86400.0, bucket_data.reset_timestamp + 1 - now))
                    return True
                if is_bucket_local_rate_limited(red, bucket_data.id, message.webhook_type):
                    await finish("retry", "local_rate_limit", max(0.1, LOCAL_RL_RESET_AFTER))
                    return True

            if not await asyncio.to_thread(webhook_outbox.mark_sending, claim.id, claim.token):
                settled = True
                return True
            started = True
            try:
                async with asyncio.timeout(DELIVERY_TIMEOUT_SECONDS):
                    response = await (wh.edit(client=client) if message.edit else wh.execute(client=client))
            except (httpx.HTTPError, TimeoutError):
                await finish("review", "transport_outcome_unknown")
                logger.warning("Webhook response unavailable; payload retained for review")
                return True

            status = response.status_code
            # A later Redis failure must never turn an acknowledged POST into a retry.
            if 200 <= status < 300:
                await finish("sent")
            elif status == 429:
                delay = _retry_delay(response, bucket_data)
                if claim.attempts + 1 >= WH_MAX_RETRY_ATTEMPTS:
                    await finish("review", "retry_limit_reached")
                else:
                    await finish("retry", "rate_limited", delay)
            else:
                reasons = {400: "invalid_request", 401: "unauthorized",
                           403: "forbidden", 404: "not_found"}
                await finish("review", reasons.get(status, f"http_{status}"))

            bucket = _response_bucket(response, bucket_data)
            bucket.webhook_type = message.webhook_type
            bucket.rate_limited = status == 429
            if status == 429:
                delay = _retry_delay(response, bucket)
                bucket.reset_after_secs = math.ceil(delay)
                bucket.reset_timestamp = math.ceil(datetime.now(timezone.utc).timestamp() + delay)
                _best_effort_redis(update_bucket_rate_limit, red, bucket.id or "unknown", message.webhook_type)
                try:
                    global_limit = bool(response.json().get("global"))
                except (ValueError, AttributeError):
                    global_limit = False
                if global_limit:
                    _best_effort_redis(set_global_rate_limit_reset_after, red,
                                      datetime.now(timezone.utc).timestamp() + delay)
            elif status == 404:
                _best_effort_redis(handle_webhook_not_found, red, queue_id, message.payload,
                                  message.webhook_type, str(wh.webhook_id))
            elif status in (401, 403):
                _best_effort_redis(set_webhook_error, red, str(wh.webhook_id), message.webhook_type,
                                  auth_401=status == 401, auth_403=status == 403)
            elif 200 <= status < 300:
                _best_effort_redis(clear_webhook_errors, red, str(wh.webhook_id), message.webhook_type)
            if bucket.id:
                canonical = get_or_create_bucket_lock(bucket.id)
                _best_effort_redis(set_bucket_data, red, bucket, canonical)
                _best_effort_redis(set_webhook_rate_limit_bucket, red=red, queue_id=queue_id, bucket_id=bucket.id)
        except redis.exceptions.RedisError:
            if not settled:
                await finish("review" if started else "retry",
                             "redis_interrupted_after_send" if started else "redis_unavailable",
                             0 if started else 1)
            raise
        except asyncio.CancelledError:
            if not settled:
                await asyncio.shield(finish(
                    "review" if started else "retry",
                    "worker_stopped_after_send" if started else "worker_stopped",
                ))
            raise
        except webhook_outbox.OutboxStorageError:
            # Lease recovery retains the accepted payload if the DB is unavailable.
            logger.error("Webhook outcome could not be committed; durable payload retained")
            raise
        except Exception:
            if not settled:
                await finish("review", "unexpected_delivery_error")
            logger.error("Webhook delivery interrupted; payload retained for review")
    return True


def get_queue_registry_key(prefix: str = PREFIX) -> str:
    # The webhook consumer is installation-wide and intentionally has no
    # SERVER_NUMBER. Queue keys still contain their originating server number,
    # while this single registry indexes queues from every configured server.
    return f"{prefix}:{QUEUE_REGISTRY_SUFFIX}"


def _decode_queue_ids(values) -> set[str]:
    return {
        value.decode() if isinstance(value, bytes) else str(value) for value in values
    }


def _registered_queue_keys(red: redis.StrictRedis, prefix: str = PREFIX) -> set[str]:
    """Discover legacy payloads once; SQL wakeups and archives are separate."""
    registry_key = get_queue_registry_key(prefix=prefix)
    members = _decode_queue_ids(red.smembers(registry_key))
    reserved = {registry_key, DEAD_LETTER_QUEUE, OUTBOX_WAKEUPS_KEY}
    def accepted(key):
        return key.startswith(prefix + ":") and key not in reserved
    registered = {key for key in members if accepted(key)}
    invalid = members - registered - {QUEUE_REGISTRY_SENTINEL}
    if invalid:
        red.srem(registry_key, *invalid)
    if QUEUE_REGISTRY_SENTINEL in members:
        return registered
    # Even a partially populated old registry must not hide another legacy
    # queue. Complete the one-time import before writing its sentinel.
    registered.update(
        key for key in _decode_queue_ids(red.scan_iter(match=f"{prefix}:*", _type="list"))
        if accepted(key)
    )
    registered.update(
        key for key in _decode_queue_ids(red.scan_iter(match=f"{prefix}:*", _type="string"))
        if accepted(key) and TRANSIENT_IDENTIFIER in key
    )
    red.sadd(registry_key, QUEUE_REGISTRY_SENTINEL, *registered)
    return registered


def get_all_queue_keys(
    red: redis.StrictRedis | None = None, prefix: str = PREFIX
) -> list[str]:
    """Retrieve registered persistent webhook queue keys."""
    logger.debug("Getting all queue IDs from %s", PREFIX)
    if red is None:
        red = get_redis_client(decode_responses=False, global_pool=True)

    legacy = {
        queue_id
        for queue_id in _registered_queue_keys(red=red, prefix=prefix)
        if TRANSIENT_IDENTIFIER not in queue_id
    }
    durable = {key for key in webhook_outbox.queue_lengths()
               if TRANSIENT_IDENTIFIER not in key and key.startswith(prefix + ":")}
    return sorted(legacy | durable)


def get_all_transient_message_keys(
    red: redis.StrictRedis | None = None, prefix: str = PREFIX
) -> list[str]:
    """Retrieve each registered transient key which acts as a queue ID."""
    if red is None:
        red = get_redis_client(decode_responses=False, global_pool=True)
    legacy = {
        queue_id
        for queue_id in _registered_queue_keys(red=red, prefix=prefix)
        if TRANSIENT_IDENTIFIER in queue_id
    }
    durable = {key for key in webhook_outbox.queue_lengths()
               if TRANSIENT_IDENTIFIER in key and key.startswith(prefix + ":")}
    return sorted(legacy | durable)


def get_all_queue_keys_and_lengths(
    red: redis.StrictRedis, prefix: str = PREFIX
) -> list[tuple[str, int]]:
    """Return each queue key and the number of elements in its queue"""
    lengths = webhook_outbox.queue_lengths()
    return [(queue_id, red.llen(queue_id) + lengths.get(queue_id, 0))
            for queue_id in get_all_queue_keys(red=red, prefix=prefix)]


def get_all_queue_keys_not_empty(
    red: redis.StrictRedis, prefix: str = PREFIX
) -> list[str]:
    """Scan for all the queues (identified by prefix)"""
    logger.debug("Getting all queue IDs with items from %s", PREFIX)
    populated_queues = [queue_id for queue_id, count in get_all_queue_keys_and_lengths(red, prefix) if count > 0]
    populated_transient_messages = get_all_transient_message_keys(
        red=red, prefix=prefix
    )
    return populated_queues + populated_transient_messages


@dataclass
class WebhookQueueKeyCache:
    """Reuse webhook queue keys while continuing to poll their contents."""

    red: redis.StrictRedis
    prefix: str = PREFIX
    refresh_interval_secs: float = QUEUE_KEY_REFRESH_INTERVAL_SECS
    queue_ids: tuple[str, ...] = ()
    transient_message_keys: tuple[str, ...] = ()
    next_refresh_at: float = 0.0

    def get_not_empty(self, now: float | None = None) -> list[str]:
        now = time.monotonic() if now is None else now
        if now >= self.next_refresh_at:
            registered = _registered_queue_keys(red=self.red, prefix=self.prefix)
            self.queue_ids = tuple(
                sorted(
                    queue_id
                    for queue_id in registered
                    if TRANSIENT_IDENTIFIER not in queue_id
                )
            )
            self.transient_message_keys = tuple(
                sorted(
                    queue_id
                    for queue_id in registered
                    if TRANSIENT_IDENTIFIER in queue_id
                )
            )
            self.next_refresh_at = now + self.refresh_interval_secs

        populated_queues: list[str] = []
        orphaned_queues: list[str] = []
        for queue_id in self.queue_ids:
            if self.red.llen(queue_id) > 0:
                populated_queues.append(queue_id)
            elif not self.red.exists(queue_id):
                # A deleted list stays in the registry until we remove it. Do
                # not remove merely empty lists: producers reuse them.
                orphaned_queues.append(queue_id)
        populated_transient_messages = [
            queue_id
            for queue_id in self.transient_message_keys
            if self.red.exists(queue_id)
        ]
        expired_transient_messages = set(self.transient_message_keys).difference(
            populated_transient_messages
        )
        expired_registry_entries = (*orphaned_queues, *expired_transient_messages)
        if expired_registry_entries:
            self.red.srem(
                get_queue_registry_key(prefix=self.prefix),
                *expired_registry_entries,
            )
        if orphaned_queues:
            self.queue_ids = tuple(
                queue_id
                for queue_id in self.queue_ids
                if queue_id not in orphaned_queues
            )
        if expired_transient_messages:
            self.transient_message_keys = tuple(populated_transient_messages)
        return populated_queues + populated_transient_messages


def get_transient_message_overview(
    queue_id: str,
    red: redis.StrictRedis | None,
) -> TransientMessageStatus | None:
    parts = _split_transient_message_key(queue_id=queue_id)

    if not parts:
        return

    if red is None:
        red = get_redis_client(decode_responses=False, global_pool=True)

    bucket_data: DiscordRateLimitData | None = None
    bucket_id = get_webhook_rate_limit_bucket(red=red, queue_id=queue_id)
    if bucket_id:
        bucket_data = get_rate_limit_bucket_data(red=red, bucket_id=bucket_id)

    overview: TransientMessageStatus = {
        "server_number": int(parts.server_number),
        "id": parts.id,
        "webhook_type": parts.wh_type,
        "message_type": parts.msg_type,
        "rate_limit_bucket": bucket_id,
        "rate_limited": bucket_data.rate_limited if bucket_data else False,
        "message_key": parts.message_group_key,
        "redis_key": queue_id,
    }
    return overview


def get_queue_overview(
    queue_id: str, red: redis.StrictRedis | None = None, *, durable_length: int | None = None
) -> QueueStatus | None:
    """Return a summary of a queue if it exists"""
    parts = _split_queue_id(queue_id=queue_id)

    if not parts:
        return

    if red is None:
        red = get_redis_client(decode_responses=False, global_pool=True)

    if durable_length is None:
        durable_length = webhook_outbox.queue_lengths().get(queue_id, 0)
    length = red.llen(queue_id) + durable_length
    bucket_data: DiscordRateLimitData | None = None
    bucket_id = get_webhook_rate_limit_bucket(red=red, queue_id=queue_id)
    if bucket_id:
        bucket_data = get_rate_limit_bucket_data(red=red, bucket_id=bucket_id)

    overview: QueueStatus = {
        "server_number": int(parts.server_number),
        "id": parts.id,
        "webhook_type": parts.wh_type,
        "message_type": parts.msg_type,
        "length": length,
        "rate_limit_bucket": bucket_data.id if bucket_data else None,
        "rate_limited": bucket_data.rate_limited if bucket_data else False,
        "redis_key": queue_id,
    }
    return overview


def get_next_queue_id(queue_ids: list[str]) -> str | None:
    """Get the next queue to process (if any) and re-add queue to the end"""
    logger.debug("Getting a random queue ID from %s", queue_ids)
    # People can add/remove webhooks in CRCON at any point, after we've scanned Redis
    # for queues, pick one at random instead of trying to track the previous one we did
    # this should be random enough that over time no queue gets priority and if any
    # one queue has a weird error, we shouldn't get stuck trying to reprocess it
    return random.choice(queue_ids) if queue_ids else None


def webhook_service_summary(red: redis.StrictRedis | None = None):
    """Return a queue overview for all queues, by server number, webhook type and message type"""
    if red is None:
        red = get_redis_client(decode_responses=False, global_pool=True)

    # Get the global rate limit status/expiration
    # Get each queue, by webhook type (discord, etc.) and the number of messages

    data = {}

    data["is_globally_rate_limited"] = is_globally_rate_limited(red=red)
    data["global_rate_limit_reset_after"] = get_global_rate_limit_reset_after(red=red)
    data["empty_dequeues"] = get_empty_dequeue_count(red=red)
    data["dead_letters"] = get_dead_letter_messages(red=red, limit=20)
    data["dead_letter_count"] = webhook_outbox.count_review() + red.llen(DEAD_LETTER_QUEUE)
    data["dead_letter_ttl_seconds"] = 0  # SQL review records have no automatic expiry.

    queue_ids = get_all_queue_keys(red=red)
    queues: defaultdict[int, dict[str, dict[str, list[QueueStatus]]]] = defaultdict(
        lambda: defaultdict(lambda: defaultdict(list))
    )
    lengths = webhook_outbox.queue_lengths()
    for qid in queue_ids:
        overview: QueueStatus | None = get_queue_overview(red=red, queue_id=qid, durable_length=lengths.get(qid, 0))
        if overview:
            queues[overview["server_number"]][overview["webhook_type"]][
                overview["message_type"]
            ].append(overview)

    data["queues"] = queues

    transient_messages: defaultdict[
        int, dict[str, dict[str, list[TransientMessageStatus]]]
    ] = defaultdict(lambda: defaultdict(lambda: defaultdict(list)))
    for key in get_all_transient_message_keys(red=red):
        transient_message_overview: TransientMessageStatus | None = (
            get_transient_message_overview(red=red, queue_id=key)
        )

        if transient_message_overview:
            transient_messages[transient_message_overview["server_number"]][
                transient_message_overview["webhook_type"]
            ][transient_message_overview["message_type"]].append(
                transient_message_overview
            )

    data["transient_messages"] = transient_messages
    return data


def _retain_reset_queue(queue_id, red):
    # Import in bounded batches before an explicit operator reset. Retained SQL
    # messages become review records instead of disappearing from an expiring list.
    retained = webhook_outbox.review_queue(queue_id, reason="operator_reset")
    # The persistent marker makes every remaining legacy head review-only.
    # A large backlog is archived by bounded worker passes after this call.
    imported = _import_legacy_queue(red, queue_id)
    remaining = red.exists(queue_id) or red.exists(webhook_legacy.stage_key(queue_id))
    if not remaining:
        _clear_legacy_reset_if_empty(red, queue_id)
    return retained or imported or bool(remaining)


def reset_all_queues_for_server_number(server_number, red=None) -> int:
    red = red or get_redis_client(decode_responses=False, global_pool=True)
    changed = 0
    for queue_id in get_all_queue_keys(red):
        parts = _split_queue_id(queue_id)
        if parts and parts.server_number == str(server_number):
            changed += bool(_retain_reset_queue(queue_id, red))
    return changed


def reset_webhook_queues(red=None) -> int:
    red = red or get_redis_client(decode_responses=False, global_pool=True)
    return sum(bool(_retain_reset_queue(queue_id, red)) for queue_id in get_all_queue_keys(red))


def reset_queue(queue_id: str, red=None) -> bool:
    red = red or get_redis_client(decode_responses=False, global_pool=True)
    return bool(_retain_reset_queue(queue_id, red))


def reset_queue_type(webhook_type, red=None) -> int:
    red = red or get_redis_client(decode_responses=False, global_pool=True)
    webhook_type = WebhookType(webhook_type)
    return sum(bool(_retain_reset_queue(qid, red)) for qid in get_all_queue_keys(red)
               if (parts := _split_queue_id(qid)) and parts.wh_type == webhook_type)


def reset_message_type(message_type, red=None) -> int:
    red = red or get_redis_client(decode_responses=False, global_pool=True)
    message_type = WebhookMessageType(message_type)
    return sum(bool(_retain_reset_queue(qid, red)) for qid in get_all_queue_keys(red)
               if (parts := _split_queue_id(qid)) and parts.msg_type == message_type)


def _split_queue_id(queue_id: str) -> QueueParts | None:
    """Parse a queue ID int its component parts (prefix, server number, webhook type, message type and ID)"""
    try:
        prefix, server_number, wh_type, msg_type, qid = queue_id.split(":")
        return QueueParts(
            prefix=prefix,
            server_number=server_number,
            wh_type=WebhookType(wh_type),
            msg_type=WebhookMessageType(msg_type),
            id=qid,
        )
    except ValueError:
        logger.error("Unable to parse %s received an invalid key", queue_id)
        return


def _split_transient_message_key(queue_id: str) -> TransientMessageParts | None:
    try:
        prefix, server_number, _, wh_type, msg_type, qid, message_key = queue_id.split(
            ":"
        )
        return TransientMessageParts(
            prefix=prefix,
            server_number=server_number,
            wh_type=WebhookType(wh_type),
            msg_type=WebhookMessageType(msg_type),
            id=qid,
            message_group_key=message_key,
        )
    except ValueError:
        logger.error("Unable to parse %s received an invalid key", queue_id)
        return


async def _wait_for_stop(stop_event, delay):
    try:
        await asyncio.wait_for(stop_event.wait(), timeout=max(0.01, delay))
    except TimeoutError:
        pass


async def main(*, stop_event: asyncio.Event | None = None):
    """Bound task/Redis memory and reconnect without discarding SQL work."""
    from pathlib import Path
    stop_event = stop_event or asyncio.Event()
    red = get_redis_client(redis_url=construct_redis_url(0), decode_responses=False, global_pool=True)
    queue_cache = WebhookQueueKeyCache(red=red)
    tasks: dict[asyncio.Task, str] = {}
    task_locks: dict[asyncio.Task, int] = {}
    ready: set[str] = set()
    next_poll = 0.0
    next_cleanup = 0.0
    backoff = 0.1
    Path(os.getenv("HLL_WH_HEALTH_PATH", "/code/webhook-service-healthy")).touch()
    logger.info("Starting durable webhook delivery service")
    async with httpx.AsyncClient(timeout=DELIVERY_TIMEOUT_SECONDS) as client:
        try:
            while not stop_event.is_set():
                try:
                    # Observe every task exception; no detached delivery tasks.
                    for task in tuple(tasks):
                        if task.done():
                            queue_id = tasks.pop(task)
                            task_locks.pop(task)
                            if task.result():
                                ready.add(queue_id)
                    now = time.monotonic()
                    hints = red.lpop(OUTBOX_WAKEUPS_KEY, max(1, WH_MAX_QUEUE_LENGTH))
                    if hints:
                        next_poll = 0
                    if now >= next_poll:
                        await asyncio.to_thread(_import_legacy_dead_letters, red)
                        legacy = set(queue_cache.get_not_empty(now))
                        legacy.update(webhook_legacy.staged_queues(red, limit=100))
                        legacy.discard(DEAD_LETTER_QUEUE)
                        for queue_id in sorted(legacy)[:100]:
                            await asyncio.to_thread(_import_legacy_queue, red, queue_id)
                        ready.update(await asyncio.to_thread(webhook_outbox.pending_queues, limit=100))
                        next_poll = now + OUTBOX_POLL_SECONDS
                    if now >= next_cleanup:
                        await asyncio.to_thread(webhook_outbox.cleanup_sent)
                        next_cleanup = now + 60
                    active_queues = set(tasks.values())
                    candidates = list(ready - active_queues)
                    random.shuffle(candidates)
                    for queue_id in candidates:
                        if len(tasks) >= MAX_DELIVERY_TASKS:
                            break
                        bucket_id = get_webhook_rate_limit_bucket(red, queue_id)
                        if bucket_id:
                            bucket, lock = get_bucket_lock(red, bucket_id)
                        else:
                            bucket, lock = DiscordRateLimitData(), get_shared_lock()
                        if lock.locked() or id(lock) in task_locks.values():
                            continue
                        task = asyncio.create_task(dequeue_message(
                            red=red, client=client, queue_id=queue_id,
                            bucket_data=bucket, lock=lock,
                        ))
                        tasks[task] = queue_id
                        task_locks[task] = id(lock)
                        ready.discard(queue_id)
                    backoff = 0.1
                    # Rate-limited/empty queues always yield; no hot continue loop.
                    await _wait_for_stop(stop_event, min(1.0, max(0.01, HLL_WH_IDLE_SLEEP_TIME)))
                except redis.exceptions.RedisError:
                    queue_cache.next_refresh_at = 0
                    next_poll = 0
                    ready.clear()
                    logger.warning("Redis connection interrupted; durable webhooks wait for reconnect")
                    await _wait_for_stop(stop_event, backoff)
                    backoff = min(5.0, backoff * 2)
                except webhook_outbox.OutboxStorageError:
                    next_poll = 0
                    ready.clear()
                    logger.error("Webhook outbox unavailable; accepted work remains retained")
                    await _wait_for_stop(stop_event, backoff)
                    backoff = min(5.0, backoff * 2)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    logger.error("Webhook worker iteration interrupted; accepted work remains retained")
                    await _wait_for_stop(stop_event, backoff)
                    backoff = min(5.0, backoff * 2)
        finally:
            # A known HTTP response gets a chance to commit its acknowledgement.
            # Each HTTP operation has its own timeout shorter than the SQL lease.
            if tasks:
                results = await asyncio.gather(*tasks, return_exceptions=True)
                if any(isinstance(result, BaseException) for result in results):
                    logger.warning("Webhook shutdown retained unfinished outcomes for recovery")


if __name__ == "__main__":
    asyncio.run(main())
