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
from sqlalchemy import or_

from rcon.broadcast import format_message
from rcon.models import (
    Blacklist,
    BlacklistRecord,
    PlayerID,
    VipLifecycleDelivery,
    enter_session,
)
from rcon.user_config.auto_broadcast import VipLifecycleConfig
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


def unverified_cooldown_elapsed(
    last_sent: datetime | None, *, cooldown_days: int, now: datetime
) -> bool:
    if last_sent is None:
        return True
    return _as_utc(now) >= _as_utc(last_sent) + timedelta(days=cooldown_days)


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


def _message_for_rule(config: VipLifecycleConfig, rule: str) -> str:
    return str(getattr(config.messages, rule, "") or "").strip()


def _unverified_fingerprint(
    sess,
    player_db_id: int,
    *,
    server_family: str,
    test_mode: bool,
) -> tuple[str, datetime | None]:
    latest = (
        sess.query(VipLifecycleDelivery)
        .filter(
            VipLifecycleDelivery.server_family == server_family,
            VipLifecycleDelivery.player_id_id == player_db_id,
            VipLifecycleDelivery.rule == RULE_UNVERIFIED,
            VipLifecycleDelivery.test_mode.is_(test_mode),
        )
        .order_by(VipLifecycleDelivery.created_at.desc())
        .first()
    )
    seed = f"after:{latest.id}" if latest else "initial"
    last_sent = _as_utc(latest.created_at) if latest else None
    digest = hashlib.sha256(
        f"{server_family}|{RULE_UNVERIFIED}|{test_mode}|{seed}".encode()
    ).hexdigest()
    return digest, last_sent


def _prepare_delivery(
    *,
    player_id: str,
    player_name: str,
    decision: LifecycleDecision,
    message: str,
    config: VipLifecycleConfig,
    server_number: int,
    now: datetime,
) -> int | None:
    with enter_session() as sess:
        player = (
            sess.query(PlayerID).filter(PlayerID.player_id == player_id).one_or_none()
        )
        if player is None:
            return None
        fingerprint = decision.status_fingerprint
        if decision.rule == RULE_UNVERIFIED:
            fingerprint, last_sent = _unverified_fingerprint(
                sess,
                player.id,
                server_family=config.server_family,
                test_mode=config.test_mode,
            )
            if not unverified_cooldown_elapsed(
                last_sent,
                cooldown_days=config.unverified_cooldown_days,
                now=now,
            ):
                return None

        # Test-mode simulations intentionally use a separate dedupe namespace.
        fingerprint = hashlib.sha256(
            f"{'test' if config.test_mode else 'live'}|{fingerprint}".encode()
        ).hexdigest()
        delivery = (
            sess.query(VipLifecycleDelivery)
            .filter(
                VipLifecycleDelivery.server_family == config.server_family,
                VipLifecycleDelivery.rule == decision.rule,
                VipLifecycleDelivery.player_id_id == player.id,
                VipLifecycleDelivery.status_fingerprint == fingerprint,
            )
            .one_or_none()
        )
        if delivery is not None:
            # The claim itself is the dedupe boundary. Never retry the same
            # state automatically: if the process dies after RCON accepted a
            # message but before the result update, a retry could duplicate it.
            return None
        else:
            delivery = VipLifecycleDelivery(
                server_number=server_number,
                server_family=config.server_family,
                rule=decision.rule,
                player_id_id=player.id,
                player_name=player_name,
                status_fingerprint=fingerprint,
                message=message,
                status="queued",
                attempt_count=0,
                test_mode=config.test_mode,
                status_checked_at=now,
                created_at=now,
                updated_at=now,
            )
            sess.add(delivery)
            sess.flush()
        delivery.status = "sending"
        delivery.attempt_count = 1
        delivery.updated_at = now
        delivery.status_checked_at = now
        delivery.player_name = player_name
        delivery.message = message
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

    for player_id in sorted(candidate_ids):
        status = statuses.get(player_id)
        if status is None:
            continue
        decision = classify_status(
            status,
            now=now,
            expiry_window_hours=config.expiry_window_hours,
        )
        if decision is None:
            continue
        message = _message_for_rule(config, decision.rule)
        if not message:
            continue
        counters["eligible"] += 1
        delivery_id = _prepare_delivery(
            player_id=player_id,
            player_name=players[player_id],
            decision=decision,
            message=message,
            config=config,
            server_number=server_number,
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
                message,
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
    statuses = fetch_statuses(
        set(players) - blocked,
        server_family=config.server_family,
        cache_seconds=config.status_cache_seconds,
        force=True,
    )
    now = utc_now()
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
        rows.append(
            {
                "player_id": player_id,
                "player_name": player_name,
                "blocked": player_id in blocked,
                "status_known": status is not None,
                "rule": decision.rule if decision else None,
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
    message = _message_for_rule(config, rule)
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
                sent_at=now,
            )
        )
    return formatted
