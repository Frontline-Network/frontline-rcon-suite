import logging
from threading import Timer
from typing import List

from pydantic import HttpUrl
from redis.client import Redis

import rcon.game_logs
from rcon.automods import action_guard, event_guard
from rcon.automods.level_thresholds import LevelThresholdsAutomod
from rcon.automods.models import ActionMethod, PunishPlayer, PunitionsToApply
from rcon.automods.no_leader import NoLeaderAutomod
from rcon.automods.no_solotank import NoSoloTankAutomod
from rcon.automods.seeding_rules import SeedingRulesAutomod
from rcon.cache_utils import get_redis_client
from rcon.commands import HLLCommandFailedError
from rcon.connection import HLLCommandError, HLLServerError
from rcon.discord import send_to_discord_audit
from rcon.hooks import inject_player_ids
from rcon.logs.loop import on_connected, on_kill
from rcon.rcon import Rcon, get_rcon
from rcon.service_runtime import stopping, wait
from rcon.types import GetDetailedPlayer, StructuredLogLineType, StructuredLogLineWithMetaData
from rcon.user_config.auto_mod_level import AutoModLevelUserConfig
from rcon.user_config.auto_mod_no_leader import AutoModNoLeaderUserConfig
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig
from rcon.user_config.auto_mod_solo_tank import AutoModNoSoloTankUserConfig
from rcon.utils import get_server_number

logger = logging.getLogger(__name__)
first_run_done_key = "first_run_done"


class WarningRejected(HLLCommandFailedError):
    """The game server explicitly rejected a warning."""


class PunishmentRejected(HLLCommandFailedError):
    """The game server explicitly rejected a punishment."""


class KickRejected(HLLCommandFailedError):
    """The game server explicitly rejected a kick."""


def _originating_moderators(mods, aplayer):
    # Weapon-kill hooks have no squad watch. Do not create an empty shared
    # squad key for those independent event-based actions.
    if not aplayer.team or not aplayer.squad:
        return []
    suffix = "-DryRun" if aplayer.details.dry_run else ""
    authors = {aplayer.details.author, *aplayer.related_authors}
    return [
        mod for mod in mods
        if getattr(mod, "action_author", None) is not None
        and mod.action_author + suffix in authors
    ]


def get_punitions_to_apply(rcon, moderators) -> PunitionsToApply:
    logger.debug("Getting team info")
    team_view = rcon.get_team_view(compact=True)
    gamestate = rcon.get_gamestate()
    punitions_to_apply = PunitionsToApply()

    for team in ["allies", "axis"]:
        if not team_view.get(team):
            continue

        if team_view[team]["commander"] is not None:
            for mod in moderators:
                punitions_to_apply.merge(
                    mod.punitions_to_apply(
                        team_view,
                        "Commander",
                        team,
                        {
                            "players": [team_view[team]["commander"]],
                        },
                        gamestate,
                    )
                )

        for squad_name, squad in team_view[team]["squads"].items():
            for mod in moderators:
                punitions_to_apply.merge(
                    mod.punitions_to_apply(
                        team_view, squad_name, team, squad, gamestate
                    )
                )

    return punitions_to_apply


def _do_punitions(
    rcon: Rcon,
    method: ActionMethod,
    players: List[PunishPlayer],
    mods,
    event: tuple[int, str] | None = None,
):
    for aplayer in players:
        action_confirmed = False
        guard_token = None
        guard_server = None
        guard_rules = sorted({aplayer.details.author, *aplayer.related_authors})
        if not aplayer.details.dry_run and method in {ActionMethod.MESSAGE, ActionMethod.PUNISH, ActionMethod.KICK}:
            try:
                guard_server = int(get_server_number())
                if event is None:
                    guard_token = action_guard.reserve(guard_server, aplayer.player_id, guard_rules, method.name.lower())
                else:
                    guard_token = action_guard.reserve(guard_server, aplayer.player_id, guard_rules, method.name.lower(), event=event)
            except Exception:
                logger.exception("Automod action not sent: durable reservation unavailable")
                continue
            if guard_token is None:
                logger.warning("Automod action held by transition, event deduplication, or an earlier unconfirmed action")
                continue

        def settle_guard(result):
            if guard_token is None:
                return True
            try:
                if event is None:
                    action_guard.finish(guard_server, aplayer.player_id, guard_token, result, expected=len(guard_rules))
                else:
                    action_guard.finish(guard_server, aplayer.player_id, guard_token, result,
                                        expected=len(guard_rules), event_expected=len(guard_rules))
                return True
            except Exception:
                logger.exception("Automod action outcome could not be saved; reservation retained")
                return False

        def close_unsuccessful_attempt(reason):
            # Mark this particular event reviewed rather than rejected: rejected
            # event reservations are eligible for replay of the same log line.
            # The watch state stays pending until the current violation resets.
            if guard_token is None:
                return
            try:
                action_guard.review(guard_server, aplayer.player_id, guard_token,
                                    'Automod', reason)
            except Exception:
                logger.exception('Could not record the unsuccessful automod attempt')

        try:
            if method == ActionMethod.MESSAGE:
                if not aplayer.details.dry_run:
                    accepted = rcon.message_player(
                        aplayer.player_id,
                        aplayer.details.message,
                        by=aplayer.details.author,
                        player_name=aplayer.name,
                    )
                    if accepted is False:
                        raise WarningRejected("Game server rejected warning")
                    if accepted is not True:
                        raise HLLCommandFailedError("Game server did not confirm warning")
                action_confirmed = True
                if not settle_guard("confirmed"):
                    continue
                for moderator in _originating_moderators(mods, aplayer):
                    moderator.player_warning_succeeded(aplayer)
                audit(
                    discord_webhook_url=aplayer.details.discord_audit_url,
                    command_name="message_player",
                    msg=f"-> WARNING: {aplayer}",
                    author=aplayer.details.author,
                )

            if method == ActionMethod.PUNISH:
                for moderator in _originating_moderators(mods, aplayer):
                    moderator.player_punish_started(aplayer)
                if not aplayer.details.dry_run:
                    accepted = rcon.punish(
                        player_name=aplayer.name,
                        reason=aplayer.details.message,
                        by=aplayer.details.author,
                        player_id=aplayer.player_id,
                    )
                    if accepted is False:
                        raise PunishmentRejected("Game server rejected punishment")
                    if accepted is not True:
                        raise HLLCommandFailedError("Game server did not confirm punishment")
                action_confirmed = True
                if not settle_guard("confirmed"):
                    continue
                for moderator in _originating_moderators(mods, aplayer):
                    moderator.player_punish_succeeded(aplayer)
                audit(
                    discord_webhook_url=aplayer.details.discord_audit_url,
                    command_name="punish",
                    msg=f"--> PUNISHING: {aplayer}",
                    author=aplayer.details.author,
                )

            if method == ActionMethod.KICK:
                for moderator in _originating_moderators(mods, aplayer):
                    moderator.player_kick_attempted(aplayer)
                if not aplayer.details.dry_run:
                    accepted = rcon.kick(
                        player_name=aplayer.name,
                        reason=aplayer.details.message,
                        by=aplayer.details.author,
                        player_id=aplayer.player_id,
                    )
                    if accepted is False:
                        raise KickRejected("Game server rejected kick")
                    if accepted is not True:
                        raise HLLCommandFailedError("Game server did not confirm kick")
                action_confirmed = True
                if not settle_guard("confirmed"):
                    continue
                audit(
                    discord_webhook_url=aplayer.details.discord_audit_url,
                    command_name="kick",
                    msg=f"---> KICKING <---: {aplayer}",
                    author=aplayer.details.author,
                )
        except WarningRejected:
            logger.warning("Game server rejected automod warning")
            close_unsuccessful_attempt('Game server rejected the warning')
        except PunishmentRejected:
            logger.warning("Game server rejected automod punishment")
            close_unsuccessful_attempt('Game server rejected the punishment')
        except KickRejected:
            logger.warning("Game server rejected automod kick; it can be retried")
            for moderator in _originating_moderators(mods, aplayer):
                moderator.player_kick_rejected(aplayer)
            settle_guard("rejected")
        except (HLLCommandFailedError, HLLServerError, OSError, UnicodeDecodeError) as exc:
            if action_confirmed:
                logger.warning("Automod action confirmed but follow-up failed", exc_info=True)
                continue
            logger.warning(
                "Couldn't confirm `%s` for player `%s`; warning delivery may be uncertain.",
                repr(method),
                repr(aplayer),
                exc_info=True,
            )
            if method in {ActionMethod.MESSAGE, ActionMethod.PUNISH}:
                reason = (f'Game server returned status {exc.status_code}'
                          if isinstance(exc, HLLCommandError)
                          else 'Response not confirmed; do not replay this attempt')
                close_unsuccessful_attempt(reason)


def do_punitions(
    rcon: Rcon,
    punitions_to_apply: PunitionsToApply,
    mods: list | None = None,
    event: tuple[int, str] | None = None,
):
    if punitions_to_apply:
        logger.debug(
            "Automod will apply the following punitions %s",
            repr(punitions_to_apply),
        )
    else:
        logger.debug("Automod did not suggest any punitions")

    mods = enabled_moderators() if mods is None else mods

    if event is None:
        _do_punitions(rcon, ActionMethod.MESSAGE, punitions_to_apply.warning, mods)
        _do_punitions(rcon, ActionMethod.PUNISH, punitions_to_apply.punish, mods)
        _do_punitions(rcon, ActionMethod.KICK, punitions_to_apply.kick, mods)
        return

    _do_punitions(rcon, ActionMethod.MESSAGE, punitions_to_apply.warning, mods, event=event)
    _do_punitions(rcon, ActionMethod.PUNISH, punitions_to_apply.punish, mods, event=event)
    _do_punitions(rcon, ActionMethod.KICK, punitions_to_apply.kick, mods, event=event)


def enabled_moderators():
    red = get_redis_client()

    level_thresholds_config = AutoModLevelUserConfig.load_from_db()
    no_leader_config = AutoModNoLeaderUserConfig.load_from_db()
    seeding_config = AutoModSeedingUserConfig.load_from_db()
    solo_tank_config = AutoModNoSoloTankUserConfig.load_from_db()

    return list(
        filter(
            lambda m: m.enabled(),
            [
                NoLeaderAutomod(no_leader_config, red),
                SeedingRulesAutomod(seeding_config, red),
                LevelThresholdsAutomod(level_thresholds_config, red),
                NoSoloTankAutomod(solo_tank_config, red),
            ],
        )
    )


def is_first_run_done(r: Redis) -> bool:
    return r.exists(first_run_done_key) == 1


def set_first_run_done(r: Redis):
    r.setex(first_run_done_key, 4 * 60, "1")


def punish_squads(rcon: Rcon, r: Redis):
    mods = enabled_moderators()
    if len(mods) == 0:
        logger.debug("No automod is enabled")
        return

    punitions_to_apply = get_punitions_to_apply(rcon, mods)

    do_punitions(rcon, punitions_to_apply, mods)
    set_first_run_done(r)


def audit(
    discord_webhook_url: HttpUrl | None, command_name: str, msg: str, author: str
):
    if discord_webhook_url is not None:
        send_to_discord_audit(
            message=msg,
            command_name=command_name,
            by=author,
            webhookurls=[discord_webhook_url],
            silent=False,
        )


@on_kill
def on_kill(rcon: Rcon, log: StructuredLogLineWithMetaData):
    red = get_redis_client()
    if not is_first_run_done(red):
        logger.debug(
            "Kill event received, but not automod run done yet, "
            "giving mods time to warmup"
        )
        return
    mods = enabled_moderators()
    if len(mods) == 0:
        logger.debug("No automod is enabled")
        return

    try:
        event = event_guard.identity(log)
    except ValueError:
        logger.warning("Automod kill action skipped: event identity is unavailable")
        return

    punitions_to_apply = PunitionsToApply()
    for mod in mods:
        on_kill_hook = getattr(mod, "on_kill", None)
        if callable(on_kill_hook):
            punitions_to_apply.merge(mod.on_kill(log))

    do_punitions(rcon, punitions_to_apply, mods, event=event)


pendingTimers: dict[str, Timer] = {}


def _remove_pending_timer(player_id: str, timer: Timer) -> None:
    if pendingTimers.get(player_id) is timer:
        pendingTimers.pop(player_id, None)


def _send_connect_warning(rcon: Rcon, player: PunishPlayer) -> None:
    """Keep a lost connect-warning response from causing a duplicate on reconnect."""
    if player.details.dry_run:
        return
    rules = sorted({player.details.author, *player.related_authors})
    try:
        server = int(get_server_number())
        token = action_guard.reserve(server, player.player_id, rules, "message")
    except Exception:
        logger.exception("Connect warning not sent: durable reservation unavailable")
        return
    if token is None:
        logger.warning("Connect warning not sent: an earlier action awaits review")
        return
    try:
        accepted = rcon.message_player(
            player_id=player.player_id, message=player.details.message,
            by=player.details.author, save_message=False,
        )
        if accepted is True:
            action_guard.finish(server, player.player_id, token, "confirmed", expected=len(rules))
        else:
            logger.warning("Connect warning failed or was not confirmed")
            action_guard.review(server, player.player_id, token, 'Automod',
                                'Warning failed or response was unconfirmed')
    except Exception:
        logger.exception("Connect warning failed or response was unconfirmed")
        try:
            action_guard.review(server, player.player_id, token, 'Automod',
                                'Warning failed or response was unconfirmed')
        except Exception:
            logger.exception("Could not record the unsuccessful connect warning")


@on_connected()
@inject_player_ids
def on_connected(rcon: Rcon, _, name: str, player_id: str):
    previous = pendingTimers.pop(player_id, None)
    if previous is not None:
        previous.cancel()
    red = get_redis_client()
    if not is_first_run_done(red):
        logger.debug(
            "Kill event received, but not automod run done yet, "
            "giving mods time to warmup"
        )
        return
    mods = enabled_moderators()
    if len(mods) == 0:
        logger.debug("No automod is enabled")
        return

    # get detailed player info for use by on_connected_hook
    detailed_player_info: GetDetailedPlayer | None = None
    try:
        detailed_player_info = rcon.get_detailed_player_info(player_id)
    except Exception as e:
        logger.error(
            f"get_detailed_player_info threw an exception for {player_id}: {e}"
        )

    punitions_to_apply: PunitionsToApply = PunitionsToApply()
    for mod in mods:
        on_connected_hook = getattr(mod, "on_connected", None)
        if callable(on_connected_hook):
            punitions_to_apply.merge(
                mod.on_connected(name, player_id, detailed_player_info)
            )

    t: Timer | None = None

    def notify_player():
        try:
            if t is None or pendingTimers.get(player_id) is not t:
                return
            for p in punitions_to_apply.warning:
                _send_connect_warning(rcon, p)
        except Exception as e:
            logger.error("Could not message player '%s' (%s) : %s", name, player_id, e)
        finally:
            if t is not None:
                _remove_pending_timer(player_id, t)

    if len(punitions_to_apply.warning) == 0:
        return

    # The player might not yet have finished connecting in order to send messages.
    t = Timer(20, notify_player)
    t.daemon = True
    pendingTimers[player_id] = t
    t.start()


def run(stop_event=None):
    rcon = get_rcon()
    red = get_redis_client()

    while not stopping(stop_event):
        try:
            punish_squads(rcon, red)
            if wait(stop_event, 5):
                return
        except Exception:
            logger.exception("Squad automod: Something unexpected happened")
            raise
