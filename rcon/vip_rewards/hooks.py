"""Log hooks only enqueue data; no VIP network operations in the log loop."""

import time
import logging
import uuid

from rcon.cache_utils import get_redis_client
from rcon.logs.loop import (
    on_chat,
    on_disconnected,
    on_generic,
    on_kill,
    on_match_end,
    on_match_start,
)
from rcon.user_config.autobalancer import AutobalancerUserConfig
from rcon.user_config.vip_rewards import VipRewardsUserConfig
from rcon.utils import get_server_number
from rcon.vip_rewards.service import enqueue, read_state
from rcon.vip_rewards.locking import switch_state_lock


def forced_key(pid):
    return f"vip-rewards-forced:{get_server_number()}:{pid}"


def forced_pending_key(pid):
    return f"vip-rewards-forced-pending:{get_server_number()}:{pid}"


def forced_inflight_key(pid):
    return f"vip-rewards-forced-inflight:{get_server_number()}:{pid}"


def players_with_forced_switch(player_ids, now):
    """Read while holding switch_state_lock; Redis failure must stop the snapshot."""
    player_ids = list(player_ids)
    with get_redis_client().pipeline(transaction=False) as pipe:
        for pid in player_ids:
            pipe.exists(forced_key(pid))
            pipe.zcount(forced_pending_key(pid), now, "+inf")
            pipe.zcount(forced_inflight_key(pid), now, "+inf")
        values = pipe.execute()
    return {pid for index, pid in enumerate(player_ids) if any(values[index * 3:index * 3 + 3])}


def mark_forced(pid, on_death=False):
    # Each command owns its marker: rejecting one command must not clear another.
    token, started = uuid.uuid4().hex, time.time()
    redis = get_redis_client()
    with switch_state_lock(), redis.pipeline(transaction=True) as pipe:
        pipe.zadd(forced_pending_key(pid), {token: started + (86400 if on_death else 120)})
        pipe.zadd(forced_inflight_key(pid), {token: started + 86400})
        pipe.expire(forced_pending_key(pid), 86400)
        pipe.expire(forced_inflight_key(pid), 86400)
        pipe.execute()
    return token, started


def finish_forced(pid, marker, rejected=False):
    token, started = marker
    with switch_state_lock():
        if rejected:
            with get_redis_client().pipeline(transaction=True) as pipe:
                pipe.zrem(forced_pending_key(pid), token)
                pipe.zrem(forced_inflight_key(pid), token)
                pipe.execute()
            return
        enqueue(
            dict(
                kind="forced",
                player_id=pid,
                time=time.time(),
                switch_started=started,
                key=f"forced:{pid}:{token}",
            )
        )
        get_redis_client().zrem(forced_inflight_key(pid), token)


def payload(kind, log):
    return dict(
        kind=kind,
        player_id=log.get("player_id_1"),
        time=log["timestamp_ms"] / 1000,
        key=f"{log['timestamp_ms']}:{log.get('line_without_time') or log.get('raw')}",
    )


@on_kill
def kill(rcon, log):
    event = payload("kill", log)
    event.update(victim=log.get("player_id_2"), weapon=log.get("weapon"))
    enqueue(event)


@on_chat
def signup(rcon, log):
    message = str(log.get("sub_content") or log.get("message") or "").strip()
    if not message.startswith("!") or len(message.split()) != 1:
        return
    command = AutobalancerUserConfig.load_from_db().volunteer_command
    if message.casefold() == command.casefold():
        enqueue(payload("signup", log))


@on_chat
def reward_status(rcon, log):
    message = str(log.get("sub_content") or log.get("message") or "").strip().casefold()
    if not message.startswith("!") or len(message.split()) != 1:
        return
    cfg = VipRewardsUserConfig.load_from_db()
    if not cfg.enabled or cfg.dry_run or not cfg.status_command or message != cfg.status_command:
        return
    pid = log.get("player_id_1")
    now = time.time()
    if not pid or not 0 <= now - log.get("timestamp_ms", 0) / 1000 <= 60:
        return
    try:
        from rcon.vip_rewards.service import status_message, status_command_conflict
        if status_command_conflict(cfg.status_command):
            return
        if not get_redis_client().set(f"vip-rewards-status:{get_server_number()}:{pid}", "1", nx=True, ex=30):
            return
        rcon.message_player(player_id=pid, message=status_message(cfg, read_state(False), pid, now))
    except Exception:
        logging.getLogger(__name__).exception("VIP reward status reply failed")


@on_disconnected
def disconnected(rcon, log):
    enqueue(payload("disconnect", log))


@on_match_start
def round_start(rcon, log):
    enqueue(payload("round_start", log))


@on_match_end
def round_end(rcon, log):
    enqueue(payload("round_end", log))


def switch(rcon, log):
    cfg = VipRewardsUserConfig.load_from_db()
    if not cfg.enabled or not cfg.balance.enabled:
        return
    event = payload("switch", log)
    if not event["player_id"]:
        # HLL switch logs can contain only names. Ambiguous names are never rewarded.
        matches = [
            pid
            for pid, p in read_state(cfg.dry_run).get("online", {}).items()
            if p.get("name") == log.get("player_name_1")
        ]
        if len(matches) != 1:
            return
        event["player_id"] = matches[0]
    parts = str(log.get("sub_content", "")).lower().split(" > ")
    if len(parts) != 2:
        return
    event.update(source=parts[0].strip(), target=parts[1].strip())
    with switch_state_lock():
        red = get_redis_client()
        pid = event["player_id"]
        pending_key = forced_pending_key(pid)
        now = time.time()
        red.zremrangebyscore(pending_key, "-inf", now)
        markers = red.zrangebyscore(pending_key, now, "+inf")
        legacy_marker = red.get(forced_key(pid))
        event["forced"] = bool(markers or legacy_marker)
        enqueue(event)
        if event["forced"] and event["target"] in ("axis", "allies"):
            # Concurrent commands cannot be matched to individual log lines.
            # Preserve ambiguous markers until their individual expiry.
            if len(markers) == 1:
                red.zrem(pending_key, *markers)
            if legacy_marker:
                red.delete(forced_key(pid))


on_generic("TEAMSWITCH", switch)
