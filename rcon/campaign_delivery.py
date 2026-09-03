from __future__ import annotations

import logging
import time
from datetime import datetime, timedelta
from typing import Any

from sqlalchemy import func, or_, text

from rcon.broadcast import campaign_is_eligible, format_message
from rcon.models import (
    CampaignDelivery,
    PlayerID,
    PlayerSession,
    enter_session,
)
from rcon.user_config.auto_broadcast import (
    AutoBroadcastMessage,
    AutoBroadcastUserConfig,
)
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig
from rcon.utils import get_server_number

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 5
DELIVERY_RETENTION_DAYS = 30
MAX_ATTEMPTS = 3
RETRY_DELAYS = (30, 60)
STALE_SENDING_SECONDS = 120
CLAIM_LOCK_NAMESPACE = 824_000

QUEUED = "queued"
SENDING = "sending"
SENT = "sent"
FAILED = "failed"
EXPIRED = "expired"


def recipient_is_eligible(campaign: AutoBroadcastMessage, is_vip: bool) -> bool:
    if campaign.recipient_group == "vip":
        return is_vip
    if campaign.recipient_group == "non_vip":
        return not is_vip
    return True


def session_is_eligible(
    campaign: AutoBroadcastMessage,
    session_start: datetime,
    now: datetime,
) -> bool:
    return now >= session_start + timedelta(minutes=campaign.min_session_minutes)


def global_send_is_due(
    last_attempt: datetime | None,
    interval_seconds: int,
    now: datetime,
) -> bool:
    return last_attempt is None or now >= last_attempt + timedelta(
        seconds=interval_seconds
    )


def player_gap_is_due(
    last_delivery: datetime | None,
    gap_seconds: int,
    now: datetime,
) -> bool:
    return last_delivery is None or now >= last_delivery + timedelta(
        seconds=gap_seconds
    )


def _direct_campaigns(
    config: AutoBroadcastUserConfig,
) -> list[AutoBroadcastMessage]:
    return [
        campaign
        for campaign in config.messages
        if campaign.delivery_mode == "player_message" and campaign.enabled
    ]


def _all_direct_campaigns(
    config: AutoBroadcastUserConfig,
) -> list[AutoBroadcastMessage]:
    return [
        campaign
        for campaign in config.messages
        if campaign.delivery_mode == "player_message"
    ]


def _online_players(ctl) -> dict[str, dict[str, Any]]:
    players = {
        player_id: {"player_id": player_id, "player_name": name, "is_vip": False}
        for name, player_id in ctl.get_player_ids()
    }
    if not players:
        return players

    try:
        vip_ids = {item["player_id"] for item in ctl.get_vip_ids()}
    except Exception:
        logger.exception("Unable to load VIP ids for campaign targeting")
        vip_ids = set()

    for player_id, player in players.items():
        player["is_vip"] = player_id in vip_ids
    return players


def _active_sessions(
    player_ids: set[str], server_number: int
) -> dict[str, dict[str, Any]]:
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


def enqueue_eligible_deliveries(
    *,
    campaigns: list[AutoBroadcastMessage],
    online_players: dict[str, dict[str, Any]],
    active_sessions: dict[str, dict[str, Any]],
    server_number: int,
    player_count: int,
    seeding_config: AutoModSeedingUserConfig | None,
    now: datetime,
) -> int:
    candidates: list[tuple[AutoBroadcastMessage, dict[str, Any], dict[str, Any]]] = []
    for campaign in campaigns:
        if not campaign_is_eligible(campaign, player_count, seeding_config):
            continue
        for player_id, player in online_players.items():
            player_session = active_sessions.get(player_id)
            if player_session is None:
                continue
            if not recipient_is_eligible(campaign, bool(player["is_vip"])):
                continue
            if not session_is_eligible(campaign, player_session["start"], now):
                continue
            candidates.append((campaign, player, player_session))

    if not candidates:
        return 0

    keys = {
        (campaign.id, player_session["session_id"])
        for campaign, _, player_session in candidates
    }
    with enter_session() as sess:
        campaign_ids = {key[0] for key in keys}
        session_ids = {key[1] for key in keys}
        existing = {
            (row.campaign_id, row.player_session_id)
            for row in sess.query(CampaignDelivery).filter(
                CampaignDelivery.server_number == server_number,
                CampaignDelivery.campaign_id.in_(campaign_ids),
                CampaignDelivery.player_session_id.in_(session_ids),
            )
        }
        created = 0
        for campaign, player, player_session in candidates:
            key = (campaign.id, player_session["session_id"])
            if key in existing:
                continue
            eligible_at = player_session["start"] + timedelta(
                minutes=campaign.min_session_minutes
            )
            sess.add(
                CampaignDelivery(
                    server_number=server_number,
                    campaign_id=campaign.id,
                    player_id_id=player_session["player_db_id"],
                    player_session_id=player_session["session_id"],
                    player_name=player["player_name"],
                    message=campaign.message,
                    status=QUEUED,
                    attempt_count=0,
                    eligible_at=eligible_at,
                    next_attempt_at=eligible_at,
                    created_at=now,
                    updated_at=now,
                )
            )
            existing.add(key)
            created += 1
        return created


def _recover_interrupted_deliveries(server_number: int, now: datetime) -> None:
    cutoff = now - timedelta(seconds=STALE_SENDING_SECONDS)
    with enter_session() as sess:
        stale = sess.query(CampaignDelivery).filter(
            CampaignDelivery.server_number == server_number,
            CampaignDelivery.status == SENDING,
            CampaignDelivery.last_attempt_at < cutoff,
        )
        for delivery in stale:
            delivery.status = FAILED
            delivery.updated_at = now
            delivery.last_error = "Worker stopped during delivery; not retried to avoid a duplicate message"


def claim_next_delivery(
    *,
    config: AutoBroadcastUserConfig,
    campaigns: list[AutoBroadcastMessage],
    online_players: dict[str, dict[str, Any]],
    active_sessions: dict[str, dict[str, Any]],
    player_count: int,
    seeding_config: AutoModSeedingUserConfig | None,
    server_number: int,
    now: datetime,
) -> dict[str, Any] | None:
    campaign_by_id = {campaign.id: campaign for campaign in campaigns}
    active_session_ids = {player["session_id"] for player in active_sessions.values()}

    with enter_session() as sess:
        acquired = sess.execute(
            text("SELECT pg_try_advisory_xact_lock(:lock_key)"),
            {"lock_key": CLAIM_LOCK_NAMESPACE + server_number},
        ).scalar()
        if not acquired:
            return None
        last_attempt = (
            sess.query(func.max(CampaignDelivery.last_attempt_at))
            .filter(CampaignDelivery.server_number == server_number)
            .scalar()
        )
        if not global_send_is_due(
            last_attempt, config.player_message_interval_sec, now
        ):
            return None

        deliveries = (
            sess.query(CampaignDelivery)
            .filter(
                CampaignDelivery.server_number == server_number,
                CampaignDelivery.status == QUEUED,
                or_(
                    CampaignDelivery.next_attempt_at.is_(None),
                    CampaignDelivery.next_attempt_at <= now,
                ),
            )
            .order_by(CampaignDelivery.eligible_at, CampaignDelivery.id)
            .limit(500)
            .all()
        )

        for delivery in deliveries:
            campaign = campaign_by_id.get(delivery.campaign_id)
            if campaign is None or delivery.player_session_id not in active_session_ids:
                delivery.status = EXPIRED
                delivery.updated_at = now
                continue

            player_id = next(
                (
                    candidate_id
                    for candidate_id, player_session in active_sessions.items()
                    if player_session["session_id"] == delivery.player_session_id
                ),
                None,
            )
            player = online_players.get(player_id) if player_id else None
            player_session = active_sessions.get(player_id) if player_id else None
            if player is None or player_session is None:
                delivery.status = EXPIRED
                delivery.updated_at = now
                continue
            if not campaign_is_eligible(campaign, player_count, seeding_config):
                continue
            if not recipient_is_eligible(campaign, bool(player["is_vip"])):
                delivery.status = EXPIRED
                delivery.updated_at = now
                continue
            if not session_is_eligible(campaign, player_session["start"], now):
                continue

            previous_player_delivery = (
                sess.query(func.max(CampaignDelivery.sent_at))
                .filter(
                    CampaignDelivery.server_number == server_number,
                    CampaignDelivery.player_session_id == delivery.player_session_id,
                    CampaignDelivery.status == SENT,
                )
                .scalar()
            )
            if not player_gap_is_due(
                previous_player_delivery, config.player_message_gap_sec, now
            ):
                continue

            delivery.status = SENDING
            delivery.attempt_count += 1
            delivery.last_attempt_at = now
            delivery.updated_at = now
            delivery.message = campaign.message
            return {
                "id": delivery.id,
                "campaign_id": delivery.campaign_id,
                "campaign_title": campaign.title,
                "player_id": player_id,
                "player_name": player["player_name"],
                "message": delivery.message,
                "attempt_count": delivery.attempt_count,
            }
    return None


def finish_delivery(
    delivery_id: int,
    *,
    success: bool,
    now: datetime,
    error: str | None = None,
) -> None:
    with enter_session() as sess:
        delivery = sess.get(CampaignDelivery, delivery_id)
        if delivery is None:
            logger.error("Campaign delivery %s disappeared while sending", delivery_id)
            return
        delivery.updated_at = now
        if success:
            delivery.status = SENT
            delivery.sent_at = now
            delivery.next_attempt_at = None
            delivery.last_error = None
            return

        delivery.last_error = (error or "Unknown RCON failure")[:4000]
        if delivery.attempt_count >= MAX_ATTEMPTS:
            delivery.status = FAILED
            delivery.next_attempt_at = None
        else:
            delivery.status = QUEUED
            retry_index = min(delivery.attempt_count - 1, len(RETRY_DELAYS) - 1)
            delivery.next_attempt_at = now + timedelta(
                seconds=RETRY_DELAYS[retry_index]
            )


def expire_old_deliveries(server_number: int, now: datetime) -> int:
    cutoff = now - timedelta(days=DELIVERY_RETENTION_DAYS)
    with enter_session() as sess:
        return (
            sess.query(CampaignDelivery)
            .filter(
                CampaignDelivery.server_number == server_number,
                CampaignDelivery.created_at < cutoff,
                CampaignDelivery.status.in_([SENT, FAILED, EXPIRED]),
            )
            .delete(synchronize_session=False)
        )


def get_delivery_status(limit: int = 20) -> dict[str, Any]:
    now = datetime.utcnow()
    cutoff = now - timedelta(hours=24)
    server_number = int(get_server_number())
    config = AutoBroadcastUserConfig.load_from_db()
    campaigns = _all_direct_campaigns(config)

    result = []
    with enter_session() as sess:
        for campaign in campaigns:
            base = sess.query(CampaignDelivery).filter(
                CampaignDelivery.server_number == server_number,
                CampaignDelivery.campaign_id == campaign.id,
            )
            pending = base.filter(
                CampaignDelivery.status.in_([QUEUED, SENDING])
            ).count()
            sent_24h = base.filter(
                CampaignDelivery.status == SENT,
                CampaignDelivery.sent_at >= cutoff,
            ).count()
            failed_24h = base.filter(
                CampaignDelivery.status == FAILED,
                CampaignDelivery.updated_at >= cutoff,
            ).count()
            last_sent_at = base.with_entities(
                func.max(CampaignDelivery.sent_at)
            ).scalar()
            recent_rows = (
                base.order_by(CampaignDelivery.updated_at.desc())
                .limit(max(1, min(int(limit), 100)))
                .all()
            )
            result.append(
                {
                    "campaign_id": campaign.id,
                    "title": campaign.title,
                    "pending": pending,
                    "sent_24h": sent_24h,
                    "failed_24h": failed_24h,
                    "last_sent_at": last_sent_at,
                    "recent": [
                        {
                            "id": row.id,
                            "player_name": row.player_name,
                            "status": row.status,
                            "attempt_count": row.attempt_count,
                            "updated_at": row.updated_at,
                            "sent_at": row.sent_at,
                            "last_error": row.last_error,
                        }
                        for row in recent_rows
                    ],
                }
            )
    return {"generated_at": now, "campaigns": result}


def send_test_message(ctl, campaign: AutoBroadcastMessage, player_id: str) -> str:
    if campaign.delivery_mode != "player_message":
        raise ValueError("Only player-message campaigns can use this test endpoint")
    online = ctl.get_player_ids()
    player_name = next(
        (name for name, candidate_id in online if candidate_id == player_id),
        None,
    )
    if player_name is None:
        raise ValueError("The selected player is no longer online")
    formatted = format_message(
        ctl,
        campaign.message,
        player_id=player_id,
        context={"player_id": player_id, "player_name": player_name},
    )
    ctl.message_player(
        player_id, formatted, save_message=False, player_name=player_name
    )
    return formatted


def run() -> None:
    from rcon.rcon import get_rcon
    from rcon.vip_lifecycle import (
        feature_enabled as vip_lifecycle_feature_enabled,
    )
    from rcon.vip_lifecycle import process_once as process_vip_lifecycle

    ctl = get_rcon()
    server_number = int(get_server_number())
    last_cleanup = datetime.min
    _recover_interrupted_deliveries(server_number, datetime.utcnow())

    while True:
        now = datetime.utcnow()
        try:
            if now - last_cleanup >= timedelta(days=1):
                expire_old_deliveries(server_number, now)
                last_cleanup = now

            config = AutoBroadcastUserConfig.load_from_db()
            all_campaigns = _all_direct_campaigns(config)
            campaigns = _direct_campaigns(config)
            direct_enabled = config.enabled and bool(campaigns)
            lifecycle_enabled = (
                vip_lifecycle_feature_enabled() and config.vip_lifecycle.enabled
            )
            if not direct_enabled and not lifecycle_enabled:
                time.sleep(CHECK_INTERVAL)
                continue

            delivery = None
            if direct_enabled:
                online_players = _online_players(ctl)
                active_sessions = _active_sessions(set(online_players), server_number)
                player_count = len(online_players)
                seeding_config = (
                    AutoModSeedingUserConfig.load_from_db()
                    if any(campaign.pause_during_seeding for campaign in campaigns)
                    else None
                )
                enqueue_eligible_deliveries(
                    campaigns=campaigns,
                    online_players=online_players,
                    active_sessions=active_sessions,
                    server_number=server_number,
                    player_count=player_count,
                    seeding_config=seeding_config,
                    now=now,
                )
                delivery = claim_next_delivery(
                    config=config,
                    campaigns=all_campaigns,
                    online_players=online_players,
                    active_sessions=active_sessions,
                    player_count=player_count,
                    seeding_config=seeding_config,
                    server_number=server_number,
                    now=now,
                )
            if delivery:
                try:
                    formatted = format_message(
                        ctl,
                        delivery["message"],
                        player_id=delivery["player_id"],
                        context={
                            "player_id": delivery["player_id"],
                            "player_name": delivery["player_name"],
                        },
                    )
                    success = ctl.message_player(
                        delivery["player_id"],
                        formatted,
                        by=f"Campaign: {delivery['campaign_title'] or delivery['campaign_id']}",
                        save_message=True,
                        player_name=delivery["player_name"],
                    )
                    if not success:
                        raise RuntimeError("RCON rejected the player message")
                except Exception as exc:
                    logger.exception(
                        "Unable to deliver campaign %s to %s",
                        delivery["campaign_id"],
                        delivery["player_id"],
                    )
                    finish_delivery(
                        delivery["id"],
                        success=False,
                        now=datetime.utcnow(),
                        error=str(exc),
                    )
                else:
                    finish_delivery(delivery["id"], success=True, now=datetime.utcnow())
            elif lifecycle_enabled:
                # Keep lifecycle traffic behind already queued direct campaigns so
                # a player never receives two campaign messages in one cycle.
                process_vip_lifecycle(ctl, config.vip_lifecycle)

        except Exception:
            logger.exception("Campaign player-message loop failed")
        time.sleep(CHECK_INTERVAL)
