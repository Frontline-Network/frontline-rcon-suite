import datetime
import logging

from pydantic import HttpUrl

from rcon.blacklist import blacklist_or_ban
from rcon.discord import send_to_discord_audit
from rcon.game_logs import get_recent_logs
from rcon.logs.loop import on_tk
from rcon.player_history import get_player_profile, player_has_flag
from rcon.rcon import Rcon
from rcon.types import StructuredLogLineWithMetaData, BlacklistRecordWithBlacklistType
from rcon.user_config.ban_tk_on_connect import BanTeamKillOnConnectUserConfig
from rcon.utils import get_server_number
from rcon.automods import tk_action_guard

logger = logging.getLogger(__name__)


def _matches_player(player_id, log, position):
    value = log.get(f"player_id_{position}")
    return value is not None and str(value) == str(player_id)


def is_player_death(player_id, log):
    return log["action"] == "KILL" and _matches_player(player_id, log, 2)


def is_player_kill(player_id, log):
    return log["action"] == "KILL" and _matches_player(player_id, log, 1)


@on_tk
def auto_ban_if_tks_right_after_connection(
        rcon: Rcon,
        log: StructuredLogLineWithMetaData,
        config: BanTeamKillOnConnectUserConfig | None = None,
) -> None | bool | BlacklistRecordWithBlacklistType:
    if config is None:
        config = BanTeamKillOnConnectUserConfig.load_from_db()
    if not config or not config.enabled:
        return

    result: None | bool | BlacklistRecordWithBlacklistType = None

    player_name = log["player_name_1"]
    player_id = log["player_id_1"]
    if not player_id:
        logger.warning("Skipping teamkill rule because the player ID is missing")
        return
    trigger_timestamp = log.get("timestamp_ms")
    try:
        tk_action_guard.ensure_cutover(int(get_server_number()), trigger_timestamp)
    except Exception:
        logger.exception("Unable to establish teamkill transition boundary; skipping teamkill ban")
        return
    whitelist_players = config.whitelist_players
    if whitelist_players.is_vip:
        try:
            rows = rcon.get_vip_ids()
            if not isinstance(rows, list) or any(
                not isinstance(row, dict) or not row.get("player_id") for row in rows
            ):
                raise ValueError("Incomplete VIP list")
            if str(player_id) in {str(row["player_id"]) for row in rows}:
                logger.debug("Not checking player because they are VIP")
                return
        except Exception:
            logger.exception("Unable to verify VIP exemption; skipping teamkill ban")
            return

    if whitelist_players.has_at_least_n_sessions or whitelist_players.has_flag:
        try:
            player_profile = get_player_profile(player_id, 0)
            if player_profile is not None:
                if not isinstance(player_profile, dict):
                    raise ValueError("Invalid player profile")
                if whitelist_players.has_at_least_n_sessions:
                    count = player_profile.get("sessions_count")
                    if not isinstance(count, int) or isinstance(count, bool) or count < 0:
                        raise ValueError("Invalid player session count")
                    if count >= whitelist_players.has_at_least_n_sessions:
                        logger.debug("Not checking player because they have %s sessions", count)
                        return
                if whitelist_players.has_flag:
                    flags = player_profile.get("flags")
                    if not isinstance(flags, list) or any(
                        not isinstance(flag, dict) or not isinstance(flag.get("flag"), str)
                        for flag in flags
                    ):
                        raise ValueError("Incomplete player flags")
                    if any(player_has_flag(player_profile, flag) for flag in whitelist_players.has_flag):
                        logger.debug("Not checking player due to a whitelist flag")
                        return
        except Exception:
            logger.exception("Unable to verify player exemptions; skipping teamkill ban")
            return

    # Names are not unique and can change within a session. Match event
    # identities after reading the same bounded history instead of filtering by name.
    last_logs = get_recent_logs(end=500)
    logger.debug("Checking TK from %s", player_name)
    author = config.author_name
    reason = config.message
    discord_msg = config.discord_webhook_message
    webhook = config.discord_webhook_url
    max_time_minute = config.max_time_after_connect_minutes
    excluded_weapons = [w.lower() for w in config.excluded_weapons]
    ignore_after_kill = config.ignore_tk_after_n_kills
    ignore_after_death = config.ignore_tk_after_n_deaths
    tk_tolerance_count = config.teamkill_tolerance_count

    last_action_is_connect = False
    last_connect_time = None
    kill_counter = 0
    death_counter = 0
    tk_counter = 0
    for log in reversed(last_logs["logs"]):
        logger.debug(log)

        if log["action"] == "CONNECTED":
            if not _matches_player(player_id, log, 1):
                if log.get("player_name_1") == player_name and not log.get("player_id_1"):
                    last_action_is_connect = False
                continue
            last_action_is_connect = log
            last_connect_time = log["timestamp_ms"]
            kill_counter = 0
            death_counter = 0
            continue
        if (
                log["action"] == "TEAM KILL"
                and _matches_player(player_id, log, 1)
                and last_action_is_connect
        ):
            if excluded_weapons and log["weapon"].lower() in excluded_weapons:
                logger.debug("Not counting TK as offense due to weapon exclusion")
                continue
            if log["timestamp_ms"] - last_connect_time > max_time_minute * 60 * 1000:
                logger.debug(
                    "Not counting TK as offense due to elapsed time exclusion, last connection time %s, tk time %s",
                    datetime.datetime.fromtimestamp(last_connect_time / 1000),
                    datetime.datetime.fromtimestamp(log["timestamp_ms"] / 1000),
                )
                continue

            tk_counter += 1
            if tk_counter > tk_tolerance_count:
                logger.info(
                    "Banning player %s for TEAMKILL after connect %s", player_name, log
                )
                if config.ban_duration.total_seconds > 0:
                    expires_at = (
                            datetime.datetime.now(datetime.timezone.utc) + config.ban_duration.as_timedelta
                    )
                else:
                    expires_at = None

                try:
                    server = int(get_server_number())
                    token = tk_action_guard.reserve(server, str(player_id), last_connect_time, trigger_timestamp)
                except Exception:
                    logger.exception("Unable to reserve teamkill ban; no action taken")
                    return
                if token is None:
                    logger.warning("Teamkill ban is held by the durable guard or cutover for %s", player_id)
                    return
                try:
                    result = blacklist_or_ban(
                        rcon=rcon,
                        blacklist_id=config.blacklist_id,
                        player_id=player_id,
                        reason=reason,
                        admin_name=author,
                        expires_at=expires_at,
                    )
                except Exception:
                    logger.exception("Teamkill ban outcome uncertain; reservation requires review")
                    return
                confirmed = result is True or (isinstance(result, dict) and bool(result))
                if confirmed or result is False:
                    try:
                        state = 'confirmed' if confirmed else 'rejected'
                        if tk_action_guard.finish(server, str(player_id), token, state) != 1:
                            raise RuntimeError("Teamkill reservation could not be finished")
                    except Exception:
                        logger.exception("Unable to finalize teamkill reservation; review is required")
                        return result
                if not confirmed:
                    logger.warning("Teamkill ban for %s was not confirmed", player_id)
                    return result
                if isinstance(result, dict):
                    logger.info("Blacklist entry recorded for %s; game-server enforcement is pending", player_id)
                    audit_message = f"Blacklist entry created for {player_name}; game-server enforcement pending."
                else:
                    audit_message = discord_msg.format(player=player_name)
                logger.info(
                    "Teamkill action recorded for player %s after connect %s", player_name, log
                )

                webhookurls: list[HttpUrl | None] | None
                if webhook is None:
                    webhookurls = None
                else:
                    webhookurls = [webhook]
                send_to_discord_audit(
                    message=audit_message,
                    command_name="blacklist",
                    by=author,
                    webhookurls=webhookurls,
                )
                # The rest of this history can contain additional qualifying
                # teamkills from the same connection. One scan must not issue
                # another ban for the same player.
                return result
        elif log["action"] in {"KILL", "TEAM KILL"} and any(
            log.get(f"player_name_{position}") == player_name and not log.get(f"player_id_{position}")
            for position in (1, 2)
        ):
            logger.warning("Skipping teamkill rule because a relevant event has no player ID")
            return
        elif is_player_death(player_id, log):
            death_counter += 1
            if death_counter >= ignore_after_death:
                last_action_is_connect = False
        elif is_player_kill(player_id, log):
            kill_counter += 1
            if kill_counter >= ignore_after_kill:
                last_action_is_connect = False

    return result
