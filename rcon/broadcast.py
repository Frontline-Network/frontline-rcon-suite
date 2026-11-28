import logging
import random
import re
import threading
import time

from rcon.broadcast_activity import load_rotation, record_attempt, save_rotation, update_state

from rcon.connection import HLLCommandError
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


def format_message(ctl, msg, player_id=None, context=None):
    for sub in subs:
        msg = msg.replace(f"{{{sub}}}", f"{{{subs[sub].value}}}")
    message_vars: list[str] = re.findall(MESSAGE_VAR_RE, msg)
    populated_variables = populate_message_variables(
        vars=message_vars, player_id=player_id, rcon=ctl
    )

    try:
        return format_message_string(
            msg,
            populated_variables=populated_variables,
            context=context or {},
        )
    except KeyError as e:
        logger.warning(
            "Can't format campaign message correctly, variable does not exist %s", e
        )
        return msg


def seeding_is_active(config: AutoModSeedingUserConfig, player_count: int) -> bool:
    """Return whether any configured seeding rule currently applies."""
    if not config.enabled or player_count < config.dont_do_anything_below_this_number_of_players:
        return False
    rules = (
        (config.enforce_cap_fight, True),
        (config.disallowed_roles, bool(config.disallowed_roles.roles)),
        (config.disallowed_weapons, bool(config.disallowed_weapons.weapons)),
    )
    return any(rule.enabled and configured and rule.min_players <= player_count < rule.max_players
               for rule, configured in rules)


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


def broadcast_slots(config):
    # Older records can lack IDs. A private message inserted before an old
    # slot must not change its identity within the broadcast rotation.
    broadcasts = (msg for msg in config.messages if msg.delivery_mode == "broadcast")
    return {
        (f"id:{msg.id}" if msg.id else f"legacy:{index}"): msg
        for index, msg in enumerate(broadcasts)
    }


def wait_for_campaign(stop_event, slot_key, campaign):
    """Keep this slot's dwell time when unrelated settings change."""
    started = time.monotonic()
    current = campaign
    while not stop_event.is_set():
        remaining = started + current.time_sec - time.monotonic()
        if remaining <= 0:
            return
        update_state("waiting", time.time() + remaining)
        if stop_event.wait(min(CHECK_INTERVAL, remaining)):
            return
        try:
            config = AutoBroadcastUserConfig.load_from_db()
        except Exception:
            logger.exception("Cannot refresh broadcast settings during a slot")
            continue
        current = broadcast_slots(config).get(slot_key)
        if (not config.enabled or current is None or not current.enabled
                or current.message != campaign.message
                or current.min_players != campaign.min_players
                or current.max_players != campaign.max_players
                or current.pause_during_seeding != campaign.pause_during_seeding):
            return


def run(stop_event: threading.Event | None = None):
    # avoid circular import
    from rcon.rcon import get_rcon

    stop_event = stop_event or threading.Event()
    if stop_event.is_set():
        return
    ctl = get_rcon()
    remaining = load_rotation()
    while not stop_event.is_set():
        try:
            config = AutoBroadcastUserConfig.load_from_db()
            slots = broadcast_slots(config)
            if not config.enabled or not slots:
                update_state("paused" if not config.enabled else "no_broadcasts")
                stop_event.wait(CHECK_INTERVAL)
                continue

            try:
                player_count = int(ctl.get_slots()["current_players"])
            except Exception:
                logger.exception("Unable to determine player count for campaigns")
                update_state("player_count_unavailable")
                stop_event.wait(CHECK_INTERVAL)
                continue

            seeding = (
                AutoModSeedingUserConfig.load_from_db()
                if any(msg.enabled and msg.pause_during_seeding for msg in slots.values())
                else None
            )
            eligible = {
                key for key, msg in slots.items()
                if campaign_is_eligible(msg, player_count, seeding)
            }
            if not eligible:
                update_state("no_eligible_campaigns")
                stop_event.wait(CHECK_INTERVAL)
                continue

            remaining = [key for key in remaining if key in eligible]
            if not remaining:
                remaining = [key for key in slots if key in eligible]
                if config.randomize:
                    random.shuffle(remaining)

            key = remaining.pop(0)
            campaign = slots[key]
            formatted = campaign.message
            try:
                formatted = format_message(ctl, campaign.message)
                update_state("sending")
                # The same text is sent, cached and audited. Never interpret
                # braces in a substituted map, server or player name twice.
                ctl._send_rendered_broadcast(formatted, cached_text=formatted)
            except Exception as exc:
                logger.exception("Unable to broadcast campaign %s", campaign.id)
                error = f"RCON {exc.status_code}" if isinstance(exc, HLLCommandError) else type(exc).__name__
                record_attempt(campaign, formatted, False, error)
                save_rotation(remaining)
                update_state("waiting", time.time() + CHECK_INTERVAL)
                stop_event.wait(CHECK_INTERVAL)
                continue

            record_attempt(campaign, formatted, True)
            save_rotation(remaining)
            wait_for_campaign(stop_event, key, campaign)
        except Exception:
            logger.exception("Broadcast scheduler temporarily unavailable")
            update_state("waiting", time.time() + CHECK_INTERVAL)
            stop_event.wait(CHECK_INTERVAL)


if __name__ == "__main__":
    run()
