import logging
import threading
import time
from datetime import datetime, timedelta, timezone
from typing import List, Optional

from pydantic import HttpUrl

from rcon.discord import send_to_discord_audit
from rcon.models import PlayerID, PlayerVIP, enter_session
from rcon.rcon import Rcon, get_rcon
from rcon.types import GameEnum
from rcon.user_config.expired_vips import ExpiredVipsUserConfig
from rcon.utils import INDEFINITE_VIP_DATE, get_server_number

SERVICE_NAME = "ExpiringVIPs"
VIP_RECONCILE_INTERVAL_SECONDS = 60
logger = logging.getLogger(__name__)


def restore_missing_vips(rcon_hook: Rcon) -> int:
    """Restore active database VIPs missing from the game server.

    HLL Vietnam currently loses its in-memory VIP list when the game process
    restarts.  CRCON's database remains the source of truth, so reconciliation
    is additive: it restores active records but never removes VIPs that were
    added directly on the game server.
    """

    server_number = get_server_number()
    now = datetime.now(timezone.utc)
    # A game-process restart happens outside CRCON, so the shared five-minute
    # VIP cache may still contain the pre-restart list.  Force a live read for
    # reconciliation instead of waiting for that stale cache to expire.
    rcon_hook.get_vip_ids.cache_clear()
    live_vip_ids = {vip["player_id"] for vip in rcon_hook.get_vip_ids()}

    with enter_session() as session:
        active_vips = (
            session.query(PlayerVIP)
            .filter(
                PlayerVIP.server_number == server_number,
                PlayerVIP.expiration >= now,
            )
            .all()
        )
        missing_vips = []
        for vip in active_vips:
            player_id = vip.player.player_id
            if player_id in live_vip_ids:
                continue
            try:
                description = vip.player.names[0].name
            except IndexError:
                description = "Restored CRCON VIP"
            missing_vips.append((player_id, description, vip.expiration.isoformat()))

    restored = 0
    for player_id, description, expiration in missing_vips:
        try:
            rcon_hook.add_vip(
                player_id=player_id,
                description=description,
                expiration=expiration,
            )
            restored += 1
        except Exception:
            logger.exception("Unable to restore VIP %s", player_id)

    if restored:
        logger.warning(
            "Restored %s active VIP(s) missing from the game server", restored
        )
    return restored


def remove_expired_vips(rcon_hook: Rcon, webhook_url: Optional[HttpUrl] = None):
    logger.info(f"Checking for expired VIPs")

    count = 0
    server_number = get_server_number()
    with enter_session() as session:
        expired_vips: List[PlayerVIP] = (
            session.query(PlayerVIP)
            .filter(
                PlayerVIP.server_number == server_number,
                PlayerVIP.expiration < datetime.utcnow(),
            )
            .all()
        )

        count = len(expired_vips)
        for vip in expired_vips:
            name: str
            try:
                name = vip.player.names[0].name
            except IndexError:
                name = "No name found"
            message = f"Removing VIP from `{name}`/`{vip.player.player_id}` expired `{vip.expiration}`"
            logger.info(message)

            webhookurls: list[HttpUrl | None] | None
            if webhook_url is None:
                webhookurls = None
            else:
                webhookurls = [webhook_url]
            send_to_discord_audit(
                message=message,
                command_name="remove_vip",
                by=SERVICE_NAME,
                webhookurls=webhookurls,
            )
            rcon_hook.remove_vip(vip.player.player_id)

        # Look for anyone with VIP but without a record and create one for them
        vip_ids = rcon_hook.get_vip_ids()
        missing_expiration_records = []
        for player in vip_ids:
            player_expiration: datetime | None = player["vip_expiration"]
            if player_expiration is None:
                missing_expiration_records.append(player)
            # Find any old style records that had a floating creation date + 200 year expiration
            # so they get changed to the new fixed UTC 3000-01-01 datetime
            elif (
                player_expiration
                and player_expiration
                >= datetime.now(timezone.utc) + timedelta(days=365 * 100)
                and player_expiration.year < 3000
            ):
                missing_expiration_records.append(player)
                logger.info(
                    "Correcting old style expiration date for %s", player["player_id"]
                )

        for raw_player in missing_expiration_records:
            player: PlayerID = (
                session.query(PlayerID)
                .filter(PlayerID.player_id == raw_player["player_id"])
                .one_or_none()
            )

            if player:
                expiration_date = INDEFINITE_VIP_DATE
                vip_record = (
                    session.query(PlayerVIP)
                    .filter(
                        PlayerVIP.player_id_id == player.id,
                        PlayerVIP.server_number == get_server_number(),
                    )
                    .one_or_none()
                )

                if vip_record:
                    vip_record.expiration = expiration_date
                else:
                    vip_record = PlayerVIP(
                        expiration=expiration_date,
                        player_id_id=player.id,
                        server_number=server_number,
                    )
                    session.add(vip_record)

                try:
                    name = player.names[0].name
                except IndexError:
                    name = "No name found"

                logger.info(
                    f"Creating missing VIP expiration (indefinite) record for {name} / {player.player_id}"
                )
            else:
                logger.info(
                    f"{raw_player['player_id']} has VIP on the server but does not have a PlayerSteamID record."
                )

    if count > 0:
        logger.info(f"Removed VIP from {count} player(s)")
    else:
        logger.info("No expired VIPs found")


def run(stop_event: threading.Event | None = None):
    stop_event = stop_event or threading.Event()
    rcon_hook = get_rcon()
    next_expiration_check = 0.0

    while not stop_event.is_set():
        config = ExpiredVipsUserConfig.load_from_db()
        now = time.monotonic()

        if config.enabled and now >= next_expiration_check:
            try:
                remove_expired_vips(rcon_hook, config.discord_webhook_url)
            except Exception:
                logger.exception("Unable to process expired VIPs")
            next_expiration_check = now + config.interval_minutes * 60

        if rcon_hook.config.game == GameEnum.HLL_VIETNAM:
            try:
                restore_missing_vips(rcon_hook)
            except Exception:
                logger.exception("Unable to reconcile Vietnam VIPs")

        stop_event.wait(VIP_RECONCILE_INTERVAL_SECONDS)


if __name__ == "__main__":
    run()
