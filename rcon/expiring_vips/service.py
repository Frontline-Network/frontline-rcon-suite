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


def _resolve_expired_vip(rcon_hook: Rcon, player_id: str, expected_expiration: datetime) -> str:
    """Remove a confirmed expired VIP or its orphaned record under the VIP lock."""
    from rcon.vip_rewards.locking import vip_lock
    from rcon.vip_rewards.service import current_vip, expiration

    with vip_lock(player_id):
        current = current_vip(rcon_hook, player_id)
        if current is not None:
            return "removed" if rcon_hook.remove_vip(player_id, expected_expiration=expected_expiration) is True else "changed"
        with enter_session() as session:
            record = (session.query(PlayerVIP).join(PlayerID, PlayerVIP.player_id_id == PlayerID.id)
                      .filter(PlayerVIP.server_number == get_server_number(), PlayerID.player_id == player_id)
                      .with_for_update().one_or_none())
            if record is None:
                return "already_clean"
            # The initial scan and live lookup may be separated by an extension.
            # Recheck under the row lock before deleting anything locally.
            if (expiration(record.expiration) != expiration(expected_expiration)
                    or expiration(record.expiration) >= datetime.now(timezone.utc)):
                return "changed"
            session.delete(record)
        return "orphan_cleaned"


def restore_missing_vips(rcon_hook: Rcon) -> int:
    """Restore active database VIPs missing from the game server.

    HLL Vietnam currently loses its in-memory VIP list when the game process
    restarts.  CRCON's database remains the source of truth, so reconciliation
    is additive: it restores active records but never removes VIPs that were
    added directly on the game server.
    """

    from rcon.automods import action_guard
    from rcon.vip_rewards.locking import vip_lock
    from rcon.vip_rewards.service import expiration as normalize_expiration

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
            missing_vips.append(player_id)

    restored = 0
    for player_id in missing_vips:
        try:
            # The initial scan is only a hint. A revoke or extension may have
            # happened since then; serialize with the regular VIP operations
            # and re-read both sources before issuing any game-server command.
            with vip_lock(player_id):
                with enter_session() as session:
                    vip = (session.query(PlayerVIP).join(PlayerID, PlayerVIP.player_id_id == PlayerID.id)
                           .filter(PlayerVIP.server_number == server_number, PlayerID.player_id == player_id)
                           .with_for_update().one_or_none())
                    if vip is None or normalize_expiration(vip.expiration) <= datetime.now(timezone.utc):
                        continue
                    current_expiration = vip.expiration.isoformat()
                    try:
                        description = vip.player.names[0].name
                    except IndexError:
                        description = "Restored CRCON VIP"
                rcon_hook.get_vip_ids.cache_clear()
                if player_id in {vip["player_id"] for vip in rcon_hook.get_vip_ids()}:
                    continue
                token = action_guard.reserve(int(server_number), player_id, ["VietnamVipRestore"], "vip")
                if token is None:
                    logger.warning("VIP restore awaits review for %s", player_id)
                    continue
                with rcon_hook.without_retries():
                    result = rcon_hook.add_vip(
                        player_id=player_id,
                        description=description,
                        expiration=current_expiration,
                    )
                if result is True or result is False:
                    action_guard.finish(int(server_number), player_id, token,
                                        "confirmed" if result is True else "rejected", expected=1)
                if result is True:
                    restored += 1
                else:
                    logger.warning("VIP restore was not confirmed for %s", player_id)
        except Exception:
            logger.exception("Unable to restore VIP %s", player_id)

    if restored:
        logger.warning(
            "Restored %s active VIP(s) missing from the game server", restored
        )
    return restored


def _backfill_vip_expiration(rcon_hook: Rcon, player_id: str, observed: datetime | None):
    from rcon.vip_rewards.locking import vip_lock

    # The scan can be stale. Hold the same lock as grants and revocations
    # from the fresh server read through the local commit.
    with vip_lock(player_id):
        if not rcon_hook.has_live_vip(player_id):
            return
        with enter_session() as session:
            player = session.query(PlayerID).filter_by(player_id=player_id).one_or_none()
            if player is None:
                return
            server_number = get_server_number()
            record = (
                session.query(PlayerVIP)
                .filter_by(player_id_id=player.id, server_number=server_number)
                .with_for_update()
                .one_or_none()
            )
            if record is None:
                if observed is None:
                    session.add(PlayerVIP(player_id_id=player.id, server_number=server_number,
                                          expiration=INDEFINITE_VIP_DATE))
            elif record.expiration == observed:
                record.expiration = INDEFINITE_VIP_DATE


def remove_expired_vips(rcon_hook: Rcon, webhook_url: Optional[HttpUrl] = None):
    logger.info(f"Checking for expired VIPs")

    count = 0
    orphan_count = 0
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

        for vip in expired_vips:
            name: str
            try:
                name = vip.player.names[0].name
            except IndexError:
                name = "No name found"
            try:
                outcome = _resolve_expired_vip(rcon_hook, vip.player.player_id, vip.expiration)
            except Exception:
                logger.exception("Unable to reconcile expired VIP %s", vip.player.player_id)
                continue
            if outcome == "removed":
                count += 1
                message = f"Removed VIP from `{name}`/`{vip.player.player_id}` expired `{vip.expiration}`"
            elif outcome == "orphan_cleaned":
                orphan_count += 1
                message = f"Cleared expired local VIP record for `{name}`/`{vip.player.player_id}`; already absent on server"
            else:
                logger.info("Expired VIP changed or was already reconciled; no removal recorded")
                continue
            logger.info(message)
            send_to_discord_audit(message=message, command_name="remove_vip", by=SERVICE_NAME,
                                  webhookurls=None if webhook_url is None else [webhook_url])

    legacy_threshold = datetime.now(timezone.utc) + timedelta(days=365 * 100)
    for vip in rcon_hook.get_vip_ids():
        observed = vip["vip_expiration"]
        if observed is None or (observed.year < 3000 and observed >= legacy_threshold):
            try:
                _backfill_vip_expiration(rcon_hook, vip["player_id"], observed)
            except Exception:
                logger.exception("Unable to reconcile missing or legacy VIP expiration for %s", vip["player_id"])


    if count > 0:
        logger.info(f"Removed VIP from {count} player(s)")
    else:
        logger.info("No game-server VIPs removed")
    if orphan_count:
        logger.info("Cleared %s expired local VIP record(s) already absent on server", orphan_count)


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
