"""Short-lived Seed VIP notice outbox with no replay after uncertain delivery."""

import json
import logging
import time
from uuid import uuid4

from redis.exceptions import WatchError

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
        if success is True:
            return True
        if success is False:
            logger.warning("Seed VIP notice was rejected")
            return False
        logger.warning("Seed VIP notice result was unclear; not retrying")
        return None
    except Exception as exc:
        logger.warning("Seed VIP notice result unclear (%s); not retrying", type(exc).__name__)
        return None
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
            # The transaction may have committed even when its reply was lost.
            # Sending here could duplicate the entry that will be recovered later.
            logger.error("Seed VIP outbox enqueue uncertain (%s); not sending directly", type(exc).__name__)

    def clear(self):
        try:
            self.redis.delete(self.key)
        except Exception as exc:
            logger.warning("Unable to clear Seed VIP notices (%s)", type(exc).__name__)

    def _claim(self, ident, raw, item):
        """Atomically reserve this exact queued version before any send."""
        try:
            with self.redis.pipeline(transaction=True) as pipe:
                pipe.watch(self.key)
                if pipe.hget(self.key, ident) != raw:
                    return False
                item["state"] = "sending"
                pipe.multi()
                pipe.hset(self.key, ident, json.dumps(item))
                pipe.execute()
                return True
        except WatchError:
            return False

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
                    if item['expires'] <= now:
                        self.redis.hdel(self.key, ident)
                        expired += 1
                        continue
                    if 'state' not in item and item['attempts'] > 0:
                        # Older releases did not distinguish rejection from a
                        # lost reply. Preserve the entry as uncertain on upgrade.
                        self._claim(ident, raw, item)
                        continue
                    if item.get('state', 'queued') == 'sending':
                        # A previous worker may have sent this notice before a
                        # crash or lost reply. Leave it until TTL expiry.
                        continue
                    if item.get('state', 'queued') != 'queued':
                        raise ValueError("Invalid notice state")
                    if item['attempts'] >= MAX_ATTEMPTS:
                        self.redis.hdel(self.key, ident)
                        expired += 1
                        continue
                    if item['due'] > now:
                        continue
                except (ValueError, TypeError, KeyError):
                    self.redis.hdel(self.key, ident)
                    expired += 1
                    continue
                # Persist the reservation before sending. A crash, Redis error,
                # or lost RCON reply must never make this entry retryable.
                item['attempts'] += 1
                item['due'] = now + RETRY_SECONDS
                if not self._claim(ident, raw, item):
                    continue
                result = send_notice(rcon, item['player_id'], item['message'])
                if result is True:
                    self.redis.hdel(self.key, ident)
                    delivered += 1
                elif result is False:
                    # The server explicitly rejected this attempt: a retry is safe.
                    item['state'] = 'queued'
                    self.redis.hset(self.key, ident, json.dumps(item))
            pending = self.redis.hlen(self.key)
            if entries:
                logger.info("Seed VIP notices: delivered=%s pending=%s expired=%s",
                            delivered, pending, expired)
            return bool(pending)
        except Exception as exc:
            logger.warning("Seed VIP outbox retry deferred (%s)", type(exc).__name__)
            return True
