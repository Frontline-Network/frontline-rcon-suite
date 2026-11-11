"""Bounded, server-local diagnostics; never control delivery from this cache."""
import json
import logging
import time
from datetime import datetime, timezone
from rcon.cache_utils import get_redis_client

logger = logging.getLogger(__name__)
STATE = "campaign:broadcast:state"
HISTORY = "campaign:broadcast:history"

def iso(timestamp):
    return datetime.fromtimestamp(timestamp, timezone.utc).isoformat()

def update_state(phase, next_at=None):
    try:
        get_redis_client().set(STATE, json.dumps({"phase": phase, "updated_at": iso(time.time()), "next_at": iso(next_at) if next_at else None}), ex=90)
    except Exception:
        logger.exception("Cannot record broadcast worker state")

def record_attempt(campaign, message, accepted, error=None):
    entry = {"at": iso(time.time()), "campaign_id": campaign.id, "title": campaign.title, "message": message, "status": "accepted" if accepted else "unconfirmed", "error": error}
    logger.info("Broadcast campaign %s: %s", campaign.id, entry["status"])
    try:
        with get_redis_client().pipeline() as pipe:
            pipe.lpush(HISTORY, json.dumps(entry))
            pipe.ltrim(HISTORY, 0, 199)
            pipe.expire(HISTORY, 86400)
            pipe.execute()
    except Exception:
        logger.exception("Cannot record broadcast outcome")

def get_status():
    try:
        red = get_redis_client()
        state = json.loads(red.get(STATE) or "null")
        cutoff = iso(time.time() - 86400)
        recent = [entry for row in red.lrange(HISTORY, 0, 19)
                  if (entry := json.loads(row))["at"] >= cutoff]
        return {"available": True, "state": state, "recent": recent}
    except Exception:
        logger.exception("Cannot read broadcast activity")
        return {"available": False, "state": None, "recent": []}
