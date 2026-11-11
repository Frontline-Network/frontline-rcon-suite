"""Log hooks only enqueue data; no VIP network operations in the log loop."""

import time
import logging

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


def forced_key(pid):
    return f"vip-rewards-forced:{get_server_number()}:{pid}"


def mark_forced(pid, on_death=False):
    # Set before sending the switch command; a failed command errs on the safe side.
    get_redis_client().setex(forced_key(pid), 86400 if on_death else 120, "1")
    enqueue(
        dict(
            kind="forced",
            player_id=pid,
            time=time.time(),
            key=f"forced:{pid}:{time.time_ns()}",
        )
    )


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
    red = get_redis_client()
    event["forced"] = bool(red.get(forced_key(event["player_id"])))
    enqueue(event)
    if event["forced"] and event["target"] in ("axis", "allies"):
        red.delete(forced_key(event["player_id"]))


on_generic("TEAMSWITCH", switch)
