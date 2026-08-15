import logging
import random
import re
import time

from rcon.commands import HLLCommandFailedError
from rcon.message_variables import format_message_string, populate_message_variables
from rcon.types import MessageVariable
from rcon.user_config.auto_broadcast import (
    AutoBroadcastMessage,
    AutoBroadcastUserConfig,
)
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig
from rcon.user_config.chat_commands import MESSAGE_VAR_RE

logger = logging.getLogger(__name__)

CHECK_INTERVAL = 20

subs = {
    "nextmap": MessageVariable.next_map,
    "maprotation": MessageVariable.map_rotation,
    "servername": MessageVariable.server_name,
    "admins": MessageVariable.admin_names,
    "owners": MessageVariable.owner_names,
    "seniors": MessageVariable.senior_names,
    "juniors": MessageVariable.junior_names,
    "vips": MessageVariable.vip_names,
    "randomvip": MessageVariable.random_vip_name,
    "votenextmap_line": MessageVariable.votenextmap_line,
    "votenextmap_noscroll": MessageVariable.votenextmap_noscroll,
    "votenextmap_vertical": MessageVariable.votenextmap_vertical,
    "votenextmap_by_mod_line": MessageVariable.votenextmap_by_mod_line,
    "votenextmap_by_mod_vertical": MessageVariable.votenextmap_by_mod_vertical,
    "votenextmap_by_mod_vertical_all": MessageVariable.votenextmap_by_mod_vertical_all,
    "votenextmap_by_mod_split": MessageVariable.votenextmap_by_mod_split,
    "total_votes": MessageVariable.total_votes,
    "winning_maps_short": MessageVariable.winning_maps_short,
    "winning_maps_all": MessageVariable.winning_maps_all,
    "scrolling_votemap": MessageVariable.scrolling_votemap,
    "online_mods": MessageVariable.online_mods,
    "ingame_mods": MessageVariable.ingame_mods,
}


def format_message(ctl, msg):
    for sub in subs:
        msg = msg.replace(f"{{{sub}}}", f"{{{subs[sub].value}}}")
    message_vars: list[str] = re.findall(MESSAGE_VAR_RE, msg)
    populated_variables = populate_message_variables(
        vars=message_vars, player_id=None, rcon=ctl
    )

    try:
        return format_message_string(
            msg,
            populated_variables=populated_variables,
            context={},
        )
    except KeyError as e:
        logger.warning(
            "Can't broadcast message correctly, variable does not exists %s", e
        )
        return msg


def seeding_is_active(config: AutoModSeedingUserConfig, player_count: int) -> bool:
    """Return whether any configured seeding rule currently applies."""
    if not config.enabled:
        return False

    limits = [config.enforce_cap_fight.max_players]
    if config.disallowed_roles.roles:
        limits.append(config.disallowed_roles.max_players)
    if config.disallowed_weapons.weapons:
        limits.append(config.disallowed_weapons.max_players)

    return (
        player_count >= config.dont_do_anything_below_this_number_of_players
        and player_count <= max(limits)
    )


def campaign_is_eligible(
    campaign: AutoBroadcastMessage,
    player_count: int,
    seeding_config: AutoModSeedingUserConfig | None = None,
) -> bool:
    """Apply campaign guards without changing legacy broadcast behaviour."""
    if not campaign.enabled:
        return False
    if not campaign.min_players <= player_count <= campaign.max_players:
        return False
    if (
        campaign.pause_during_seeding
        and seeding_config is not None
        and seeding_is_active(seeding_config, player_count)
    ):
        return False
    return True


def manual_broadcast_is_active(ctl, campaigns: list[AutoBroadcastMessage]) -> bool:
    """Protect a recent manual/admin broadcast from campaign replacement.

    CRCON keeps the last broadcast in Redis for 30 minutes.  Campaign messages
    are recognised by their formatted text; any other cached text is treated as
    an operator or automod message and is allowed to finish first.
    """
    try:
        current = ctl.get_broadcast_message()
    except Exception:
        logger.exception("Unable to inspect the current broadcast message")
        return False

    if not current:
        return False

    managed_messages = {format_message(ctl, item.message) for item in campaigns}
    return current not in managed_messages


def run():
    # avoid circular import
    from rcon.rcon import get_rcon

    ctl = get_rcon()

    while True:
        config = AutoBroadcastUserConfig.load_from_db()
        if not config.enabled or not config.messages:
            logger.debug(
                "Auto broadcasts are disabled. Sleeping %s seconds", CHECK_INTERVAL
            )
            time.sleep(CHECK_INTERVAL)
            continue

        campaigns = list(config.messages)
        if config.randomize:
            logger.debug("Auto broadcasts. Radomizing")
            random.shuffle(campaigns)

        sent_campaign = False
        needs_seeding_state = any(msg.pause_during_seeding for msg in campaigns)
        seeding_config = (
            AutoModSeedingUserConfig.load_from_db()
            if needs_seeding_state
            else None
        )

        try:
            player_count = int(ctl.get_slots()["current_players"])
        except (HLLCommandFailedError, KeyError, TypeError, ValueError):
            logger.exception("Unable to determine player count for campaigns")
            time.sleep(CHECK_INTERVAL)
            continue

        if manual_broadcast_is_active(ctl, campaigns):
            logger.info("A manual broadcast is active; campaign cycle deferred")
            time.sleep(CHECK_INTERVAL)
            continue

        for msg in campaigns:
            if not config.enabled:
                break

            if not campaign_is_eligible(msg, player_count, seeding_config):
                logger.debug(
                    "Skipping campaign %s for %s players",
                    msg.title or msg.id or "legacy broadcast",
                    player_count,
                )
                continue

            formatted = format_message(ctl, msg.message)
            logger.debug(
                "Broadcasting campaign %s for %s seconds: %s",
                msg.title or msg.id or "legacy broadcast",
                msg.time_sec,
                formatted,
            )
            try:
                ctl.set_broadcast(formatted)
                sent_campaign = True
            except HLLCommandFailedError:
                logger.exception("Unable to broadcast %s %s", msg.time_sec, msg.message)
            time.sleep(int(msg.time_sec))

        if not sent_campaign:
            time.sleep(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
