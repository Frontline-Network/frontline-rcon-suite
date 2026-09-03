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
from sqlalchemy import func, or_

from rcon.broadcast import campaign_is_eligible, format_message
from rcon.models import (
    Blacklist,
    BlacklistRecord,
    CampaignDelivery,
    PlayerID,
    PlayerSession,
    VipLifecycleDelivery,
    enter_session,
)
from rcon.user_config.auto_broadcast import VipLifecycleCampaign, VipLifecycleConfig
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig
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
    payload = {
        "rule": rule,
        "server_family": status.get("server_family"),
        "verified": status.get("verified"),
        "vip_active": status.get("vip_active"),
        "grant_source": status.get("grant_source"),
        "expires_at": status.get("expires_at"),
        "has_purchased_vip": status.get("has_purchased_vip"),
        "status_version": status.get("status_version"),
    }
    encoded = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode()
    return hashlib.sha256(encoded).hexdigest()


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
    return {
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
        rows = (
            sess.query(PlayerID, PlayerSession)
            .join(PlayerSession, PlayerSession.player_id_id == PlayerID.id)
            .filter(
                PlayerID.player_id.in_(player_ids),
                PlayerSession.server_number == server_number,
                PlayerSession.end.is_(None),
            )
            .order_by(PlayerSession.created.desc())
            .all()
        )
        result: dict[str, dict[str, Any]] = {}
        for player, player_session in rows:
            result.setdefault(
                player.player_id,
                {
                    "player_db_id": player.id,
                    "session_id": player_session.id,
                    "start": player_session.start or player_session.created,
                },
            )
        return result


def _session_is_eligible(
    campaign: VipLifecycleCampaign,
    session_start: datetime,
    now: datetime,
) -> bool:
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


def _session_fingerprint(
    *, server_number: int, rule: str, player_session_id: int, test_mode: bool
) -> str:
    namespace = "test" if test_mode else "live"
    return hashlib.sha256(
        f"{namespace}|{server_number}|{rule}|{player_session_id}".encode()
    ).hexdigest()


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
            # The session claim is the dedupe boundary. Never retry it
            # automatically because RCON may have accepted a timed-out send.
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
            latest_lifecycle_send = (
                sess.query(func.max(VipLifecycleDelivery.sent_at))
                .filter(
                    VipLifecycleDelivery.server_number == server_number,
                    VipLifecycleDelivery.player_session_id == player_session_id,
                    VipLifecycleDelivery.status == "sent",
                    VipLifecycleDelivery.test_mode.is_(False),
                )
                .scalar()
            )
            if not _interval_is_due(
                _latest_timestamp(latest_direct_send, latest_lifecycle_send),
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
            status_fingerprint=_session_fingerprint(
                server_number=server_number,
                rule=decision.rule,
                player_session_id=player_session_id,
                test_mode=config.test_mode,
            ),
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
    active_sessions = _active_sessions(candidate_ids, server_number)
    statuses = fetch_statuses(
        candidate_ids,
        server_family=config.server_family,
        cache_seconds=config.status_cache_seconds,
    )
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
        if decision is None:
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
            accepted = ctl.message_player(
                player_id,
                formatted,
                by=f"VIP lifecycle: {decision.rule}",
                save_message=True,
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
    active_sessions = _active_sessions(set(players) - blocked, server_number)
    statuses = fetch_statuses(
        set(players) - blocked,
        server_family=config.server_family,
        cache_seconds=config.status_cache_seconds,
        force=True,
    )
    now = utc_now()
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
    accepted = ctl.message_player(
        player_id,
        formatted,
        by=f"VIP lifecycle test: {rule}",
        save_message=True,
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
