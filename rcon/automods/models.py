import logging
from dataclasses import field
from datetime import datetime
from enum import Enum, auto
from typing import List, Mapping, Optional, TypedDict

from pydantic import HttpUrl
from pydantic.dataclasses import dataclass

logger = logging.getLogger(__name__)

# Stored using the existing datetime representation so that older workers can
# still unpickle a watch state during a rollback. A pending warning never
# advances the warning timer until delivery is confirmed.
PENDING_WARNING = datetime.max


class WarningConfirmationMixin:
    """Keep a planned warning pending until the game server confirms it."""

    def progress_key(self, aplayer):
        return aplayer.player_id

    def player_warning_succeeded(self, aplayer):
        with self.watch_state(aplayer.team, aplayer.squad) as status:
            warnings = status.warned.get(self.progress_key(aplayer))
            if warnings and warnings[-1] == PENDING_WARNING:
                warnings[-1] = datetime.now()

    def player_warning_failed(self, aplayer):
        with self.watch_state(aplayer.team, aplayer.squad) as status:
            warnings = status.warned.get(self.progress_key(aplayer))
            if warnings and warnings[-1] == PENDING_WARNING:
                warnings.pop()

    def player_punish_started(self, aplayer):
        """Reserve a punishment before sending it to the game server."""
        with self.watch_state(aplayer.team, aplayer.squad) as status:
            punishes = status.punished.setdefault(self.progress_key(aplayer), [])
            if punishes:
                punishes[-1] = PENDING_WARNING
            else:
                punishes.append(PENDING_WARNING)

    def player_punish_succeeded(self, aplayer):
        with self.watch_state(aplayer.team, aplayer.squad) as status:
            punishes = status.punished.get(self.progress_key(aplayer))
            if punishes and punishes[-1] == PENDING_WARNING:
                punishes[-1] = datetime.now()

    def player_kick_attempted(self, aplayer):
        """Reserve the kick before sending, so a crash cannot trigger a replay."""
        with self.watch_state(aplayer.team, aplayer.squad) as status:
            punishes = status.punished.setdefault(self.progress_key(aplayer), [])
            if not punishes or punishes[-1] != PENDING_WARNING:
                punishes.append(PENDING_WARNING)

    def player_kick_rejected(self, aplayer):
        with self.watch_state(aplayer.team, aplayer.squad) as status:
            punishes = status.punished.get(self.progress_key(aplayer))
            if punishes and punishes[-1] == PENDING_WARNING:
                punishes.pop()


class SquadHasLeader(Exception):
    pass


class NoSoloTanker(Exception):
    pass


class SquadCycleOver(Exception):
    pass


class NoSeedingViolation(Exception):
    pass


class NoLevelViolation(Exception):
    pass


class OffensiveDefensiveState(TypedDict):
    offensive_points: int
    defensive_points: int


@dataclass
class WatchStatus:
    warning_confirmation_version: int = 1
    offensive_points: Mapping[str, int] = field(default_factory=dict)
    initial_world_positions: Mapping[str, tuple[float, float, float] | None] = field(
        default_factory=dict
    )
    world_position_map_id: str | None = None
    combat_area_outside_player_ids: set[str] = field(default_factory=set)
    position_tracking_context: Mapping[str, tuple[int | None, str | None]] = field(
        default_factory=dict
    )
    # (position, observation time, death counter); primitive values also keep
    # these pickles readable by older processes during a rollback.
    position_observations: Mapping[
        str, tuple[tuple[float, float, float], float, int | None]
    ] = field(default_factory=dict)

    noted: Mapping[str, List[datetime]] = field(default_factory=dict)
    warned: Mapping[str, List[datetime]] = field(default_factory=dict)
    punished: Mapping[str, List[datetime]] = field(default_factory=dict)


def upgrade_legacy_warning_state(state: WatchStatus) -> WatchStatus:
    """Do not treat warnings planned by older workers as confirmed sends."""
    if state.__dict__.get("warning_confirmation_version") == 1:
        return state
    affected = 0
    for warnings in state.warned.values():
        if warnings:
            warnings[-1] = PENDING_WARNING
            affected += 1
    state.warning_confirmation_version = 1
    if affected:
        logger.warning(
            "Automod retained %s legacy warning(s) as unconfirmed until the watch resets",
            affected,
        )
    return state


class PunishStepState(Enum):
    WAIT = auto()
    IMMUNED = auto()
    DISABLED = auto()
    APPLY = auto()
    GO_TO_NEXT_STEP = auto()


class ActionMethod(Enum):
    MESSAGE = auto()
    PUNISH = auto()
    KICK = auto()
    FORCE_KICK = auto()


@dataclass
class PunishDetails:
    author: str
    message: str = ""
    discord_audit_url: Optional[HttpUrl] = field(repr=False, default=None)
    dry_run: bool = False


@dataclass
class Flag:
    id: int
    flag: str
    comment: Optional[str]
    modified: datetime


@dataclass
class PunishPlayer:
    player_id: str
    name: str
    squad: str
    team: str
    flags: List[Flag] = field(default_factory=list)
    role: str = None
    lvl: int = None
    details: PunishDetails = None
    # Rules with the same live/dry-run mode can propose one shared action.
    # Keep their authors so every contributing watch receives its outcome.
    related_authors: List[str] = field(default_factory=list, repr=False, compare=False)
    related_details: List[PunishDetails] = field(default_factory=list, repr=False, compare=False)

    def short_repr(self):
        return (
            f"{self.__class__.__name__}"
            f"(name={self.name}, lvl={self.lvl}, role={self.role}, flags={self.flags})"
        )


@dataclass
class ASquad:
    team: str
    name: str
    players: List[PunishPlayer] = field(default_factory=list)


@dataclass
class PunitionsToApply:
    warning: List[PunishPlayer] = field(default_factory=list)
    punish: List[PunishPlayer] = field(default_factory=list)
    kick: List[PunishPlayer] = field(default_factory=list)
    squads_state: List[ASquad] = field(default_factory=list)

    def add_squad_state(self, team: str, squad_name: str, squad: dict):
        try:
            if any(s.team == team and s.name == squad_name for s in self.squads_state):
                return

            players = []
            for player in squad.get("players", []):
                profile = player.get("profile", {})
                punish_player = PunishPlayer(
                    player_id=player.get("player_id"),
                    name=player.get("name"),
                    squad=player.get("unit_name"),
                    team=player.get("team"),
                    flags=profile.get("flags") if profile else [],
                    role=player.get("role"),
                    lvl=player.get("level"),
                )
                players.append(punish_player)

            self.squads_state.append(
                ASquad(team=team, name=squad_name, players=players)
            )
        except:
            logger.exception("Unable to add squad info")

    def merge(self, o: "PunitionsToApply"):
        if len(o.warning) != 0:
            self.warning.extend(o.warning)
        for current, incoming in ((self.punish, o.punish), (self.kick, o.kick)):
            for player in incoming:
                index = next((i for i, item in enumerate(current) if item.player_id == player.player_id), None)
                if index is None:
                    current.append(player)
                elif getattr(current[index].details, "dry_run", False) and not getattr(player.details, "dry_run", False):
                    current[index] = player
                elif getattr(current[index].details, "dry_run", False) == getattr(player.details, "dry_run", False):
                    selected = current[index]
                    if current is self.punish:
                        selected.related_details.extend([player.details, *player.related_details])
                    for author in [player.details.author, *player.related_authors]:
                        if author != selected.details.author and author not in selected.related_authors:
                            selected.related_authors.append(author)
        for s in o.squads_state:
            if any(s.team == ss.team and s.name == ss.name for ss in self.squads_state):
                continue
            self.squads_state.append(
                ASquad(
                    team=s.team,
                    name=s.name,
                    players=s.players,
                )
            )

    def __bool__(self):
        return any(
            [
                self.warning,
                self.punish,
                self.kick,
            ]
        )
