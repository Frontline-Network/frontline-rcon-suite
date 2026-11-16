import logging
import re

from pydantic import HttpUrl

from rcon.api_commands import RconAPI
from rcon.automods import action_guard
from rcon.discord import send_to_discord_audit
from rcon.hooks import inject_player_ids
from rcon.logs.loop import on_connected
from rcon.player_history import get_player_profile, player_has_flag
from rcon.user_config.name_kicks import NameKickUserConfig
from rcon.utils import get_server_number

logger = logging.getLogger(__name__)
NAME_KICK_GUARD_RULE = "NameKick"


def apply_name_kick(
    rcon: RconAPI,
    name: str,
    player_id: str,
    config: NameKickUserConfig | None = None,
) -> bool:
    """Apply the configured name rules to one player.

    The helper is shared by the CONNECTED hook and the one-time roster scan
    after an operator changes the configuration.
    """
    config = config or NameKickUserConfig.load_from_db()

    if not config.regular_expressions or not name or not player_id:
        return False

    if config.whitelist_flags:
        try:
            profile = get_player_profile(player_id, 0)
            if (not isinstance(profile, dict) or not isinstance(profile.get("flags"), list)
                    or any(not isinstance(entry, dict) or not isinstance(entry.get("flag"), str)
                           for entry in profile["flags"])):
                logger.warning("Skipping nickname kick: player exemption flags are unavailable")
                return False
            for flag in config.whitelist_flags:
                if player_has_flag(profile, flag):
                    logger.debug(
                        "Not checking nickname validity for whitelisted player %s (%s)",
                        name,
                        player_id,
                    )
                    return False
        except Exception:
            # A lookup failure cannot establish that the player is not exempt.
            logger.exception("Skipping nickname kick: unable to check player exemptions")
            return False

    for pattern in config.regular_expressions:
        if re.match(pattern, name):
            logger.info("%s matched player %s", pattern, name)
            server_number = int(get_server_number())
            try:
                token = action_guard.reserve(server_number, player_id, [NAME_KICK_GUARD_RULE], "kick")
            except Exception:
                logger.exception("Skipping nickname kick: durable reservation unavailable")
                return False
            if token is None:
                logger.warning("Skipping nickname kick: previous result awaits review")
                return False
            try:
                accepted = rcon.kick(
                    player_name=name,
                    reason=config.kick_reason,
                    by="NAME_KICK",
                    player_id=player_id,
                )
            except Exception:
                logger.exception("Nickname kick result uncertain; reservation retained")
                return False
            if accepted is not True:
                if accepted is False:
                    try:
                        action_guard.finish(server_number, player_id, token, "rejected", expected=1)
                    except Exception:
                        logger.exception("Could not record rejected nickname kick; reservation retained")
                logger.warning("Game server did not confirm nickname kick for %s", player_id)
                return False
            try:
                action_guard.finish(server_number, player_id, token, "confirmed", expected=1)
            except Exception:
                logger.exception("Could not record confirmed nickname kick; reservation retained")
            try:
                webhookurls: list[HttpUrl | None] | None
                if config.discord_webhook_url is None:
                    webhookurls = None
                else:
                    webhookurls = [config.discord_webhook_url]
                send_to_discord_audit(
                    message=f"`{name}` kicked from regexp `{pattern}`",
                    command_name="kick",
                    by="NAME_KICK",
                    webhookurls=webhookurls,
                )
            except Exception:
                logger.exception("Unable to send to audit_log")
            return True

    return False


def scan_current_players(
    rcon: RconAPI, config: NameKickUserConfig | None = None
) -> int:
    """Check the current roster once after name-kick settings change."""
    config = config or NameKickUserConfig.load_from_db()
    if not config.regular_expressions:
        return 0

    players = rcon.get_player_ids()
    kicked = 0
    for name, player_id in players:
        try:
            kicked += int(apply_name_kick(rcon, name, player_id, config=config))
        except Exception:
            # One stale roster entry or rejected kick must not prevent the
            # remaining online players from being checked.
            logger.exception(
                "Unable to apply nickname rules to current player %s (%s)",
                name,
                player_id,
            )

    logger.info(
        "Checked %s current players after name-kick config update; kicked %s",
        len(players),
        kicked,
    )
    return kicked


@on_connected()
@inject_player_ids
def auto_kick(rcon: RconAPI, struct_log, name: str, player_id: str):
    return apply_name_kick(rcon, name, player_id)
