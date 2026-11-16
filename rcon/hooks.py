import json
import logging
import re
import shlex
from datetime import UTC, datetime, timedelta, timezone
from functools import wraps
from typing import Final

from discord_webhook import DiscordEmbed

import rcon.steam_utils as steam_utils
from discord.utils import escape_markdown
from rcon.arguments import max_arg_index, replace_params
from rcon.automods import action_guard
from rcon.blacklist import (
    apply_blacklist_punishment,
    blacklist_or_ban,
    is_player_blacklisted,
)
from rcon.cache_utils import invalidates, get_redis_client
from rcon.commands import HLLCommandFailedError
from rcon.discord import get_prepared_discord_hooks, send_to_discord_audit
from rcon.frontline_vip_verification import handle_chat_verification
from rcon.hllv_admin_refresh import refresh_hllv_admin_role_on_connect
from rcon.logs.loop import (
    on_camera,
    on_chat,
    on_connected,
    on_disconnected,
    on_match_end,
    on_match_start,
)
from rcon.message_variables import format_message_string, populate_message_variables
from rcon.models import PlayerID, PlayerFlag, PlayerSoldier, enter_session, GameLayout
from rcon.player_history import (
    _get_set_player,
    get_player,
    save_end_player_session,
    save_player,
    save_start_player_session,
)
from rcon.rcon import Rcon, StructuredLogLineWithMetaData, do_run_commands
from rcon.recent_actions import get_recent_actions
from rcon.types import (
    GameEnum,
    MessageVariableContext,
    MostRecentEvents,
    PlayerFlagType,
    SteamBansType,
    WindowsStoreIdActionType,
)
from rcon.user_config.camera_notification import CameraNotificationUserConfig
from rcon.user_config.chat_commands import (
    MESSAGE_VAR_RE,
    BaseChatCommand,
    ChatCommand,
    ChatCommandsUserConfig,
    chat_contains_command_word,
    is_command_word,
    is_description_word,
    is_help_word,
)
from rcon.user_config.rcon_chat_commands import (
    RConChatCommand,
    RConChatCommandsUserConfig,
)
from rcon.user_config.rcon_server_settings import RconServerSettingsUserConfig
from rcon.user_config.real_vip import RealVipUserConfig
from rcon.user_config.vac_game_bans import VacGameBansUserConfig
from rcon.user_config.webhooks import CameraWebhooksUserConfig
from rcon.utils import (
    DefaultStringFormat,
    MapsHistory,
    get_server_number,
    guess_map_from_log,
    layer_matches_match_log,
)
from rcon.vote_map import VoteMap
from rcon.workers import (
    get_queue,
    save_missing_match_logs_worker,
    record_stats_worker,
    temporary_broadcast,
    temporary_welcome,
    update_player_steaminfo_on_connect_worker,
)

logger = logging.getLogger(__name__)
ARG_RE = re.compile(r"\$(\d+)")
STEAM_ENRICHMENT_MAX_EVENT_AGE: Final = timedelta(minutes=5)
STEAM_ENRICHMENT_DEDUPE_SECONDS: Final = 15 * 60
VAC_ACTION_GUARD_RULE: Final = "VacHistory"
STEAM_ENRICHMENT_DEDUPE_PREFIX: Final = "steam_connect_enrichment"


@on_chat
def count_map_vote(_, struct_log: StructuredLogLineWithMetaData):
    VoteMap().handle_vote_command(struct_log)


@on_chat
def frontline_vip_verification(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    handle_chat_verification(rcon, struct_log)


@on_chat
def chat_commands(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    chat_config = ChatCommandsUserConfig.load_from_db()
    rcon_config = RConChatCommandsUserConfig.load_from_db()

    words: list[BaseChatCommand] = []
    if chat_config.enabled:
        words.extend(chat_config.command_words)
    if rcon_config.enabled:
        words.extend(rcon_config.command_words)
    if len(words) == 0:
        return

    chat_message = struct_log["sub_content"]
    if chat_message is None:
        return

    event_cache = get_recent_actions()
    player_id: str = struct_log["player_id_1"]
    if player_id is None:
        return

    player_cache = event_cache.get(player_id, MostRecentEvents())
    chat_words = set(chat_message.split())
    ctx = {
        MessageVariableContext.player_name.value: struct_log["player_name_1"],
        MessageVariableContext.player_id.value: player_id,
        MessageVariableContext.last_victim_player_id.value: player_cache.last_victim_player_id,
        MessageVariableContext.last_victim_name.value: player_cache.last_victim_name,
        MessageVariableContext.last_victim_weapon.value: player_cache.last_victim_weapon,
        MessageVariableContext.last_nemesis_player_id.value: player_cache.last_nemesis_player_id,
        MessageVariableContext.last_nemesis_name.value: player_cache.last_nemesis_name,
        MessageVariableContext.last_nemesis_weapon.value: player_cache.last_nemesis_weapon,
        MessageVariableContext.last_tk_nemesis_player_id.value: player_cache.last_tk_nemesis_player_id,
        MessageVariableContext.last_tk_nemesis_name.value: player_cache.last_tk_nemesis_name,
        MessageVariableContext.last_tk_nemesis_weapon.value: player_cache.last_tk_nemesis_weapon,
        MessageVariableContext.last_tk_victim_player_id.value: player_cache.last_tk_victim_player_id,
        MessageVariableContext.last_tk_victim_name.value: player_cache.last_tk_victim_name,
        MessageVariableContext.last_tk_victim_weapon.value: player_cache.last_tk_victim_weapon,
    }

    for command in words:
        if not (
            triggered_word := chat_contains_command_word(
                chat_words, command.words, command.help_words
            )
        ):
            continue

        if is_command_word(triggered_word) and isinstance(command, ChatCommand):
            chat_message_command(rcon, command, ctx)
        if (
            is_command_word(triggered_word)
            and isinstance(command, RConChatCommand)
            and command.enabled
        ):
            chat_rcon_command(rcon, command, ctx, triggered_word, chat_message)
        if is_help_word(triggered_word):
            # Help words describe a specific command
            chat_help_command(rcon, command, ctx)

    # Description words trigger the entire help menu, test outside the loop
    # since these are global help words
    if is_description_word(chat_words, chat_config.describe_words):
        description = chat_config.describe_chat_commands()
        if description:
            rcon.message_player(
                player_id=player_id,
                message="\n".join(description),
                save_message=False,
            )
        else:
            logger.warning(
                "No descriptions set for command words, %s",
                ", ".join(chat_config.describe_words),
            )


def chat_message_command(rcon: Rcon, command: ChatCommand, ctx: dict[str, str]):
    player_id = ctx[MessageVariableContext.player_id.value]
    message_vars: list[str] = MESSAGE_VAR_RE.findall(command.message)
    populated_variables = populate_message_variables(
        vars=message_vars, player_id=player_id
    )
    formatted_message = format_message_string(
        command.message,
        populated_variables=populated_variables,
        context=ctx,
    )
    rcon.message_player(
        player_id=player_id,
        message=formatted_message,
        save_message=False,
    )


def chat_rcon_command(
    rcon: Rcon,
    command: RConChatCommand,
    ctx: dict[str, str],
    triggering_word: str,
    msg: str,
):
    player_id = ctx[MessageVariableContext.player_id.value]
    player: PlayerID
    with enter_session() as session:
        player = (
            session.query(PlayerID)
            .filter(PlayerID.player_id == player_id)
            .one_or_none()
        )
        if player is None:
            logger.debug(
                "player executed a command but does not exist in database: %s",
                player_id,
            )
        if not command.conditions_fulfilled(rcon, player, ctx):
            return

        arguments = msg[msg.find(triggering_word) + len(triggering_word) + 1 :]
        args = shlex.split(arguments)
        expected_argument_count = 0
        for _, params in command.commands.items():
            for _, v in params.items():
                a = max_arg_index(v)
                if a > expected_argument_count:
                    expected_argument_count = a
        if len(args) != expected_argument_count:
            logger.info(
                "provided message does not have expected number of arguments. Expected %d, got %d. Message: %s, Command: %s",
                expected_argument_count,
                len(args),
                msg,
                triggering_word,
            )
            return

        commands: dict[str, dict[str, str | list[str]]] = {}
        for name, params in command.commands.items():
            logger.info("Original: %s -> %s, args: %s", name, params, args)
            commands[name] = {}
            for k, v in params.items():
                commands[name][k] = replace_params(ctx, args, v)

        do_run_commands(rcon, commands)


def chat_help_command(rcon: Rcon, command: BaseChatCommand, ctx: dict[str, str]):
    player_id = ctx[MessageVariableContext.player_id.value]
    description = command.description
    if description:
        rcon.message_player(
            player_id=player_id,
            message=description,
            save_message=False,
        )
    else:
        rcon.message_player(
            player_id=player_id,
            message="Command description not set, let the admins know!",
            save_message=False,
        )
        logger.warning(
            "No descriptions set for chat command word(s), %s",
            ", ".join(command.words),
        )


@on_match_end
def remind_vote_map(_, struct_log):
    vm = VoteMap()
    if vm.enabled:
        logger.info("Match ended reminding to vote map. %s", struct_log)
        vm.apply_results()
        if vm.config.remind_on_match_end:
            vm.send_reminder(force=True, scope=f"event:end:{struct_log['timestamp_ms']}")
        else:
            vm.send_reminder(force=False)


@on_match_start
def reset_watch_killrate_cooldown(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    """Reset the last reported time cache for new matches"""
    from rcon.watch_killrate import reset_cache

    reset_cache()


@on_match_start
def handle_new_match_start(rcon: Rcon, struct_log):
    # The event is authoritative. GetServerInformation frequently times out
    # while HLL loads a map; it must not gate persistence of the round boundary.
    # The polling loop enriches the guessed layer/timer once live data agrees.
    maps_history = MapsHistory()
    start = int(struct_log["timestamp_ms"] / 1000)
    current = maps_history.get_current_map()
    if current and current["start"] is not None and start <= current["start"]:
        logger.info("Ignoring duplicate or older match start at %s", start)
        return
    log_map = guess_map_from_log(struct_log, rcon.game_profile.layers)
    game_layout: GameLayout = {"requested": [], "set": []}
    try:
        raw = get_redis_client().getdel("GAME_LAYOUT")
        loaded = json.loads(raw) if raw is not None else {}
        if isinstance(loaded, dict):
            game_layout = {
                "requested": loaded.get("requested", []),
                "set": loaded.get("set", []),
            }
    except Exception as e:
        logger.error("Could not fetch Game Layout: %s", e)

    if (
        maps_history.save_new_map(
            new_map=str(log_map),
            guessed=True,
            start_timestamp=start,
            game_layout=game_layout,
            match_time=0,
            start_log=struct_log["raw"],
        )
        is None
    ):
        return

    # A voting/webhook failure must not prevent round statistics from queuing.
    prev_map = maps_history[1] if len(maps_history) > 1 else None
    if (
        prev_map
        and prev_map.get("start") is not None
        and prev_map.get("end") is not None
    ):
        first_job = None
        try:
            first_job = save_missing_match_logs_worker(prev_map)
        except Exception:
            logger.exception("Unable to enqueue match-log backfill")
        try:
            record_stats_worker(prev_map, first_job)
        except Exception:
            logger.exception("Unable to enqueue round statistics")

    try:
        # Clear the old round's cached layer/timer without querying the server.
        # Otherwise a same-map day/night switch could refine against stale data.
        with invalidates(Rcon.get_map, Rcon.get_next_map, Rcon.get_gamestate):
            pass
    except Exception:
        logger.exception("Unable to invalidate previous round's live data")

    try:
        vm = VoteMap()
        if vm.enabled:
            logger.info("MATCH START: Restarting votemap")
            if prev_map:
                vm.record_result(prev_map)
                send_to_discord_audit(
                    command_name="on_match_start",
                    message=vm.get_result_message(),
                    md_escape_message=False,
                    flatten=False,
                )
            vm.restart()
            if vm.config.remind_on_match_start:
                vm.send_reminder(force=True, scope=f"event:start:{struct_log['timestamp_ms']}")
            else:
                vm.send_reminder(force=False)
    except Exception:
        logger.exception("Unable to update map vote after recording match start")


@on_match_end
def record_map_end(rcon: Rcon, struct_log: StructuredLogLineWithMetaData):
    logger.info("Match ended recording map %s", struct_log)
    maps_history = MapsHistory()
    current = maps_history.get_current_map()
    if not current:
        return
    end = int(struct_log["timestamp_ms"] / 1000)
    if (
        current["start"] is None
        or end <= current["start"]
        or current["end"] is not None
    ):
        return
    layer = rcon.game_profile.parse_layer(current["name"])
    if current.get("guessed") and current.get("start_log"):
        # With no successful live poll, the start may still have an unspecified
        # weather/attacker. An end log can supply it, but cannot contradict start.
        log_layer = guess_map_from_log(struct_log, rcon.game_profile.layers)
        if layer_matches_match_log(log_layer, current["start_log"]):
            current["name"] = log_layer.id
            maps_history.update(0, current)
            layer = log_layer
    if not layer_matches_match_log(layer, struct_log["raw"]):
        logger.warning(
            "Ignoring match end that does not match cached round %s", current["name"]
        )
        return
    maps_history.save_map_end(
        current["name"],
        end_timestamp=end,
        start_timestamp=current["start"],
    )


def ban_if_blacklisted(rcon: Rcon, player_id: str, name: str):
    with enter_session() as sess:
        blacklist = is_player_blacklisted(sess, player_id)
        if not blacklist:
            return False

        return apply_blacklist_punishment(
            rcon, blacklist, player_id=player_id, player_name=name
        )


def should_ban(
    bans: SteamBansType | None,
    max_game_bans: float,
    max_days_since_ban: int,
    player_flags: list[PlayerFlag | PlayerFlagType | str] | None = None,
    whitelist_flags: list[str] | None = None,
) -> bool | None:
    if not bans:
        return

    if whitelist_flags:
        if player_flags is None:
            logger.warning("Skipping VAC ban: player exemption flags unavailable")
            return None
        try:
            flags = [
                flag if isinstance(flag, str) else
                flag.get("flag") if isinstance(flag, dict) else
                flag.flag if isinstance(flag, PlayerFlag) else None
                for flag in player_flags
            ]
        except Exception:
            logger.exception("Skipping VAC ban: unable to read player exemption flags")
            return None
        if any(not isinstance(flag, str) for flag in flags):
            logger.warning("Skipping VAC ban: invalid player exemption flags")
            return None
        if any(flag in whitelist_flags for flag in flags):
            return False

    try:
        days_since_last_ban = int(bans["DaysSinceLastBan"])
        number_of_game_bans = int(bans.get("NumberOfGameBans", 0))
    except ValueError:  # In case DaysSinceLastBan can be null
        return

    has_a_ban = bans.get("VACBanned") == True or number_of_game_bans >= max_game_bans

    if days_since_last_ban <= 0:
        return False

    if days_since_last_ban <= max_days_since_ban and has_a_ban:
        return True

    return False


def ban_if_has_vac_bans(rcon: Rcon, player_id: str, name: str):
    config = VacGameBansUserConfig.load_from_db()

    max_days_since_ban = config.vac_history_days
    max_game_bans = (
        float("inf") if config.game_ban_threshhold <= 0 else config.game_ban_threshhold
    )
    whitelist_flags = config.whitelist_flags

    if max_days_since_ban <= 0:
        return  # Feature is disabled

    with enter_session() as sess:
        player = get_player(sess, player_id)

        if not player:
            logger.error("Can't check VAC history, player not found %s", player_id)
            return

        bans = player.steaminfo.bans if player.steaminfo else None
        if not bans or not isinstance(bans, dict):
            logger.warning(
                "Can't fetch Bans for player %s, received %s", player_id, bans
            )
            return

        if should_ban(
            bans,
            max_game_bans,
            max_days_since_ban,
            player_flags=player.flags,
            whitelist_flags=whitelist_flags,
        ):
            days_since_last_ban = int(bans["DaysSinceLastBan"])
            reason = config.ban_on_vac_history_reason.format(
                DAYS_SINCE_LAST_BAN=days_since_last_ban,
                MAX_DAYS_SINCE_BAN=str(max_days_since_ban),
            )
            if config.auto_expire:
                days_until_expire = max_days_since_ban - days_since_last_ban
                if days_until_expire <= 0:
                    logger.info("Skipping VAC action: calculated expiry has already been reached")
                    return
                expires_at = datetime.now(tz=timezone.utc) + timedelta(
                    days=days_until_expire
                )
            else:
                expires_at = None
            server_number = int(get_server_number())
            try:
                token = action_guard.reserve(server_number, player_id, [VAC_ACTION_GUARD_RULE], "ban")
            except Exception:
                logger.exception("Skipping VAC action: durable reservation unavailable")
                return
            if token is None:
                logger.warning("Skipping VAC action: previous result awaits review")
                return
            try:
                result = blacklist_or_ban(
                    rcon=rcon,
                    blacklist_id=config.blacklist_id,
                    player_id=player_id,
                    reason=reason,
                    expires_at=expires_at,
                    admin_name="VAC BOT",
                )
            except Exception:
                logger.exception("VAC action result uncertain; reservation retained")
                return
            confirmed = (config.blacklist_id is not None and isinstance(result, dict) and bool(result.get("id"))) or (
                config.blacklist_id is None and result is True
            )
            if confirmed or result is False:
                try:
                    action_guard.finish(server_number, player_id, token,
                                        "confirmed" if confirmed else "rejected", expected=1)
                except Exception:
                    logger.exception("Could not finalize VAC action; reservation retained")
            if config.blacklist_id is not None and confirmed:
                logger.info("VAC blacklist record created for player %s; game-server synchronization pending", player_id)
            elif config.blacklist_id is None and confirmed:
                logger.info("VAC ban confirmed by game server for player %s", player_id)
            else:
                logger.warning("VAC action was not confirmed for player %s", player_id)


def inject_player_ids(func):
    @wraps(func)
    def wrapper(rcon, struct_log: StructuredLogLineWithMetaData):
        name = struct_log["player_name_1"]
        player_id = struct_log["player_id_1"]
        return func(rcon, struct_log, name, player_id)

    return wrapper


@on_connected()
@inject_player_ids
def handle_on_connect(
    rcon: Rcon, struct_log: StructuredLogLineWithMetaData, name: str, player_id: str
):
    try:
        rcon.get_players.clear_for()
        rcon.get_player_info.clear_for(player_id=struct_log["player_id_1"])
        rcon.get_detailed_player_info.clear_for(player_id=struct_log["player_id_1"])
    except Exception:
        logger.exception("Unable to clear cache for %s", player_id)

    timestamp = int(struct_log["timestamp_ms"]) / 1000
    if not player_id:
        logger.error(
            "Unable to get player ID for %s, can't process connection",
            struct_log,
        )
        return

    try:
        player_info = rcon.get_detailed_player_info(player_id)
    except HLLCommandFailedError as e:
        logger.warning("Unable to update soldier info for %s\n%s", player_id, str(e))
        player_info = None

    save_player(
        struct_log["player_name_1"],
        player_id,
        timestamp=int(struct_log["timestamp_ms"]) / 1000,
        steam_id=player_info["steam_id"] if player_info else None,
    )

    if player_info:
        PlayerSoldier.update(player_info)

    blacklisted = ban_if_blacklisted(rcon, player_id, struct_log["player_name_1"])
    if blacklisted:
        # We don't need the player potentially blacklisted a second
        # time because of VAC bans. So we return here.
        return

    save_start_player_session(player_id, timestamp=timestamp)
    ban_if_has_vac_bans(rcon, player_id, struct_log["player_name_1"])


@on_disconnected
@inject_player_ids
def handle_on_disconnect(rcon, struct_log, _, player_id: str):
    if not player_id:
        logger.debug("Ignoring anonymous disconnect event: %s", struct_log["raw"])
        return
    save_end_player_session(player_id, struct_log["timestamp_ms"] / 1000)


@on_connected()
@inject_player_ids
def refresh_hllv_spectator_on_connect(
    rcon: Rcon,
    struct_log: StructuredLogLineWithMetaData,
    name: str,
    player_id: str,
):
    """Work around HLLV not restoring spectator rights after reconnect."""

    try:
        refresh_hllv_admin_role_on_connect(rcon, player_id, name)
    except Exception:
        # A privilege refresh must never interrupt CONNECTED log processing or
        # affect the player's otherwise valid server session.
        logger.exception(
            "Unable to refresh HLLV spectator privileges for %s (%s)",
            name,
            player_id,
        )


# Steam enrichment is queued so a slow external API cannot block log processing.
@on_connected(0)
@inject_player_ids
def update_player_steaminfo_on_connect(
    rcon, struct_log: StructuredLogLineWithMetaData, _, player_id: str
):
    if not player_id:
        logger.error(
            "Can't update steam info, no steam id available for %s",
            struct_log.get("player_name_1"),
        )
        return

    event_time = struct_log.get("event_time")
    if not isinstance(event_time, datetime):
        timestamp_ms = struct_log.get("timestamp_ms")
        if isinstance(timestamp_ms, (int, float)):
            event_time = datetime.fromtimestamp(timestamp_ms / 1000, tz=UTC)
    elif event_time.tzinfo is None:
        event_time = event_time.replace(tzinfo=UTC)
    else:
        event_time = event_time.astimezone(UTC)

    if isinstance(event_time, datetime):
        event_age = datetime.now(tz=UTC) - event_time
        if event_age > STEAM_ENRICHMENT_MAX_EVENT_AGE:
            logger.info(
                "Skipping Steam enrichment for historical connection (%ds old)",
                int(event_age.total_seconds()),
            )
            return

    dedupe_key = f"{STEAM_ENRICHMENT_DEDUPE_PREFIX}:{get_server_number()}:{player_id}"
    red = get_redis_client()
    if not red.set(
        dedupe_key,
        "1",
        nx=True,
        ex=STEAM_ENRICHMENT_DEDUPE_SECONDS,
    ):
        logger.debug("Steam enrichment already queued recently for %s", player_id)
        return

    logger.info(
        "Queueing Steam enrichment for player %s %s",
        struct_log["player_name_1"],
        player_id,
    )
    try:
        get_queue().enqueue(
            update_player_steaminfo_on_connect_worker,
            struct_log["player_name_1"],
            player_id,
            job_timeout=60,
        )
    except Exception:
        red.delete(dedupe_key)
        raise


@on_connected()
@inject_player_ids
def windows_store_player_check(rcon: Rcon, _, name: str, player_id: str):
    config = RconServerSettingsUserConfig.load_from_db().windows_store_players

    if not config.enabled or not isinstance(player_id, str) or not player_id.strip():
        return
    if steam_utils.is_steam_id_64(player_id):
        return

    # Non-Steam / EOS IDs occur on PC and consoles. Only the explicit PC
    # Windows-GDK platform can justify this rule. Unknown formats, mismatched
    # identities and unavailable player information must never be punished.
    try:
        # The detailed-player helper is cached; a rapid reconnect on another
        # platform must not inherit a previous session's PC classification.
        details = rcon._get_adapted_player_info(player_id)
        if (not isinstance(details, dict) or str(details.get("iD") or "") != str(player_id)
                or not isinstance(details.get("platform"), str)
                or details["platform"].strip().lower().rsplit("::", 1)[-1] != "pc_wingdk"):
            logger.warning("Skipping Windows Store rule: player platform is not confirmed as PC WinGDK")
            return
    except Exception:
        logger.exception("Skipping Windows Store rule: player platform could not be verified")
        return

    action = config.action
    action_value = action.value if action else None

    logger.info(
        "Windows store player '%s' (%s) connected, action=%s",
        name,
        player_id,
        action_value,
    )

    try:
        if action == WindowsStoreIdActionType.kick:
            accepted = rcon.kick(
                player_id=player_id,
                player_name=name,
                reason=config.player_message,
                by=config.audit_message_author,
            )
        elif action == WindowsStoreIdActionType.temp_ban:
            accepted = rcon.temp_ban(
                player_id=player_id,
                duration_hours=config.temp_ban_length_hours,
                reason=config.player_message,
                by=config.audit_message_author,
            )
        elif action == WindowsStoreIdActionType.perma_ban:
            accepted = rcon.perma_ban(
                player_id=player_id,
                reason=config.player_message,
                by=config.audit_message_author,
            )
        else:
            return
    except Exception as e:
        logger.error(
            "Could not %s whitespace name player %s/%s: %s",
            action_value,
            name,
            player_id,
            e,
        )
        return
    if accepted is not True:
        logger.warning("Windows Store action was rejected or not confirmed; no success audit sent")
        return
    try:
        send_to_discord_audit(
            message=config.audit_message.format_map(
                DefaultStringFormat(name=name, player_id=player_id, action=action_value)
            ),
            command_name=str(action_value),
        )
    except Exception:
        logger.exception("Unable to send %s %s (%s) to audit", action_value, name, player_id)


def _set_real_vips(rcon: Rcon, struct_log):
    config = RealVipUserConfig.load_from_db()
    if not config.enabled:
        logger.debug("Real VIP is disabled")
        return

    desired_nb_vips = config.desired_total_number_vips
    min_vip_slot = config.minimum_number_vip_slots
    vip_count = rcon.get_vips_count()

    remaining_vip_slots = max(desired_nb_vips - vip_count, max(min_vip_slot, 0))
    rcon.set_vip_slots_num(remaining_vip_slots)
    logger.info("Real VIP set slots to %s", remaining_vip_slots)


@on_connected()
def do_real_vips(rcon: Rcon, struct_log):
    _set_real_vips(rcon, struct_log)


@on_disconnected
def undo_real_vips(rcon: Rcon, struct_log):
    _set_real_vips(rcon, struct_log)


@on_camera
def notify_camera(rcon: Rcon, struct_log):
    send_to_discord_audit(
        command_name="camera", message=struct_log["message"], by="CRCON"
    )
    short_name: Final = RconServerSettingsUserConfig.load_from_db().short_name

    try:
        if hooks := get_prepared_discord_hooks(CameraWebhooksUserConfig):
            embeded = DiscordEmbed(
                title=f'{escape_markdown(struct_log["player_name_1"])}  - {escape_markdown(struct_log["player_id_1"])}',
                description=f'{short_name} - {struct_log["sub_content"]}',
                color=242424,
            )
            for h in hooks:
                h.add_embed(embeded)
                h.execute()
    except Exception:
        logger.exception("Unable to forward to hooks")

    config = CameraNotificationUserConfig.load_from_db()
    if config.broadcast:
        temporary_broadcast(rcon, struct_log["message"], 60)

    if config.welcome:
        temporary_welcome(rcon, struct_log["message"], 60)
