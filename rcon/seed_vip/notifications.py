"""Short-lived message outbox, consumed only by the Seed VIP process.

A lost acknowledgement can cause a duplicate notice, never another VIP grant.
"""

import json
import logging
import time
from uuid import uuid4

from rcon.cache_utils import get_redis_client
from rcon.utils import get_server_number

logger = logging.getLogger(__name__)
RETRY_SECONDS = 30
MAX_ATTEMPTS = 3
NOTICE_TTL = 600
MESSAGE_SPACING = 0.1


def send_notice(rcon, player_id, message):
    try:
        # Exit and discard a broken connection before any outbox retry.
        with rcon.without_retries():
            success = rcon.message_player(player_id=player_id, message=message)
        if not success:
            logger.warning("Seed VIP notice was not acknowledged")
        return bool(success)
    except Exception as exc:
        logger.warning("Seed VIP notice failed (%s)", type(exc).__name__)
        return False
    finally:
        time.sleep(MESSAGE_SPACING)


class NotificationOutbox:
    def __init__(self, redis=None, server_number=None):
        self.redis = redis if redis is not None else get_redis_client()
        self.key = f"seed_vip:{server_number or get_server_number()}:notices:v1"

    def enqueue(self, messages, rcon):
        if not messages:
            return
        now = time.time()
        batch = uuid4().hex
        values = {
            f"{batch}:{player_id}": json.dumps(
                dict(player_id=player_id, message=message, attempts=0,
                     due=now, expires=now + NOTICE_TTL)
            )
            for player_id, message in messages.items()
        }
        try:
            with self.redis.pipeline(transaction=True) as pipe:
                pipe.hset(self.key, mapping=values)
                pipe.expire(self.key, NOTICE_TTL)
                pipe.execute()
        except Exception as exc:
            logger.error("Seed VIP outbox unavailable (%s); sending once", type(exc).__name__)
            for player_id, message in messages.items():
                send_notice(rcon, player_id, message)

    def clear(self):
        try:
            self.redis.delete(self.key)
        except Exception as exc:
            logger.warning("Unable to clear Seed VIP notices (%s)", type(exc).__name__)

    def flush(self, rcon):
        """Return whether a short retry poll is needed. Never replay rewards."""
        try:
            entries = self.redis.hgetall(self.key)
            delivered = expired = 0
            started = time.monotonic()
            for ident, raw in entries.items():
                if time.monotonic() - started > 30:
                    break
                try:
                    item = json.loads(raw)
                    if (not isinstance(item['player_id'], str)
                            or not isinstance(item['message'], str)):
                        raise ValueError("Invalid notice")
                    now = time.time()
                    if item['expires'] <= now or item['attempts'] >= MAX_ATTEMPTS:
                        self.redis.hdel(self.key, ident)
                        expired += 1
                        continue
                    if item['due'] > now:
                        continue
                except (ValueError, TypeError, KeyError):
                    self.redis.hdel(self.key, ident)
                    expired += 1
                    continue
                # Count before sending, including interrupted attempts.
                item['attempts'] += 1
                item['due'] = now + RETRY_SECONDS
                self.redis.hset(self.key, ident, json.dumps(item))
                if send_notice(rcon, item['player_id'], item['message']):
                    self.redis.hdel(self.key, ident)
                    delivered += 1
            pending = self.redis.hlen(self.key)
            if entries:
                logger.info("Seed VIP notices: delivered=%s pending=%s expired=%s",
                            delivered, pending, expired)
            return bool(pending)
        except Exception as exc:
            logger.warning("Seed VIP outbox retry deferred (%s)", type(exc).__name__)
            return True
