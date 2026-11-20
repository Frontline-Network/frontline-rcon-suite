from __future__ import annotations

import hashlib
import hmac
import json
import logging
import os
import secrets
import threading
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Callable

import requests
from sqlalchemy import String, cast, func, or_

from rcon.broadcast import campaign_is_eligible, format_message
from rcon.models import (
    Blacklist,
    BlacklistRecord,
    CampaignDelivery,
    LogLine,
    PlayerID,
    PlayerSession,
    VipLifecycleDelivery,
    enter_session,
)
from rcon.user_config.auto_broadcast import VipLifecycleCampaign, VipLifecycleConfig
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig
from rcon.active_session_selection import latest_open_sessions
from rcon.types import GameIntEnum
from rcon.utils import get_server_number

logger = logging.getLogger(__name__)

RULE_UNVERIFIED = "unverified"
RULE_TRIAL_ACTIVE = "trial_active"
RULE_TRIAL_EXPIRING = "trial_expiring"
RULE_TRIAL_EXPIRED = "trial_expired"
RULES = (
    RULE_UNVERIFIED,
    RULE_TRIAL_ACTIVE,
    RULE_TRIAL_EXPIRING,
    RULE_TRIAL_EXPIRED,
)
_cache_lock = threading.Lock()
_status_cache: dict[tuple[str, str], tuple[float, dict[str, Any]]] = {}


def feature_enabled() -> bool:
    """Return whether this installation is allowed to expose VIP lifecycle."""

    return os.getenv("FRONTLINE_VIP_LIFECYCLE_ENABLED", "false").strip().lower() in {
        "1",
        "true",
        "yes",
        "on",
    }


def require_feature_enabled() -> None:
    if not feature_enabled():
        raise ValueError("VIP lifecycle campaigns are not available")


@dataclass(frozen=True)
class LifecycleDecision:
    rule: str
    status_fingerprint: str


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def parse_utc_timestamp(value: Any) -> datetime | None:
    if not isinstance(value, str) or not value.strip():
        return None
    candidate = value.strip().replace("Z", "+00:00")
    try:
        parsed = datetime.fromisoformat(candidate)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return None
    return parsed.astimezone(timezone.utc)


def classify_status(
    status: dict[str, Any],
    *,
    now: datetime,
    expiry_window_hours: int,
) -> LifecycleDecision | None:
    """Map a validated WordPress status to exactly one lifecycle rule."""

    now = _as_utc(now)
    if status.get("status_known") is not True:
        return None

    if status.get("verified") is False:
        return LifecycleDecision(
            RULE_UNVERIFIED,
            _fingerprint_status(status, RULE_UNVERIFIED),
        )

    if status.get("verified") is not True:
        return None

    # Paid customers never receive lifecycle advertising, active or expired.
    if status.get("has_purchased_vip") is True:
        return None

    if status.get("grant_source") != "trial":
        return None

    expires_at = parse_utc_timestamp(status.get("expires_at"))
    if expires_at is None:
        return None

    if status.get("vip_active") is True and expires_at > now:
        remaining = expires_at - now
        rule = (
            RULE_TRIAL_EXPIRING
            if remaining <= timedelta(hours=expiry_window_hours)
            else RULE_TRIAL_ACTIVE
        )
        return LifecycleDecision(rule, _fingerprint_status(status, rule))

    if status.get("vip_active") is False and expires_at <= now:
        return LifecycleDecision(
            RULE_TRIAL_EXPIRED,
            _fingerprint_status(status, RULE_TRIAL_EXPIRED),
        )
    return None


def _fingerprint_status(status: dict[str, Any], rule: str) -> str:
    # WordPress offers a single free trial per player and family. A provider
    # offering repeat trials can identify each grant independently of its expiry.
    if rule == RULE_UNVERIFIED:
        return "invitation"
    trial_id = status.get("trial_id")
    if not trial_id:
        return "single"
    return hashlib.sha256(trial_id.encode()).hexdigest()[:48]



def _local_server_family() -> str:
    return (
        "hll_vietnam"
        if os.getenv("HLL_GAME", "hll").strip().lower() == "hllv"
        else "hll"
    )


def _status_url() -> str:
    configured = os.getenv("FRONTLINE_VIP_STATUS_URL", "").strip()
    if configured:
        return configured
    redeem_url = os.getenv("FRONTLINE_VIP_REDEEM_URL", "").strip()
    if redeem_url.endswith("/redeem"):
        return redeem_url[: -len("/redeem")] + "/lifecycle-status"
    return ""


def _signed_headers(secret: str, body: bytes) -> dict[str, str]:
    timestamp = str(int(time.time()))
    nonce = secrets.token_hex(16)
    signature = hmac.new(
        secret.encode(),
        b"\n".join((timestamp.encode(), nonce.encode(), body)),
        hashlib.sha256,
    ).hexdigest()
    return {
        "Content-Type": "application/json",
        "X-FLN-Timestamp": timestamp,
        "X-FLN-Nonce": nonce,
        "X-FLN-Signature": signature,
    }


def _validate_status(
    raw: Any, *, player_id: str, server_family: str
) -> dict[str, Any] | None:
    if not isinstance(raw, dict):
        return None
    if raw.get("player_id") != player_id:
        return None
    if raw.get("server_family") != server_family:
        return None
    if raw.get("status_known") is not True:
        return None
    if not all(
        isinstance(raw.get(field), bool)
        for field in ("verified", "vip_active", "has_purchased_vip")
    ):
        return None
    if raw.get("grant_source") not in {"trial", "paid", "none"}:
        return None
    expires_at = raw.get("expires_at")
    if expires_at is not None and parse_utc_timestamp(expires_at) is None:
        return None
    verified = raw["verified"]
    vip_active = raw["vip_active"]
    purchased = raw["has_purchased_vip"]
    grant_source = raw["grant_source"]

    # Fail closed on combinations the WordPress source of truth cannot produce.
    # This prevents a partially migrated or malformed response from selecting an
    # advertising rule merely because one boolean happened to be false.
    if not verified and (
        vip_active or purchased or grant_source != "none" or expires_at is not None
    ):
        return None
    if grant_source == "trial" and (
        not verified or purchased or expires_at is None
    ):
        return None
    if grant_source == "paid" and (not verified or not purchased):
        return None
    if purchased and grant_source != "paid":
        return None
    trial_id = raw.get("trial_id")
    if trial_id is not None and (not isinstance(trial_id, str) or not trial_id.strip() or len(trial_id) > 256):
        return None
    return {
        "trial_id": trial_id,
        "player_id": player_id,
        "server_family": server_family,
        "status_known": True,
        "verified": verified,
        "vip_active": vip_active,
        "grant_source": grant_source,
        "expires_at": expires_at,
        "has_purchased_vip": purchased,
        "status_version": str(raw.get("status_version") or ""),
    }


def fetch_statuses(
    player_ids: set[str],
    *,
    server_family: str,
    cache_seconds: int,
    force: bool = False,
    post: Callable[..., Any] = requests.post,
) -> dict[str, dict[str, Any]]:
    """Fetch missing player states with one authenticated batch request."""

    if not player_ids:
        return {}
    now_mono = time.monotonic()
    result: dict[str, dict[str, Any]] = {}
    missing: list[str] = []
    with _cache_lock:
        for player_id in sorted(player_ids):
            cached = _status_cache.get((server_family, player_id))
            if not force and cached and cached[0] > now_mono:
                result[player_id] = cached[1]
            else:
                missing.append(player_id)

    if not missing:
        return result

    url = _status_url()
    secret = os.getenv("FRONTLINE_VIP_REDEEM_SECRET", "")
    if not url or len(secret) < 32:
        logger.warning("VIP lifecycle status API is not configured; skipping messages")
        return result

    body = json.dumps(
        {"player_ids": missing, "server_family": server_family},
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    try:
        response = post(
            url,
            data=body,
            headers=_signed_headers(secret, body),
            timeout=10,
        )
        response.raise_for_status()
        payload = response.json()
    except (requests.RequestException, ValueError, AttributeError):
        logger.exception("VIP lifecycle status API request failed; skipping messages")
        return result

    if not isinstance(payload, dict) or payload.get("success") is not True:
        logger.error("VIP lifecycle status API returned an invalid response")
        return result
    if payload.get("server_family") != server_family:
        logger.error("VIP lifecycle status API returned the wrong server family")
        return result

    rows = payload.get("players")
    if not isinstance(rows, list):
        return result
    allowed = set(missing)
    validated: dict[str, dict[str, Any]] = {}
    for raw in rows:
        player_id = raw.get("player_id") if isinstance(raw, dict) else None
        if not isinstance(player_id, str) or player_id not in allowed:
            continue
        status = _validate_status(raw, player_id=player_id, server_family=server_family)
        if status is not None:
            validated[player_id] = status

    expires_mono = now_mono + cache_seconds
    with _cache_lock:
        for player_id, status in validated.items():
            _status_cache[(server_family, player_id)] = (expires_mono, status)
            result[player_id] = status
    return result


def clear_status_cache() -> None:
    with _cache_lock:
        _status_cache.clear()


def _online_players(ctl) -> dict[str, str]:
    return {player_id: name for name, player_id in ctl.get_player_ids() if player_id}


def _blocked_player_ids(player_ids: set[str], server_number: int) -> set[str]:
    if not player_ids:
        return set()
    now = utc_now()
    with enter_session() as sess:
        rows = (
            sess.query(PlayerID.player_id, Blacklist)
            .join(BlacklistRecord, BlacklistRecord.player_id_id == PlayerID.id)
            .join(Blacklist, Blacklist.id == BlacklistRecord.blacklist_id)
            .filter(
                PlayerID.player_id.in_(player_ids),
                or_(
                    BlacklistRecord.expires_at.is_(None),
                    BlacklistRecord.expires_at > now,
                ),
            )
            .all()
        )
        return {
            player_id
            for player_id, blacklist in rows
            if blacklist.servers is None
            or server_number in blacklist.get_server_numbers()
        }


def _campaign_for_rule(
    config: VipLifecycleConfig, rule: str
) -> VipLifecycleCampaign:
    return getattr(config.campaigns, rule)


def _active_sessions(
    player_ids: set[str], server_number: int
) -> dict[str, dict[str, Any]]:
    """Return the newest active CRCON session for each online player."""

    if not player_ids:
        return {}
    with enter_session() as sess:
        rows = latest_open_sessions(sess, player_ids, server_number)
        result: dict[str, dict[str, Any]] = {}
        for player, player_session in sorted(
            rows, key=lambda row: PlayerID._session_order_key(row[1]), reverse=True
        ):
            result.setdefault(
                player.player_id,
                {
                    "player_db_id": player.id,
                    "session_id": player_session.id,
                    "start_us": player_session.start_event_us,
                    "server_number": server_number,
                    "start": (
                        datetime.fromtimestamp(
                            player_session.start_event_us / 1_000_000, timezone.utc
                        )
                        if player_session.start_event_us is not None
                        # Legacy start is local wall time without a timezone;
                        # UTC creation is the conservative known boundary.
                        else player_session.created
                    ),
                },
            )
        return result


def _audience_sessions(statuses, server_number, config):
    result = _active_sessions(set(statuses), server_number)
    with enter_session() as sess:
        ids = [row["player_db_id"] for row in result.values()]
        attempts = _family_attempts(sess, ids, config)
        invitation = LifecycleDecision(RULE_UNVERIFIED, "invitation")
        candidates = {pid: row for pid, row in result.items()
                      if statuses.get(pid, {}).get("verified") is False
                      and not _already_attempted(attempts, row["player_db_id"], invitation, config.test_mode)}
        returning = _returning_players(sess, candidates, config.server_family) if config.campaigns.unverified.enabled else set()
        for row in result.values():
            row["returning"] = row["player_db_id"] in returning
            row["attempts"] = attempts
        return result


def _session_is_eligible(
    campaign: VipLifecycleCampaign,
    session_start: datetime | None,
    now: datetime,
) -> bool:
    if session_start is None:
        return False
    return _as_utc(now) >= _as_utc(session_start) + timedelta(
        minutes=campaign.min_session_minutes
    )


def _latest_timestamp(*values: datetime | None) -> datetime | None:
    normalized = [_as_utc(value) for value in values if value is not None]
    return max(normalized) if normalized else None


def _interval_is_due(
    last_event: datetime | None,
    interval_seconds: int,
    now: datetime,
) -> bool:
    return last_event is None or _as_utc(now) >= _as_utc(last_event) + timedelta(
        seconds=interval_seconds
    )


VISIT_BREAK_US = 30 * 60 * 1_000_000


def _returning_players(sess, sessions, family):
    """A new visit begins after 30 minutes off all servers in this family."""
    if not sessions:
        return set()
    game = GameIntEnum.HLL_VIETNAM if family == "hll_vietnam" else GameIntEnum.HLL_WW2
    starts = {row["player_db_id"]: row["start_us"] for row in sessions.values()
              if row["start_us"] is not None}
    if not starts:
        return set()
    # Server numbers can be reused for another game. Match the recorded
    # connection, including its player and game, before counting past visits.
    recorded = sess.query(LogLine.id).filter(
        LogLine.server == cast(PlayerSession.server_number, String),
        LogLine.event_time == PlayerSession.start,
        LogLine.player1_player_id == PlayerSession.player_id_id,
        LogLine.type == "CONNECTED", LogLine.game == game.value,
    ).exists()
    rows = (sess.query(PlayerSession.player_id_id, PlayerSession.start_event_us,
                       PlayerSession.end_event_us, PlayerSession.server_number)
            .filter(PlayerSession.player_id_id.in_(starts), PlayerSession.start_event_us.isnot(None),
                    PlayerSession.start_event_us <= max(starts.values()), recorded)
            .order_by(PlayerSession.player_id_id, PlayerSession.start_event_us, PlayerSession.id))
    intervals = {}
    for pid, start, end, server in rows:
        if start <= starts[pid]:
            intervals.setdefault(pid, []).append((start, end, server))
    returning = set()
    for row in sessions.values():
        pid = row["player_db_id"]
        if pid not in starts:
            continue
        history = intervals.get(pid, [])
        # The live session can precede persistence of its CONNECTED log.
        history.append((starts[pid], None, row["server_number"]))
        last_end = None
        open_servers = set()
        for start, end, server in history:
            if not open_servers and last_end is not None and start - last_end >= VISIT_BREAK_US:
                returning.add(pid)
                break
            # A later connection on the same server supersedes an unclosed one,
            # but cannot by itself prove that the player had been offline.
            open_servers.discard(server)
            if end is None or end < start:
                open_servers.add(server)
            else:
                last_end = max(last_end or end, end)
    return returning


def _family_attempts(sess, player_ids, config):
    if not player_ids:
        return {}
    rows = (sess.query(VipLifecycleDelivery.player_id_id, VipLifecycleDelivery.rule,
                       VipLifecycleDelivery.status_fingerprint)
            .filter(VipLifecycleDelivery.player_id_id.in_(player_ids),
                    VipLifecycleDelivery.server_family == config.server_family,
                    VipLifecycleDelivery.test_mode.is_(config.test_mode),
                    VipLifecycleDelivery.status != "test"))
    attempts = {}
    for pid, rule, fingerprint in rows:
        attempts.setdefault((pid, rule), set()).add(fingerprint)
    return attempts


def _already_attempted(attempts, pid, decision, test_mode):
    rules = ((RULE_TRIAL_EXPIRING, RULE_TRIAL_EXPIRED)
             if decision.rule in (RULE_TRIAL_EXPIRING, RULE_TRIAL_EXPIRED) else (decision.rule,))
    current = _delivery_key(decision, test_mode)
    for rule in rules:
        for prior in attempts.get((pid, rule), ()):
            # Old session-based entries and unidentified one-time trials have
            # no reliable grant identity. Suppress a possible repeat.
            if (prior == current or not prior.startswith("v2:") or prior.endswith(":single")
                    or decision.status_fingerprint == "single"):
                return True
    return False


def _delivery_key(decision, test_mode):
    return f"v2:{'test' if test_mode else 'live'}:{decision.status_fingerprint}"


def _prepare_delivery(
    *,
    player_db_id: int,
    player_session_id: int,
    player_name: str,
    decision: LifecycleDecision,
    campaign: VipLifecycleCampaign,
    config: VipLifecycleConfig,
    server_number: int,
    player_message_interval_sec: int,
    player_message_gap_sec: int,
    now: datetime,
) -> int | None:
    with enter_session() as sess:
        # Serialize claims across servers and the two expiry notice rules.
        sess.query(PlayerID.id).filter(PlayerID.id == player_db_id).with_for_update().one()
        if _already_attempted(_family_attempts(sess, [player_db_id], config), player_db_id, decision, config.test_mode):
            return None
        existing = (
            sess.query(VipLifecycleDelivery)
            .filter(
                VipLifecycleDelivery.server_number == server_number,
                VipLifecycleDelivery.rule == decision.rule,
                VipLifecycleDelivery.player_session_id == player_session_id,
                VipLifecycleDelivery.test_mode.is_(config.test_mode),
            )
            .one_or_none()
        )
        if existing is not None:
            # Keep compatibility with the historical unique session constraint.
            return None

        if not config.test_mode:
            latest_direct_attempt = (
                sess.query(func.max(CampaignDelivery.last_attempt_at))
                .filter(CampaignDelivery.server_number == server_number)
                .scalar()
            )
            latest_lifecycle_attempt = (
                sess.query(func.max(VipLifecycleDelivery.last_attempt_at))
                .filter(
                    VipLifecycleDelivery.server_number == server_number,
                    VipLifecycleDelivery.test_mode.is_(False),
                )
                .scalar()
            )
            if not _interval_is_due(
                _latest_timestamp(latest_direct_attempt, latest_lifecycle_attempt),
                player_message_interval_sec,
                now,
            ):
                return None

            latest_direct_send = (
                sess.query(func.max(CampaignDelivery.sent_at))
                .filter(
                    CampaignDelivery.server_number == server_number,
                    CampaignDelivery.player_session_id == player_session_id,
                    CampaignDelivery.status == "sent",
                )
                .scalar()
            )
            latest_family_contact = (
                sess.query(func.max(func.coalesce(VipLifecycleDelivery.sent_at, VipLifecycleDelivery.last_attempt_at)))
                .filter(
                    VipLifecycleDelivery.server_family == config.server_family,
                    VipLifecycleDelivery.player_id_id == player_db_id,
                    VipLifecycleDelivery.test_mode.is_(False),
                )
                .scalar()
            )
            if not _interval_is_due(
                _latest_timestamp(latest_direct_send, latest_family_contact),
                player_message_gap_sec,
                now,
            ):
                return None

        delivery = VipLifecycleDelivery(
            server_number=server_number,
            server_family=config.server_family,
            rule=decision.rule,
            player_id_id=player_db_id,
            player_session_id=player_session_id,
            player_name=player_name,
            status_fingerprint=_delivery_key(decision, config.test_mode),
            message=campaign.message.strip(),
            status="sending",
            attempt_count=1,
            test_mode=config.test_mode,
            status_checked_at=now,
            created_at=now,
            updated_at=now,
            last_attempt_at=None if config.test_mode else now,
        )
        sess.add(delivery)
        sess.flush()
        return delivery.id


def _finish_delivery(
    delivery_id: int,
    *,
    status: str,
    now: datetime,
    error: str | None = None,
) -> None:
    with enter_session() as sess:
        delivery = sess.get(VipLifecycleDelivery, delivery_id)
        if delivery is None:
            return
        delivery.status = status
        delivery.updated_at = now
        delivery.sent_at = now if status in {"sent", "simulated", "test"} else None
        delivery.last_error = error


def _eligible_this_visit(player_session, decision, config):
    return ((decision.rule != RULE_UNVERIFIED or player_session["returning"])
            and not _already_attempted(player_session["attempts"], player_session["player_db_id"],
                                       decision, config.test_mode))


def process_once(
    ctl,
    config: VipLifecycleConfig,
    *,
    player_message_interval_sec: int = 10,
    player_message_gap_sec: int = 300,
    now: datetime | None = None,
) -> dict[str, int]:
    """Evaluate one batch and deliver at most one lifecycle message."""

    counters = {"online": 0, "eligible": 0, "sent": 0, "simulated": 0}
    if (
        not feature_enabled()
        or not config.enabled
        or config.server_family != _local_server_family()
    ):
        return counters

    now = _as_utc(now or utc_now())
    server_number = int(get_server_number())
    players = _online_players(ctl)
    counters["online"] = len(players)
    blocked = _blocked_player_ids(set(players), server_number)
    candidate_ids = set(players) - blocked
    statuses = fetch_statuses(
        candidate_ids,
        server_family=config.server_family,
        cache_seconds=config.status_cache_seconds,
    )
    active_sessions = _audience_sessions(statuses, server_number, config)
    seeding_config = (
        AutoModSeedingUserConfig.load_from_db()
        if any(
            _campaign_for_rule(config, rule).pause_during_seeding
            for rule in RULES
        )
        else None
    )
    player_count = len(players)

    for player_id in sorted(candidate_ids):
        status = statuses.get(player_id)
        player_session = active_sessions.get(player_id)
        if status is None or player_session is None:
            continue
        decision = classify_status(
            status,
            now=now,
            expiry_window_hours=config.expiry_window_hours,
        )
        if decision is None or not _eligible_this_visit(player_session, decision, config):
            continue
        campaign = _campaign_for_rule(config, decision.rule)
        if not campaign.message.strip():
            continue
        if not campaign_is_eligible(campaign, player_count, seeding_config):
            continue
        if not _session_is_eligible(campaign, player_session["start"], now):
            continue
        counters["eligible"] += 1
        delivery_id = _prepare_delivery(
            player_db_id=player_session["player_db_id"],
            player_session_id=player_session["session_id"],
            player_name=players[player_id],
            decision=decision,
            campaign=campaign,
            config=config,
            server_number=server_number,
            player_message_interval_sec=player_message_interval_sec,
            player_message_gap_sec=player_message_gap_sec,
            now=now,
        )
        if delivery_id is None:
            continue
        if config.test_mode:
            _finish_delivery(delivery_id, status="simulated", now=now)
            counters["simulated"] += 1
            return counters
        try:
            formatted = format_message(
                ctl,
                campaign.message.strip(),
                player_id=player_id,
                context={"player_id": player_id, "player_name": players[player_id]},
            )
            accepted = ctl.message_player_info(
                player_id,
                formatted,
                by=f"VIP lifecycle: {decision.rule}",
                player_name=players[player_id],
            )
            if not accepted:
                raise RuntimeError("RCON rejected the player message")
        except Exception as exc:
            logger.exception("VIP lifecycle message failed for %s", player_id)
            _finish_delivery(
                delivery_id,
                status="failed",
                now=utc_now(),
                error=str(exc),
            )
        else:
            _finish_delivery(delivery_id, status="sent", now=utc_now())
            counters["sent"] += 1
        return counters
    return counters


def preview(ctl, config: VipLifecycleConfig) -> dict[str, Any]:
    require_feature_enabled()
    players = _online_players(ctl)
    server_number = int(get_server_number())
    family_matches = config.server_family == _local_server_family()
    if not family_matches:
        return {
            "available": True,
            "family_matches": False,
            "players": [],
            "server_family": config.server_family,
        }
    blocked = _blocked_player_ids(set(players), server_number)
    statuses = fetch_statuses(
        set(players) - blocked,
        server_family=config.server_family,
        cache_seconds=config.status_cache_seconds,
        force=True,
    )
    now = utc_now()
    active_sessions = _audience_sessions(statuses, server_number, config)
    seeding_config = (
        AutoModSeedingUserConfig.load_from_db()
        if any(
            _campaign_for_rule(config, rule).pause_during_seeding
            for rule in RULES
        )
        else None
    )
    rows = []
    for player_id, player_name in players.items():
        status = statuses.get(player_id)
        decision = (
            classify_status(
                status,
                now=now,
                expiry_window_hours=config.expiry_window_hours,
            )
            if status
            else None
        )
        player_session = active_sessions.get(player_id)
        campaign = (
            _campaign_for_rule(config, decision.rule) if decision else None
        )
        eligible = bool(
            decision
            and campaign
            and player_session
            and _eligible_this_visit(player_session, decision, config)
            and campaign.message.strip()
            and campaign_is_eligible(campaign, len(players), seeding_config)
            and _session_is_eligible(campaign, player_session["start"], now)
        )
        rows.append(
            {
                "player_id": player_id,
                "player_name": player_name,
                "blocked": player_id in blocked,
                "status_known": status is not None,
                "matched_rule": decision.rule if decision else None,
                "rule": decision.rule if eligible else None,
                "eligible": eligible,
                "session_started_at": (
                    player_session["start"] if player_session else None
                ),
                "verified": status.get("verified") if status else None,
                "vip_active": status.get("vip_active") if status else None,
                "grant_source": status.get("grant_source") if status else None,
                "expires_at": status.get("expires_at") if status else None,
                "has_purchased_vip": (
                    status.get("has_purchased_vip") if status else None
                ),
            }
        )
    return {
        "available": bool(statuses) or not players,
        "family_matches": True,
        "players": rows,
        "server_family": config.server_family,
    }


def delivery_status(limit: int = 50) -> dict[str, Any]:
    if not feature_enabled():
        return {
            "available": False,
            "generated_at": utc_now(),
            "deliveries": [],
        }
    limit = max(1, min(int(limit), 200))
    server_number = int(get_server_number())
    with enter_session() as sess:
        deliveries = (
            sess.query(VipLifecycleDelivery, PlayerID.player_id)
            .join(PlayerID, PlayerID.id == VipLifecycleDelivery.player_id_id)
            .filter(VipLifecycleDelivery.server_number == server_number)
            .order_by(VipLifecycleDelivery.updated_at.desc())
            .limit(limit)
            .all()
        )
        rows = [
            {
                "id": delivery.id,
                "player_id": player_id,
                "player_name": delivery.player_name,
                "server_family": delivery.server_family,
                "rule": delivery.rule,
                "status": delivery.status,
                "attempt_count": delivery.attempt_count,
                "test_mode": delivery.test_mode,
                "player_session_id": delivery.player_session_id,
                "status_checked_at": delivery.status_checked_at,
                "updated_at": delivery.updated_at,
                "sent_at": delivery.sent_at,
                "last_error": delivery.last_error,
            }
            for delivery, player_id in deliveries
        ]
    return {
        "available": True,
        "generated_at": utc_now(),
        "deliveries": rows,
    }


def send_test_message(
    ctl,
    config: VipLifecycleConfig,
    *,
    player_id: str,
    rule: str,
) -> str:
    require_feature_enabled()
    if rule not in RULES:
        raise ValueError("Unknown VIP lifecycle rule")
    players = _online_players(ctl)
    if player_id not in players:
        raise ValueError("The selected player is no longer online")
    if player_id in _blocked_player_ids({player_id}, int(get_server_number())):
        raise ValueError("Messages cannot be sent to a blocked player")
    message = _campaign_for_rule(config, rule).message.strip()
    if not message:
        raise ValueError("The selected VIP lifecycle message is empty")
    formatted = format_message(
        ctl,
        message,
        player_id=player_id,
        context={"player_id": player_id, "player_name": players[player_id]},
    )
    accepted = ctl.message_player_info(
        player_id,
        formatted,
        by=f"VIP lifecycle test: {rule}",
        player_name=players[player_id],
    )
    if not accepted:
        raise RuntimeError("RCON rejected the player message")

    now = utc_now()
    with enter_session() as sess:
        player = sess.query(PlayerID).filter(PlayerID.player_id == player_id).one()
        sess.add(
            VipLifecycleDelivery(
                server_number=int(get_server_number()),
                server_family=config.server_family,
                rule=rule,
                player_id_id=player.id,
                # Manual tests use no session id so they neither consume nor
                # collide with the automatic once-per-session claim.
                player_session_id=None,
                player_name=players[player_id],
                status_fingerprint=hashlib.sha256(
                    f"manual|{uuid.uuid4()}".encode()
                ).hexdigest(),
                message=message,
                status="test",
                attempt_count=1,
                test_mode=True,
                status_checked_at=now,
                created_at=now,
                updated_at=now,
                last_attempt_at=now,
                sent_at=now,
            )
        )
    return formatted
