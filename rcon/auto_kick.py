import logging
import re

from pydantic import HttpUrl

from rcon.api_commands import RconAPI
from rcon.discord import send_to_discord_audit
from rcon.hooks import inject_player_ids
from rcon.logs.loop import on_connected
from rcon.player_history import get_player_profile, player_has_flag
from rcon.user_config.name_kicks import NameKickUserConfig

logger = logging.getLogger(__name__)


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
            for flag in config.whitelist_flags:
                if player_has_flag(profile, flag):
                    logger.debug(
                        "Not checking nickname validity for whitelisted player %s (%s)",
                        name,
                        player_id,
                    )
                    return False
        except Exception:
            # Profile lookup failures must not let an invalid nickname bypass
            # the configured rules.
            logger.exception("Unable to check player profile")

    for pattern in config.regular_expressions:
        if re.match(pattern, name):
            logger.info("%s matched player %s", pattern, name)
            rcon.kick(
                player_name=name,
                reason=config.kick_reason,
                by="NAME_KICK",
                player_id=player_id,
            )
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
