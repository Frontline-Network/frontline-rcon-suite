"""Durable queue, policy worker and restart-safe VIP delivery."""

import copy
import hashlib
import logging
import time
from zoneinfo import ZoneInfo
from datetime import datetime, timedelta, timezone

from sqlalchemy.dialects.postgresql import insert

from rcon.models import SeedVipGrant, VipRewardEvent, VipRewardGrant, VipRewardState, enter_session
from rcon.service_runtime import stopping, wait
from rcon.user_config.seed_vip import SeedVIPUserConfig
from rcon.user_config.vip_rewards import VipRewardsUserConfig
from rcon.utils import get_server_number
from rcon.vip_rewards.engine import Engine, budget, gate
from rcon.vip_rewards.locking import lock, vip_lock

logger = logging.getLogger(__name__)


def server():
    return int(get_server_number())


def read_state(preview):
    with enter_session() as session:
        row = session.get(VipRewardState, (server(), preview))
        return copy.deepcopy(row.data) if row else {}


def read_gate_state(preview):
    """Keep the high-frequency log hook independent of accumulated player history."""
    fields = (
        "observed",
        "healthy",
        "released",
        "config",
        "counts",
        "thresholds",
        "above_since",
    )
    with enter_session() as session:
        row = (
            session.query(*(VipRewardState.data[key].label(key) for key in fields))
            .filter_by(server_number=server(), preview=preview)
            .first()
        )
        return dict(zip(fields, row)) if row else {}


def status():
    cfg = VipRewardsUserConfig.load_from_db()
    state = read_gate_state(cfg.dry_run)
    return {
        "status": gate(state, cfg, time.time()),
        "preview": cfg.dry_run,
        "counts": state.get("counts", {}),
        "thresholds": state.get("thresholds", {}),
        "observed": state.get("observed"),
        "above_since": state.get("above_since"),
        "pause_during_seeding": cfg.pause_during_seeding,
    }


def progress(player_id):
    cfg = VipRewardsUserConfig.load_from_db()
    return read_state(cfg.dry_run).get("players", {}).get(player_id, {})


def status_command_conflict(command):
    from rcon.user_config.autobalancer import AutobalancerUserConfig
    from rcon.user_config.chat_commands import ChatCommandsUserConfig
    from rcon.user_config.rcon_chat_commands import RConChatCommandsUserConfig
    from rcon.user_config.vote_map import VoteMapUserConfig
    if command == AutobalancerUserConfig.load_from_db().volunteer_command.casefold():
        return True
    for model in (ChatCommandsUserConfig, RConChatCommandsUserConfig, VoteMapUserConfig):
        data = model.load_from_db().model_dump()
        if not data.get("enabled", False):
            continue
        words = list(data.get("describe_words") or [])
        words.append(data.get("command", ""))
        for item in data.get("command_words", []):
            if item.get("enabled", True):
                words.extend(item.get("words", []))
        if command in {str(w).strip().casefold() for w in words}:
            return True
    return False


def status_message(cfg, state, pid, now):
    from rcon.vip_rewards.engine import periods
    if not cfg.weekly_support.enabled:
        return "Wochenziel Unterstützung ist deaktiviert. / Weekly support reward is disabled."
    week = periods(now, cfg.timezone)[1]
    player = state.get("players", {}).get(pid, {})
    progress = player.get("weekly_support", {})
    points = progress.get("points", 0) if progress.get("week") == week else 0
    reached = "weekly_support:" + week in player.get("completed", {})
    result = (f"Wochenziel / Weekly support ({week}, {cfg.timezone}): "
              f"{points} / {cfg.weekly_support.points} Punkte / points. "
              f"Belohnung / Reward: {cfg.weekly_support.hours:g} h VIP. ")
    if reached:
        result += "Ziel erreicht; Gutschrift separat bestätigt. / Goal reached; credit confirmed separately. "
    if gate(state, cfg, now) != "active":
        result += "Erfassung pausiert / Tracking paused. "
    return result + "Mo–So / Mon–Sun. VIP-Limit gilt / VIP cap applies."


def journal(offset=0, limit=50, player_id=None, preview=None):
    offset, limit = max(0, int(offset)), min(100, max(1, int(limit)))
    cfg = VipRewardsUserConfig.load_from_db()
    mode = cfg.dry_run if preview is None else str(preview).lower() in ("true", "1")
    with enter_session() as session:
        query = session.query(VipRewardGrant).filter_by(
            server_number=server(), preview=mode
        )
        if player_id:
            query = query.filter_by(player_id=player_id)
        return {
            "total": query.count(),
            "offset": offset,
            "results": [
                row.to_dict()
                for row in query.order_by(VipRewardGrant.id.desc())
                .offset(offset)
                .limit(limit)
            ],
        }


def acknowledge_review(grant_id, by):
    """Explicit operator acknowledgement; never replays a write or refunds its budget."""
    with enter_session() as session:
        row = session.get(VipRewardGrant, int(grant_id))
        if row is None or row.server_number != server():
            return False
        pid = row.player_id
    with vip_lock(pid):
        with enter_session() as session:
            row = session.get(VipRewardGrant, int(grant_id))
            if row.status != "review":
                return False
            row.status = "reviewed"
            row.reason = f"Manuell geprüft von {by}; keine erneute Auszahlung"
    return True


def enqueue(payload):
    cfg = VipRewardsUserConfig.load_from_db()
    if not cfg.enabled:
        return
    now = time.time()
    if not 0 <= now - payload["time"] <= 60:
        return
    if payload["kind"] == "kill" and not (
        cfg.melee.enabled or any(c.enabled for c in cfg.challenges)
    ):
        return
    state = read_gate_state(cfg.dry_run)
    payload = dict(payload)
    payload["allowed"] = (
        gate(state, cfg, now) == "active"
        and state.get("config") == cfg.model_dump_json()
    )
    payload["config"] = cfg.model_dump_json()
    key = hashlib.sha256(str(payload["key"]).encode()).hexdigest()
    payload["key"] = key
    with enter_session() as session:
        session.execute(
            insert(VipRewardEvent)
            .values(
                server_number=server(),
                preview=cfg.dry_run,
                key=key,
                payload=payload,
                processed=False,
            )
            .on_conflict_do_nothing()
        )


def observe(rcon, cfg):
    """Only fully observed snapshots can credit time or release the seeding gate."""
    try:
        game = rcon.get_gamestate()
        details = rcon.get_detailed_players()
        counts = {
            "allies": int(game["num_allied_players"]),
            "axis": int(game["num_axis_players"]),
        }
        players = {
            pid: {"name": p["name"], "team": str(p.get("team", "")).lower(),
                  "support": p.get("support")}
            for pid, p in details["players"].items()
        }
        healthy = not details.get("fail_count", 0)
        # Missing player details must not earn attendance time.
        healthy = healthy and sum(p["team"] in counts for p in players.values()) >= sum(
            counts.values()
        )
        return players, counts, healthy
    except Exception:
        logger.exception("VIP reward snapshot failed; rewards paused")
        return {}, {"allies": 0, "axis": 0}, False


def current_round():
    from rcon.utils import MapsHistory

    try:
        return MapsHistory()[0]["start"] or None
    except Exception:
        logger.warning("Round identity unavailable; round rewards paused")
        return None


def tick(rcon):
    # Serializes snapshots and queue consumers across multiple service processes.
    with lock(f"vip-rewards-worker:{server()}"):
        cfg = VipRewardsUserConfig.load_from_db()
        seed = SeedVIPUserConfig.load_from_db()
        players, counts, healthy = (
            observe(rcon, cfg) if cfg.enabled else ({}, {"allies": 0, "axis": 0}, False)
        )
        round_id = current_round() if cfg.enabled and (cfg.round.enabled or cfg.weekly_support.enabled) else None
        now = time.time()
        with enter_session() as session:
            row = session.get(VipRewardState, (server(), cfg.dry_run))
            if row is None:
                row = VipRewardState(
                    server_number=server(), preview=cfg.dry_run, data={}
                )
                session.add(row)
            data = copy.deepcopy(row.data)
            engine = Engine(data, cfg, game=getattr(getattr(rcon, "game_profile", None), "game", "hll"))
            # A current failure or population drop also blocks queued events.
            thresholds = {
                "allies": seed.requirements.max_allies,
                "axis": seed.requirements.max_axis,
            }
            if not healthy or (
                cfg.pause_during_seeding
                and (
                    data.get("thresholds") != thresholds
                    or any(counts[t] < thresholds[t] for t in counts)
                )
            ):
                data["released"] = False
                if not healthy:
                    data["healthy"] = False
            events = (
                session.query(VipRewardEvent)
                .filter_by(server_number=server(), processed=False)
                .order_by(VipRewardEvent.id)
                .limit(5000)
                .all()
            )
            for event in events:
                if event.preview == cfg.dry_run:
                    engine.event(event.payload, now)
                event.processed = True
            # Also detect boundaries missed while this worker/log loop was offline.
            if data.get("round_id") != round_id:
                data["round_seconds"] = 0
                data["baseline"] = None
                for player in data["players"].values():
                    player["round"] = 0
                    player.pop("support_highwater", None)
                    player.pop("balance", None)
            data["round_id"] = round_id
            data["round_known"] = round_id is not None
            session.query(VipRewardEvent).filter(
                VipRewardEvent.server_number == server(),
                VipRewardEvent.processed.is_(True),
                VipRewardEvent.payload["time"].as_float() < now - 172800,
            ).delete(synchronize_session=False)
            engine.snapshot(now, players, counts, thresholds, healthy)
            row.data = data
            for claim in engine.claims:
                session.execute(
                    insert(VipRewardGrant)
                    .values(
                        server_number=server(),
                        preview=cfg.dry_run,
                        player_id=claim["player_id"],
                        rule=claim["rule"],
                        trigger=claim["trigger"],
                        occurred=claim["occurred"],
                        requested_seconds=claim["hours"] * 3600,
                        credited_seconds=0,
                        limit=claim["limit"],
                        status="queued",
                        reason="",
                        description="",
                    )
                    .on_conflict_do_nothing()
                )
        # Journal and progress are committed before any VIP writes.
        with enter_session() as session:
            ids = [
                r.id
                for r in session.query(VipRewardGrant)
                .filter(
                    VipRewardGrant.server_number == server(),
                    VipRewardGrant.status.in_(["queued", "prepared"]),
                )
                .order_by(VipRewardGrant.id)
                .limit(500)
            ]
        for grant_id in ids:
            try:
                deliver(rcon, grant_id)
            except Exception:
                logger.exception("VIP reward delivery failed for grant %s", grant_id)


def current_vip(rcon, player_id):
    from rcon.rcon import Rcon

    Rcon.get_vip_ids.cache_clear()
    rows = [row for row in rcon.get_vip_ids() if row["player_id"] == player_id]
    if len(rows) > 1:
        raise ValueError("Ambiguous VIP record")
    return rows[0] if rows else None


def expiration(value):
    if isinstance(value, str):
        value = datetime.fromisoformat(value.replace("Z", "+00:00"))
    if not isinstance(value, datetime):
        raise ValueError("Unknown VIP expiration")
    return (
        value.replace(tzinfo=timezone.utc)
        if value.tzinfo is None
        else value.astimezone(timezone.utc)
    )


def permanent(row):
    from rcon.utils import INDEFINITE_VIP_DATE

    return row is not None and (
        row["vip_expiration"] is None
        or expiration(row["vip_expiration"]) >= expiration(INDEFINITE_VIP_DATE)
    )


def award_period_start(now, period, timezone_name):
    if period == "rolling_day":
        return now - 86400
    local = datetime.fromtimestamp(now, ZoneInfo(timezone_name))
    start = local.replace(hour=0, minute=0, second=0, microsecond=0)
    if period == "week":
        start -= timedelta(days=start.weekday())
    elif period == "month":
        start = start.replace(day=1)
    elif period != "day":
        raise ValueError("Unknown award limit period")
    return start.timestamp()


def reward_rule_config(config, rule):
    kind, separator, rule_id = rule.partition(":")
    if separator and kind in {"event", "challenge"}:
        rules = config.events if kind == "event" else config.challenges
        return next((item for item in rules if item.id == rule_id), None)
    return getattr(config, rule, None)


def deliver(rcon, grant_id):
    with enter_session() as session:
        row = session.get(VipRewardGrant, grant_id)
        pid = row.player_id
    with vip_lock(pid):
        cfg = VipRewardsUserConfig.load_from_db()
        now = time.time()
        with enter_session() as session:
            row = session.get(VipRewardGrant, grant_id)
            if row.status not in ("queued", "prepared"):
                return
            was_prepared = row.status == "prepared"
            if not was_prepared:
                enabled_rules = Engine({}, cfg).rule_keys()
                if (
                    row.preview != cfg.dry_run
                    or gate(read_gate_state(cfg.dry_run), cfg, now) != "active"
                    or row.rule not in enabled_rules
                    or pid in cfg.excluded_player_ids
                ):
                    row.status, row.reason = "skipped", "disabled_or_paused"
                    return
                rule_config = reward_rule_config(cfg, row.rule)
                period = getattr(rule_config, "limit_period", "rolling_day")
                period_start = award_period_start(now, period, cfg.timezone)
                old = (
                    session.query(VipRewardGrant)
                    .filter(
                        VipRewardGrant.server_number == server(),
                        VipRewardGrant.preview == row.preview,
                        VipRewardGrant.player_id == pid,
                        VipRewardGrant.written_at >= min(now - 86400, period_start),
                        VipRewardGrant.credited_seconds > 0,
                    )
                    .all()
                )
                used = sum(g.credited_seconds for g in old if g.written_at > now - 86400)
                allowed = budget(row.requested_seconds, used, cfg.daily_hours * 3600)
                configured_limit = getattr(rule_config, "limit", 0)
                limit = min(row.limit, configured_limit) if row.limit and configured_limit else row.limit or configured_limit
                if limit and sum(g.rule == row.rule and g.written_at >= period_start for g in old) >= limit:
                    allowed = 0
                    row.reason = "rule_limit"
                if not allowed:
                    row.status, row.reason = "skipped", row.reason or "daily_budget"
                    return
                vip = current_vip(rcon, pid)
                if permanent(vip):
                    row.status, row.reason = "skipped", "permanent_vip"
                    return
                # An unresolved earlier write must be reviewed before adding more time.
                unresolved = (
                    session.query(VipRewardGrant)
                    .filter(
                        VipRewardGrant.server_number == server(),
                        VipRewardGrant.player_id == pid,
                        VipRewardGrant.preview == row.preview,
                        VipRewardGrant.status.in_(["prepared", "review"]),
                    )
                    .first()
                )
                unresolved_seed = (
                    session.query(SeedVipGrant.id)
                    .filter(
                        SeedVipGrant.server_number == server(),
                        SeedVipGrant.player_id == pid,
                        SeedVipGrant.preview == row.preview,
                        SeedVipGrant.status.in_(["prepared", "review"]),
                    )
                    .first()
                )
                if unresolved_seed:
                    # Nothing was sent for this grant. Retry after the seed
                    # write is reviewed rather than discarding the reward.
                    row.reason = "previous_seed_write_needs_review"
                    return
                if unresolved:
                    row.status, row.reason = "skipped", "previous_write_needs_review"
                    return
                base = (
                    max(
                        datetime.fromtimestamp(now, timezone.utc),
                        expiration(vip["vip_expiration"]),
                    )
                    if vip
                    else datetime.fromtimestamp(now, timezone.utc)
                )
                row.target = (base + timedelta(seconds=allowed)).isoformat()
                row.description = vip["name"] if vip else "VIP-Belohnung"
                row.credited_seconds, row.written_at = allowed, now
                row.reason = "partial_budget" if allowed < row.requested_seconds else ""
                row.status = "preview" if row.preview else "prepared"
                if row.preview:
                    return
            target, description = row.target, row.description
        # The durable target is committed before this call. Never add the duration again.
        if was_prepared:
            vip = current_vip(rcon, pid)
            confirmed = (
                vip is not None
                and vip["vip_expiration"] is not None
                and abs(
                    (
                        expiration(vip["vip_expiration"]) - expiration(target)
                    ).total_seconds()
                )
                < 1
            )
            with enter_session() as session:
                row = session.get(VipRewardGrant, grant_id)
                row.status = "awarded" if confirmed else "review"
                row.reason = "reconciled" if confirmed else "uncertain_write"
            return
        try:
            result = rcon.add_vip(
                player_id=pid, description=description, expiration=target
            )
            vip = current_vip(rcon, pid)
            confirmed = (
                result is True
                and vip is not None
                and vip["vip_expiration"] is not None
                and abs(
                    (
                        expiration(vip["vip_expiration"]) - expiration(target)
                    ).total_seconds()
                )
                < 1
            )
        except Exception:
            # Leave the prepared record intact for read-only reconciliation on next tick.
            logger.exception("Uncertain VIP write for grant %s", grant_id)
            return
        with enter_session() as session:
            row = session.get(VipRewardGrant, grant_id)
            row.status = "awarded" if confirmed else "review"
            if not confirmed:
                row.reason = "readback_mismatch"
            seconds = row.credited_seconds
        if confirmed and cfg.notify_player:
            try:
                rcon.message_player(
                    player_id=pid,
                    message=f"VIP-Belohnung: +{seconds / 3600:g} Stunden VIP. Vielen Dank!",
                )
            except Exception:
                logger.exception("Reward delivered; player message failed for %s", pid)


def run(stop_event=None):
    from rcon.api_commands import get_rcon_api

    rcon = get_rcon_api()
    # A fresh process never estimates attendance during its downtime, even <60 s.
    with lock(f"vip-rewards-worker:{server()}"):
        with enter_session() as session:
            for state in session.query(VipRewardState).filter_by(
                server_number=server()
            ):
                data = copy.deepcopy(state.data)
                data.update(
                    baseline=None, healthy=False, released=False, above_since=None
                )
                for player in data.get("players", {}).values():
                    player.pop("balance", None)
                state.data = data
    while not stopping(stop_event):
        started = time.monotonic()
        try:
            tick(rcon)
        except Exception:
            logger.exception(
                "VIP rewards worker failed; no unobserved time will be credited"
            )
        if wait(stop_event, max(1, 30 - (time.monotonic() - started))):
            return
