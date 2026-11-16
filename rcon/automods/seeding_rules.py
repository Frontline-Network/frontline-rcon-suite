"""
Enforces the various seeding rules :
- disallowed roles
- disallowed weapons
- don't enter protected ennemy zone
"""

import logging
import pickle
from contextlib import contextmanager
from datetime import datetime, timedelta
from math import dist
from time import time as position_time
from typing import Literal
from uuid import uuid4

import redis

from rcon.automods.geofence import (
    is_outside_combat_area,
    is_spawned,
    normalize_world_position,
)
from rcon.automods.get_team_count import get_team_count
from rcon.automods.is_time import is_time
from rcon.automods.models import (
    ActionMethod,
    PENDING_WARNING,
    NoSeedingViolation,
    PunishDetails,
    PunishPlayer,
    PunishStepState,
    PunitionsToApply,
    WatchStatus,
    WarningConfirmationMixin,
    upgrade_legacy_warning_state,
)
from rcon.automods.num_or_inf import num_or_inf
from rcon.cache_utils import get_redis_client
from rcon.logs.loop import on_match_start
from rcon.maps import GameMode
from rcon.rcon import StructuredLogLineType
from rcon.types import GameStateType, GetDetailedPlayer, normalize_role
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig

SEEDING_RULES_RESET_SECS = 120
AUTOMOD_USERNAME = "AutoMod_SeedingRules"
SEEDING_RULE_NAMES = ["disallowed_roles", "disallowed_weapons", "enforce_cap_fight"]

# Positions are centimetres. These are conservative continuity checks, not
# player speed enforcement: allow vehicles and the normal five-second poll.
POSITION_POLL_SECONDS = 5
POSITION_MAX_SPEED_CM_PER_SECOND = 10_000
POSITION_MAX_SAMPLE_GAP_SECONDS = 30
SPAWN_PROOF_MAX_DISTANCE_CM = 50_000
SPAWN_PROOF_MIN_DISTANCE_CM = 100


def connection_key(player_id: str) -> str:
    return f"seeding_rules_automod_connection_{player_id}"


def disabled_rule_key(rule: str) -> str:
    """
    Global off switch for
    disallowed_roles, disallowed_weapons and enforce_cap_fight rules
    according to the min/max players parameters set for each
    """
    return f"seeding_rules_automod_disabled_for_round_{rule}"


@on_match_start
def on_map_change(_, _1):
    """
    Resets the global off switch on map change for
    disallowed_roles, disallowed_weapons and enforce_cap_fight rules
    according to the min/max players parameters set for each
    """
    keys = []
    for rule in SEEDING_RULE_NAMES:
        keys.append(disabled_rule_key(rule))
    if len(keys) == 0:
        return
    get_redis_client().delete(*keys)


class SeedingRulesAutomod(WarningConfirmationMixin):
    """
    Imported from rcon/automods/automod.py
    """

    logger: logging.Logger
    red: redis.StrictRedis
    config: AutoModSeedingUserConfig
    action_author = AUTOMOD_USERNAME

    def progress_key(self, aplayer):
        return aplayer.player_id

    def __init__(
        self, config: AutoModSeedingUserConfig, red: redis.StrictRedis or None
    ):
        self.logger = logging.getLogger(__name__)
        self.red = red
        self.config = config

    def enabled(self) -> bool:
        """
        Global on/off switch
        """
        return self.config.enabled

    def on_connected(
        self,
        name: str,
        player_id: str,
        detailed_player_info: GetDetailedPlayer | None = None,
    ) -> PunitionsToApply:
        """
        Sends a one-time seeding rules reminder message to players on connect
        """
        if not isinstance(player_id, str) or not player_id.strip():
            return PunitionsToApply()
        # Independent of announcements: an old squad watch can survive a short
        # disconnect. Invalidate its spawn proof even while profiles are cached.
        self.red.setex(connection_key(player_id), SEEDING_RULES_RESET_SECS, uuid4().hex)
        p: PunitionsToApply = PunitionsToApply()

        disallowed_roles = (
            set(self.config.disallowed_roles.roles.values())
            if self.config.disallowed_roles.enabled
            else set()
        )
        disallowed_weapons = (
            set(self.config.disallowed_weapons.weapons.values())
            if self.config.disallowed_weapons.enabled
            else set()
        )
        enforce_cap_fight_maxplayers = (
            self.config.enforce_cap_fight.max_players
            if self.config.enforce_cap_fight.enabled
            else 0
        )

        if self.config.announcement_enabled and (
            len(disallowed_roles) != 0
            or len(disallowed_weapons) != 0
            or enforce_cap_fight_maxplayers != 0
        ):
            if all([self._is_seeding_rule_disabled(r) for r in SEEDING_RULE_NAMES]):
                return p

            data = {
                "disallowed_roles": ", ".join(disallowed_roles),
                "disallowed_roles_max_players": self.config.disallowed_roles.max_players,
                "disallowed_weapons": ", ".join(disallowed_weapons),
                "disallowed_weapons_max_players": self.config.disallowed_weapons.max_players,
            }
            message = self.config.announcement_message
            try:
                message = message.format(**data)
            except KeyError:
                self.logger.warning(
                    "The automod message contains an invalid key for disallowed_roles and/or disallowed_weapons (%s)",
                    message,
                )

            author = AUTOMOD_USERNAME + ("-DryRun" if self.config.dry_run else "")

            p.warning.append(
                PunishPlayer(
                    player_id=player_id,
                    name=name,
                    squad="",
                    team="",
                    flags=[],
                    role="",
                    lvl=0,
                    details=PunishDetails(
                        author=author,
                        dry_run=self.config.dry_run,
                        discord_audit_url=self.config.discord_webhook_url,
                        message=message,
                    ),
                )
            )

        return p

    def on_kill(self, log: StructuredLogLineType) -> PunitionsToApply:
        """
        Observe weapon usage
        Punishes the trespasser if a kill using a forbidden weapon has been logged
        """
        p: PunitionsToApply = PunitionsToApply()

        if not isinstance(log.get("player_id_1"), str) or not log["player_id_1"].strip():
            return p

        if log[
            "weapon"
        ] in self.config.disallowed_weapons.weapons and not self._is_seeding_rule_disabled(
            "disallowed_weapons"
        ):
            author = AUTOMOD_USERNAME + ("-DryRun" if self.config.dry_run else "")

            aplayer = PunishPlayer(
                player_id=log["player_id_1"],
                name=log["player_name_1"],
                squad="",
                team="",
                flags=[],
                role="",
                lvl=0,
                details=PunishDetails(
                    author=author,
                    dry_run=self.config.dry_run,
                    discord_audit_url=self.config.discord_webhook_url,
                ),
            )
            data = {
                "player_name": aplayer.name,
                "weapon": self.config.disallowed_weapons.weapons.get(log["weapon"]),
            }
            message = self.config.disallowed_weapons.violation_message
            try:
                message = message.format(**data)
            except KeyError:
                self.logger.warning(
                    "The automod message for disallowed weapons (%s) contains an invalid key",
                    message,
                )
            aplayer.details.message = message

            p.punish.append(aplayer)

        return p

    @contextmanager
    def watch_state(self, team: str, squad_name: str):
        """
        Observe and actualize the current moderation step
        """
        # Name-keyed legacy histories cannot safely be attributed to an ID.
        # A separate expiring namespace starts fresh without escalating from an
        # ambiguous warning or affecting the legacy state during rollback.
        redis_key = f"seeding_rules_automod_id_v2{team.lower()}{str(squad_name).lower()}"
        watch_status = self.red.get(redis_key)
        if watch_status:
            watch_status = upgrade_legacy_warning_state(pickle.loads(watch_status))
        else:  # No punishments so far, starting a fresh one
            watch_status = WatchStatus()

        try:
            yield watch_status
        except NoSeedingViolation:
            self.logger.debug(
                "Squad %s - %s no seeding violation, clearing state", team, squad_name
            )
            self.red.delete(redis_key)
        else:
            self.red.setex(
                redis_key, SEEDING_RULES_RESET_SECS, pickle.dumps(watch_status)
            )

    def get_message(
        self,
        watch_status: WatchStatus,
        aplayer: PunishPlayer,
        violation_msg: str,
        method: ActionMethod,
    ):
        """
        Construct the message sent to the player
        according to the actual moderation step
        """
        data: dict[str, str | int] = {
            "violation": violation_msg,
        }

        if method == ActionMethod.MESSAGE:
            data["received_warnings"] = len(watch_status.warned.get(self.progress_key(aplayer)))
            data["max_warnings"] = self.config.number_of_warnings
            data["next_check_seconds"] = self.config.warning_interval_seconds

        if method == ActionMethod.PUNISH:
            data["received_punishes"] = len(watch_status.punished.get(self.progress_key(aplayer)))
            data["max_punishes"] = self.config.number_of_punishments
            data["next_check_seconds"] = self.config.punish_interval_seconds

        if method == ActionMethod.KICK:
            data["kick_grace_period"] = self.config.kick_grace_period_seconds

        data["player_name"] = aplayer.name
        data["squad_name"] = aplayer.squad

        base_message = {
            ActionMethod.MESSAGE: self.config.warning_message,
            ActionMethod.PUNISH: self.config.punish_message,
            ActionMethod.KICK: self.config.kick_message,
        }

        message = base_message[method]
        try:
            return message.format(**data)
        except KeyError:
            self.logger.warning(
                "The automod message of %s (%s) contains an invalid key",
                repr(method),
                message,
            )
            return message

    def _disable_for_round(self, rule: str):
        self.red.setex(disabled_rule_key(rule), 3 * 60 * 60, "1")

    def _enable_for_round(self, rule: str):
        self.red.delete(disabled_rule_key(rule))

    def _is_seeding_rule_disabled(self, rule: str) -> bool:
        if not getattr(self.config, rule).enabled:
            return True

        k = disabled_rule_key(rule)
        if not self.red.exists(k):
            return False

        v = self.red.get(disabled_rule_key(rule))
        if isinstance(v, bytes):
            v = v.decode()
        return v == "1"

    def player_punish_failed(self, aplayer):
        """
        A dead/unspawned player can't be punished
        Resets the timer from the last unsuccessful punish.
        """
        with self.watch_state(aplayer.team, aplayer.squad) as watch_status:
            try:
                if punishes := watch_status.punished.get(self.progress_key(aplayer)):
                    del punishes[-1]
            except Exception:
                self.logger.exception("tried to cleanup punished time but failed")

    def _refresh_position_context(
        self, watch_status: WatchStatus, player: dict
    ) -> bool:
        """Re-arm join protection when this player's connection changes.

        The existing compact profile's session count also catches reconnects if
        the log hook was missed. The connection token catches them before that
        cached profile updates. Neither changes another player's watch state.
        """
        player_id = player["player_id"]
        contexts = getattr(watch_status, "position_tracking_context", None)
        if contexts is None:
            contexts = {}
            watch_status.position_tracking_context = contexts
        previous = contexts.get(player_id)
        count = (player.get("profile") or {}).get("sessions_count")
        if type(count) is not int or count <= 0:
            count = None
        token = self.red.get(connection_key(player_id))
        if isinstance(token, bytes):
            token = token.decode()
        # Expiry of the short-lived hook marker is not another connection.
        if token is None and previous is not None:
            token = previous[1]
        current = (count, token)
        contexts[player_id] = current
        initial_positions = getattr(watch_status, "initial_world_positions", {})
        changed = previous != current and (
            previous is not None or player_id in initial_positions
        )
        if changed:
            # Keep a pending marker even if this reconnect has no coordinates.
            # Subsequent missing samples must not enable the offense fallback.
            if player_id in initial_positions:
                initial_positions[player_id] = (0.0, 0.0, 0.0)
            watch_status.initial_world_positions = initial_positions
            getattr(watch_status, "position_observations", {}).pop(player_id, None)
            getattr(watch_status, "combat_area_outside_player_ids", set()).discard(
                player_id
            )
            self._clear_player_progress(watch_status, player_id)
            watch_status.offensive_points.pop(player_id, None)
            self.logger.info(
                "Re-armed seeding spawn protection for %s after connection context changed",
                player_id,
            )
        return changed

    def _position_cap_violation(
        self,
        watch_status: WatchStatus,
        player: dict,
        team: Literal["axis", "allies"],
        game_state: GameStateType,
    ) -> bool | None:
        """Return a position-based decision while filtering bogus join samples.

        Cached coordinates can survive a reconnect before a stationary bogus
        HQ appears. Neither a teleport nor the first non-zero sample after a
        spawn screen proves movement. Require nearby movement, and re-arm on
        respawn, discontinuity or a gap in positional observations.
        """
        connection_changed = self._refresh_position_context(watch_status, player)
        position = normalize_world_position(player.get("world_position"))
        if position is None:
            if player["player_id"] in getattr(
                watch_status, "initial_world_positions", {}
            ):
                self._reset_position_proof(watch_status, player)
                getattr(watch_status, "position_observations", {}).pop(
                    player["player_id"], None
                )
                return False
            # Preserve the fallback for servers which supply no positions.
            # On reconnect, first establish a fresh offense-counter baseline.
            return False if connection_changed else None

        current_map = game_state.get("current_map")
        map_data = current_map.get("map") if isinstance(current_map, dict) else None
        map_id = (
            str(map_data["id"])
            if isinstance(map_data, dict) and map_data.get("id")
            else None
        )

        tracked_map_id = getattr(watch_status, "world_position_map_id", None)
        if tracked_map_id != map_id:
            watch_status.initial_world_positions = {}
            watch_status.position_observations = {}
            watch_status.combat_area_outside_player_ids = set()
            watch_status.world_position_map_id = map_id

        initial_positions = getattr(watch_status, "initial_world_positions", None)
        if initial_positions is None:
            # Pickles created before positional seeding detection do not have
            # the new dataclass fields. Upgrade them lazily in place.
            initial_positions = {}
            watch_status.initial_world_positions = initial_positions

        observations = getattr(watch_status, "position_observations", None)
        if observations is None:
            # Old Redis pickles have no continuity evidence: re-arm once.
            observations = {}
            watch_status.position_observations = observations
        player_id = player["player_id"]
        previous = observations.get(player_id)
        deaths = player.get("deaths")
        if type(deaths) is not int or deaths < 0:
            deaths = None
        now = position_time()
        observations[player_id] = (position, now, deaths)
        if not is_spawned(position) or previous is None or not is_spawned(previous[0]):
            self._reset_position_proof(watch_status, player, position)
            return False

        previous_position, observed_at, previous_deaths = previous
        elapsed = now - observed_at
        distance = dist(previous_position, position)
        if (
            elapsed < 0
            or elapsed > POSITION_MAX_SAMPLE_GAP_SECONDS
            or distance
            > POSITION_MAX_SPEED_CM_PER_SECOND * max(elapsed, POSITION_POLL_SECONDS)
            or (
                deaths is not None
                and previous_deaths is not None
                and deaths != previous_deaths
            )
        ):
            self.logger.debug(
                "Re-armed seeding spawn protection for %s: discontinuous position data",
                player_id,
            )
            self._reset_position_proof(watch_status, player, position)
            return False

        initial_position = initial_positions.get(player_id, position)
        if initial_position is not None:
            distance_from_anchor = dist(initial_position, position)
            if distance_from_anchor > SPAWN_PROOF_MAX_DISTANCE_CM:
                self._reset_position_proof(watch_status, player, position)
                return False
            if distance_from_anchor < SPAWN_PROOF_MIN_DISTANCE_CM:
                return False
            initial_positions[player_id] = None

        if map_id is None:
            # Unknown geometry can use offense points, but only after the same
            # spawn checks. A pending HQ placeholder is not a fallback signal.
            return None
        return is_outside_combat_area(
            position,
            map_id=map_id,
            team=team,
            max_caps=self.config.enforce_cap_fight.max_caps,
        )

    def _reset_position_proof(
        self,
        watch_status: WatchStatus,
        player: dict,
        position: tuple[float, float, float] = (0.0, 0.0, 0.0),
    ) -> None:
        """Untrusted spawn data cannot carry an old escalation into a new life."""
        player_id = player["player_id"]
        outside_ids = getattr(watch_status, "combat_area_outside_player_ids", set())
        had_proof = (
            watch_status.initial_world_positions.get(player_id, position) is None
        )
        was_outside = player_id in outside_ids
        watch_status.initial_world_positions[player_id] = position
        outside_ids.discard(player_id)
        if had_proof or was_outside:
            self._clear_player_progress(watch_status, player_id)
        watch_status.offensive_points.pop(player_id, None)

    @staticmethod
    def _clear_player_progress(watch_status: WatchStatus, player_id: str) -> None:
        """Start warnings and punishments fresh for a new boundary excursion."""
        for states in (watch_status.noted, watch_status.warned, watch_status.punished):
            states.pop(player_id, None)

    def _update_combat_area_excursion(
        self,
        watch_status: WatchStatus,
        *,
        player_id: str,
        player_name: str,
        outside: bool,
    ) -> None:
        """Track transitions instead of treating every five-second poll as new."""
        outside_player_ids = getattr(
            watch_status, "combat_area_outside_player_ids", None
        )
        if outside_player_ids is None:
            # Upgrade WatchStatus pickles written before excursion tracking.
            outside_player_ids = set()
            watch_status.combat_area_outside_player_ids = outside_player_ids

        was_outside = player_id in outside_player_ids
        if outside:
            if not was_outside:
                self._clear_player_progress(watch_status, player_id)
                outside_player_ids.add(player_id)
            return

        if was_outside:
            outside_player_ids.discard(player_id)
            self._clear_player_progress(watch_status, player_id)

    def punitions_to_apply(
        self,
        team_view,
        squad_name: str,
        team: Literal["axis", "allies"],
        squad: dict,
        game_state: GameStateType,
    ) -> PunitionsToApply:
        """
        Observe all squads/players
        Find the ones who trespass rules
        Sends them to their next moderation step
        """
        self.logger.debug("Squad %s %s", squad_name, squad)
        punitions_to_apply = PunitionsToApply()

        server_player_count = get_team_count(team_view, "allies") + get_team_count(
            team_view, "axis"
        )

        # dont_do_anything_below_this_number_of_players
        if (
            server_player_count
            < self.config.dont_do_anything_below_this_number_of_players
        ):
            self.logger.debug("Server below min player count : disabling")
            return punitions_to_apply

        if not squad_name or squad_name.strip().lower() in ("", "unassigned"):
            # HLL can report an arbitrary (even enemy) HQ before squad/spawn
            # selection. Neither that coordinate nor delayed offense points
            # establish a violation. Commander is a separate, valid group.
            self.logger.debug("Skipping unassigned players - (%s) %s", team, squad_name)
            return punitions_to_apply

        with self.watch_state(team, squad_name) as watch_status:

            # if squad_name is None or squad is None:
            #     raise NoSeedingViolation()

            author = AUTOMOD_USERNAME + ("-DryRun" if self.config.dry_run else "")

            for player in squad["players"]:
                if not isinstance(player.get("player_id"), str) or not player["player_id"].strip():
                    self.logger.warning("Skipping seeding check for player without a stable ID")
                    continue
                profile = player.get("profile", {})
                aplayer = PunishPlayer(
                    player_id=player["player_id"],
                    name=player["name"],
                    squad=squad_name,
                    team=team,
                    flags=profile.get("flags") if profile else [],
                    role=player.get("role"),
                    lvl=int(player.get("level")),
                    details=PunishDetails(
                        author=author,
                        dry_run=self.config.dry_run,
                        discord_audit_url=self.config.discord_webhook_url,
                    ),
                )

                drc = self.config.disallowed_roles
                if (
                    server_player_count < drc.min_players
                    or server_player_count >= drc.max_players
                ):
                    self._disable_for_round("disallowed_roles")
                else:
                    self._enable_for_round("disallowed_roles")

                dwc = self.config.disallowed_weapons
                if (
                    server_player_count < dwc.min_players
                    or server_player_count >= dwc.max_players
                ):
                    self._disable_for_round("disallowed_weapons")
                else:
                    self._enable_for_round("disallowed_weapons")

                ecf = self.config.enforce_cap_fight
                if (
                    server_player_count < ecf.min_players
                    or server_player_count >= ecf.max_players
                ):
                    self._disable_for_round("enforce_cap_fight")
                else:
                    self._enable_for_round("enforce_cap_fight")

                violations = []

                if (
                    not self._is_seeding_rule_disabled("disallowed_roles")
                    and drc.min_players <= server_player_count < drc.max_players
                ):
                    normalized_role = normalize_role(aplayer.role)
                    if normalized_role in drc.roles:
                        violations.append(
                            drc.violation_message.format(
                                role=drc.roles.get(normalized_role)
                            )
                        )

                if game_state["game_mode"] != GameMode.WARFARE:
                    self._disable_for_round("enforce_cap_fight")

                cap_rule_active = not self._is_seeding_rule_disabled(
                    "enforce_cap_fight"
                )
                combat_area_violation = False
                position_violation = (
                    self._position_cap_violation(watch_status, player, team, game_state)
                    if cap_rule_active
                    else None
                )
                team_reached_cap_limit = (
                    team == "axis" and game_state["axis_score"] >= ecf.max_caps
                ) or (team == "allies" and game_state["allied_score"] >= ecf.max_caps)

                # A known position enforces the same boundary for both teams,
                # including the team that does not currently hold the middle.
                # Only the offense-points fallback needs the score guard: the
                # losing team also earns offense points in the allowed middle.
                if cap_rule_active and (
                    position_violation is not None or team_reached_cap_limit
                ):
                    if position_violation is not None:
                        self._update_combat_area_excursion(
                            watch_status,
                            player_id=aplayer.player_id,
                            player_name=aplayer.name,
                            outside=position_violation,
                        )

                    self.logger.debug(
                        "Checking %s combat area: position=%s, fallback eligible=%s",
                        team,
                        position_violation,
                        team_reached_cap_limit,
                    )
                    op = player["offense"]
                    oop = watch_status.offensive_points.setdefault(aplayer.player_id, -1)

                    self.logger.debug(
                        "Player had %s offensive points last and now %s",
                        str(oop),
                        str(op),
                    )
                    if position_violation is True or (
                        position_violation is None and oop != -1 and oop < op
                    ):
                        violations.append(ecf.violation_message)
                        combat_area_violation = True

                        detection = (
                            "world position"
                            if position_violation is True
                            else "offensive-points fallback"
                        )
                        self.logger.info(
                            "Detected seeding combat-area violation for %s via %s",
                            aplayer.short_repr(),
                            detection,
                        )

                        if ecf.skip_warning and self.config.number_of_warnings > 0:
                            warnings = watch_status.warned.setdefault(aplayer.player_id, [])
                            missing_warnings = max(
                                0, self.config.number_of_warnings - len(warnings)
                            )
                            for _ in range(missing_warnings):
                                warnings.append(
                                    datetime.now()
                                    - timedelta(
                                        seconds=self.config.warning_interval_seconds + 1
                                    )
                                )
                    watch_status.offensive_points[aplayer.player_id] = op
                else:
                    watch_status.offensive_points.clear()
                    self._update_combat_area_excursion(
                        watch_status,
                        player_id=aplayer.player_id,
                        player_name=aplayer.name,
                        outside=False,
                    )

                if len(violations) == 0:
                    continue

                violation_msg = ", ".join(violations)

                # Note (not applicable)

                # Warning
                state = self.should_warn_player(watch_status, squad_name, aplayer)

                if state == PunishStepState.APPLY:
                    aplayer.details.message = self.get_message(
                        watch_status, aplayer, violation_msg, ActionMethod.MESSAGE
                    )
                    punitions_to_apply.warning.append(aplayer)
                    punitions_to_apply.add_squad_state(team, squad_name, squad)

                if state == PunishStepState.WAIT:
                    # only here to make the tests pass, otherwise useless
                    punitions_to_apply.add_squad_state(team, squad_name, squad)

                if state not in [
                    PunishStepState.DISABLED,
                    PunishStepState.GO_TO_NEXT_STEP,
                ]:
                    continue

                # Punish
                state = self.should_punish_player(
                    watch_status,
                    team_view,
                    squad_name,
                    squad,
                    aplayer,
                    repeat_when_kick_disabled=combat_area_violation,
                )

                if state == PunishStepState.APPLY:
                    aplayer.details.message = self.get_message(
                        watch_status, aplayer, violation_msg, ActionMethod.PUNISH
                    )
                    punitions_to_apply.punish.append(aplayer)
                    punitions_to_apply.add_squad_state(team, squad_name, squad)

                if state not in [
                    PunishStepState.DISABLED,
                    PunishStepState.GO_TO_NEXT_STEP,
                ]:
                    continue

                # Kick
                state = self.should_kick_player(
                    watch_status, team_view, squad_name, squad, aplayer
                )

                if state == PunishStepState.APPLY:
                    aplayer.details.message = self.get_message(
                        watch_status, aplayer, violation_msg, ActionMethod.KICK
                    )
                    punitions_to_apply.kick.append(aplayer)
                    punitions_to_apply.add_squad_state(team, squad_name, squad)

                if state not in [
                    PunishStepState.DISABLED,
                    PunishStepState.GO_TO_NEXT_STEP,
                ]:
                    continue

        return punitions_to_apply

    # (not applicable)
    # def should_note_player()

    def should_warn_player(
        self, watch_status: WatchStatus, squad_name: str, aplayer: PunishPlayer
    ):
        """
        Send a message to trespassers
        telling them they must follow the rules
        before being punished and kicked
        """
        # number_of_warnings
        if self.config.number_of_warnings == 0:
            self.logger.debug("Warnings are disabled. number_of_warning is set to 0")
            return PunishStepState.DISABLED

        # whitelist_flags
        if any(
            flag_entry.flag in self.config.whitelist_flags
            for flag_entry in aplayer.flags
        ):
            self.logger.debug("%s is immune to warnings", aplayer.short_repr())
            return PunishStepState.IMMUNED

        # immune_roles
        # immune_player_level
        if (
            aplayer.lvl <= self.config.immune_player_level
            or aplayer.role in self.config.immune_roles
        ):
            self.logger.debug("%s is immune to warnings", aplayer.short_repr())
            return PunishStepState.IMMUNED

        warnings = watch_status.warned.setdefault(aplayer.player_id, [])

        # warning_interval_seconds
        if not is_time(warnings, self.config.warning_interval_seconds):
            self.logger.debug(
                "Waiting to warn: %s in %s", aplayer.short_repr(), squad_name
            )
            return PunishStepState.WAIT

        # number_of_warnings
        if (
            len(warnings) < self.config.number_of_warnings
            or self.config.number_of_warnings == -1
        ):
            self.logger.info(
                "%s Will be warned (%s/%s)",
                aplayer.short_repr(),
                len(warnings),
                num_or_inf(self.config.number_of_warnings),
            )
            warnings.append(PENDING_WARNING)
            return PunishStepState.APPLY

        self.logger.info(
            "%s Max warnings reached (%s/%s). Moving on to punish.",
            aplayer.short_repr(),
            len(warnings),
            self.config.number_of_warnings,
        )
        return PunishStepState.GO_TO_NEXT_STEP

    def should_punish_player(
        self,
        watch_status: WatchStatus,
        team_view,
        squad_name: str,
        squad,
        aplayer: PunishPlayer,
        *,
        repeat_when_kick_disabled: bool = False,
    ):
        """
        Punish (kill) trespassers
        telling them they must follow the rules
        before being kicked
        """
        # number_of_punishments
        if self.config.number_of_punishments == 0:
            self.logger.debug("Punish is disabled")
            return PunishStepState.DISABLED

        # whitelist_flags
        if any(
            flag_entry.flag in self.config.whitelist_flags
            for flag_entry in aplayer.flags
        ):
            self.logger.debug("%s is immune to punishment", aplayer.short_repr())
            return PunishStepState.IMMUNED

        # immune_roles
        # immune_player_level
        if (
            aplayer.lvl <= self.config.immune_player_level
            or aplayer.role in self.config.immune_roles
        ):
            self.logger.debug("%s is immune to punishment", aplayer.short_repr())
            return PunishStepState.IMMUNED

        # min_squad_players_for_punish
        if len(squad["players"]) < self.config.min_squad_players_for_punish:
            self.logger.debug("Squad %s below min player count for punish", squad_name)
            return PunishStepState.WAIT

        # min_server_players_for_punish
        if (
            get_team_count(team_view, "allies") + get_team_count(team_view, "axis")
        ) < self.config.min_server_players_for_punish:
            self.logger.debug("Server below min player count for punish")
            return PunishStepState.WAIT

        punishes = watch_status.punished.setdefault(aplayer.player_id, [])

        # punish_interval_seconds
        if not is_time(punishes, self.config.punish_interval_seconds):
            self.logger.debug("Waiting to punish %s", squad_name)
            return PunishStepState.WAIT

        # number_of_punishments
        if (
            len(punishes) < self.config.number_of_punishments
            or self.config.number_of_punishments == -1
        ):
            self.logger.info(
                "%s Will be punished (%s/%s)",
                aplayer.short_repr(),
                len(punishes),
                num_or_inf(self.config.number_of_punishments),
            )
            punishes.append(datetime.now())
            return PunishStepState.APPLY

        if not self.config.kick_after_max_punish and repeat_when_kick_disabled:
            # A disabled kick must not leave an outside player permanently
            # unmoderated after the finite punishment counter is exhausted.
            # Keep a bounded rolling window so the configured interval still
            # controls repetition without growing Redis state indefinitely.
            keep = max(0, self.config.number_of_punishments - 1)
            if keep:
                del punishes[:-keep]
            else:
                punishes.clear()
            self.logger.info(
                "%s Kick disabled; repeating punishment after configured interval",
                aplayer.short_repr(),
            )
            punishes.append(datetime.now())
            return PunishStepState.APPLY

        self.logger.info(
            "%s Max punish reached (%s/%s)",
            aplayer.short_repr(),
            len(punishes),
            self.config.number_of_punishments,
        )
        return PunishStepState.GO_TO_NEXT_STEP

    def should_kick_player(
        self,
        watch_status: WatchStatus,
        team_view,
        squad_name: str,
        squad,
        aplayer: PunishPlayer,
    ):
        """
        Kick (disconnect) trespassers
        telling them they must follow the rules
        """
        # kick_after_max_punish
        if not self.config.kick_after_max_punish:
            self.logger.debug("Kick is disabled")
            return PunishStepState.DISABLED

        # whitelist_flags
        if any(
            flag_entry.flag in self.config.whitelist_flags
            for flag_entry in aplayer.flags
        ):
            self.logger.debug("%s is immune to kick", aplayer.short_repr())
            return PunishStepState.IMMUNED

        # immune_roles
        # immune_player_level
        if (
            aplayer.lvl <= self.config.immune_player_level
            or aplayer.role in self.config.immune_roles
        ):
            self.logger.debug("%s is immune to kick", aplayer.short_repr())
            return PunishStepState.IMMUNED

        # min_squad_players_for_kick
        if len(squad["players"]) < self.config.min_squad_players_for_kick:
            self.logger.debug("Squad %s below min player count for punish", squad_name)
            return PunishStepState.WAIT

        # min_server_players_for_kick
        if (
            get_team_count(team_view, "allies") + get_team_count(team_view, "axis")
        ) < self.config.min_server_players_for_kick:
            self.logger.debug("Server below min player count for punish")
            return PunishStepState.WAIT

        try:
            last_time = watch_status.punished.get(aplayer.player_id, [])[-1]
        except IndexError:
            self.logger.error("Trying to kick player without prior punishes")
            return PunishStepState.DISABLED

        # kick_grace_period_seconds
        if datetime.now() - last_time < timedelta(
            seconds=self.config.kick_grace_period_seconds
        ):
            return PunishStepState.WAIT

        return PunishStepState.APPLY
