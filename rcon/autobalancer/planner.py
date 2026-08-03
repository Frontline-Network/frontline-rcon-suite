from __future__ import annotations

import math
from collections import Counter
from dataclasses import dataclass
from itertools import combinations
from typing import Collection

from .models import BalancePlan, BalanceSnapshot, Candidate, PlayerSnapshot

COMMANDER_ROLES = {"armycommander", "commander"}
LEADER_ROLES = {"officer", "tankcommander", "spotter", "artilleryobserver"}
SPECIAL_UNITS = {"armor", "armour", "recon", "artillery"}
INFANTRY_UNITS = {"infantry", "offense", "defense", "support"}


def required_switches(difference: int, target_difference: int = 2) -> int:
    return max(0, math.ceil((abs(difference) - target_difference) / 2))


def team_rating(players: list[PlayerSnapshot], team: str) -> float:
    values = [player.rating.value for player in players if player.team == team]
    return sum(values) / len(values) if values else 50.0


def protection_tier(player: PlayerSnapshot) -> tuple[int | None, str]:
    role = (player.role or "").replace(" ", "").lower()
    unit_type = (player.unit_type or "").lower()
    if role in COMMANDER_ROLES or unit_type == "commander":
        return None, "Commander sind für automatische Wechsel gesperrt"
    if unit_type in SPECIAL_UNITS:
        return 5, "Armor-, Recon- oder Artillery-Squad"
    if player.is_leader or role in LEADER_ROLES:
        return 4, "Squad Leader"
    if not player.unit_name and player.unit_id is None:
        return 0, "keinem Squad zugewiesen"
    if player.unit_size <= 1:
        return 0, "alleiniger nicht führender Infanterist"
    if player.unit_size < 6 and player.squad_seconds < 300:
        return 1, "erst kurz in einem unvollständigen Infantry-Squad"
    if player.unit_size < 6 and player.squad_seconds < 900:
        return 2, "Mitglied eines unvollständigen Infantry-Squads"
    return 3, "Mitglied eines vollen oder stabilen Infantry-Squads"


@dataclass(slots=True)
class _Choice:
    player: PlayerSnapshot
    base_tier: int
    effective_tier: int
    volunteer: bool
    reason: str


def _eligible_choices(
    snapshot: BalanceSnapshot,
    source: str,
    volunteers: Collection[str],
    cooldown_player_ids: Collection[str],
    pending_player_ids: Collection[str],
    connection_grace_seconds: int,
) -> tuple[list[_Choice], list[str]]:
    volunteers = set(volunteers)
    cooldown_player_ids = set(cooldown_player_ids)
    pending_player_ids = set(pending_player_ids)
    choices: list[_Choice] = []
    blocked: list[str] = []
    for player in snapshot.players:
        if player.team != source:
            continue
        if not player.player_id:
            blocked.append(f"{player.name}: fehlende Spieler-ID")
            continue
        if player.player_id in cooldown_player_ids:
            blocked.append(f"{player.name}: Drei-Karten-Schutzfrist")
            continue
        if player.player_id in pending_player_ids:
            blocked.append(f"{player.name}: bereits vorgemerkt")
            continue
        if player.connected_seconds < connection_grace_seconds:
            blocked.append(f"{player.name}: Verbindungs-Schutzfrist")
            continue
        tier, reason = protection_tier(player)
        if tier is None:
            blocked.append(f"{player.name}: {reason}")
            continue
        volunteer = player.player_id in volunteers
        choices.append(
            _Choice(
                player=player,
                base_tier=tier,
                effective_tier=max(0, tier - 2) if volunteer else tier,
                volunteer=volunteer,
                reason=("freiwillig; " if volunteer else "") + reason,
            )
        )
    return choices, blocked


def eligible_players(
    snapshot: BalanceSnapshot,
    cooldown_player_ids: Collection[str] = (),
    pending_player_ids: Collection[str] = (),
    connection_grace_seconds: int = 120,
) -> list[PlayerSnapshot]:
    """Return everyone on the larger team who may legally volunteer."""
    if snapshot.larger_team is None:
        return []
    choices, _ = _eligible_choices(
        snapshot,
        snapshot.larger_team,
        (),
        cooldown_player_ids,
        pending_player_ids,
        connection_grace_seconds,
    )
    return [
        choice.player
        for choice in sorted(
            choices,
            key=lambda choice: (
                choice.effective_tier,
                choice.player.squad_key or "",
                choice.player.player_id,
            ),
        )
    ]


def _projected_gap(
    players: list[PlayerSnapshot], source: str, target: str, moved: list[PlayerSnapshot]
) -> float:
    moved_ids = {player.player_id for player in moved}
    source_values = [
        player.rating.value
        for player in players
        if player.team == source and player.player_id not in moved_ids
    ]
    target_values = [
        player.rating.value
        for player in players
        if player.team == target or player.player_id in moved_ids
    ]
    source_rating = sum(source_values) / len(source_values) if source_values else 50.0
    target_rating = sum(target_values) / len(target_values) if target_values else 50.0
    return abs(source_rating - target_rating)


def build_plan(
    snapshot: BalanceSnapshot,
    target_difference: int = 2,
    volunteers: Collection[str] = (),
    cooldown_player_ids: Collection[str] = (),
    pending_player_ids: Collection[str] = (),
    connection_grace_seconds: int = 120,
    max_switches: int = 3,
) -> BalancePlan | None:
    count = required_switches(snapshot.difference, target_difference)
    if not count or snapshot.larger_team is None or snapshot.smaller_team is None:
        return None
    source, target = snapshot.larger_team, snapshot.smaller_team
    choices, blocked = _eligible_choices(
        snapshot,
        source,
        volunteers,
        cooldown_player_ids,
        pending_player_ids,
        connection_grace_seconds,
    )

    planned_count = min(count, max_switches, len(choices))
    selected_choices: list[_Choice] = []
    if planned_count:

        def combination_score(combo: tuple[_Choice, ...]):
            squad_counts = Counter(
                choice.player.squad_key
                for choice in combo
                if choice.player.squad_key is not None
            )
            repeated_squads = sum(
                max(0, amount - 1) for amount in squad_counts.values()
            )
            tier_profile = tuple(
                sorted((choice.effective_tier for choice in combo), reverse=True)
            )
            return (
                tier_profile,
                repeated_squads,
                _projected_gap(
                    snapshot.players,
                    source,
                    target,
                    [choice.player for choice in combo],
                ),
                -sum(choice.player.rating.confidence for choice in combo),
                tuple(sorted(choice.player.player_id for choice in combo)),
            )

        selected_choices = list(
            min(combinations(choices, planned_count), key=combination_score)
        )

    selected: list[Candidate] = []
    moved: list[PlayerSnapshot] = []
    used_squads: Counter[str] = Counter()
    while selected_choices:
        lowest_tier = min(choice.effective_tier for choice in selected_choices)
        tier_choices = [
            choice
            for choice in selected_choices
            if choice.effective_tier == lowest_tier
        ]
        ranked = sorted(
            tier_choices,
            key=lambda choice: (
                bool(choice.player.squad_key and used_squads[choice.player.squad_key]),
                _projected_gap(
                    snapshot.players, source, target, moved + [choice.player]
                ),
                -choice.player.rating.confidence,
                choice.player.player_id,
            ),
        )
        choice = ranked[0]
        selected_choices.remove(choice)
        moved.append(choice.player)
        if choice.player.squad_key:
            used_squads[choice.player.squad_key] += 1
        selected.append(
            Candidate(
                player=choice.player,
                base_tier=choice.base_tier,
                effective_tier=choice.effective_tier,
                volunteer=choice.volunteer,
                projected_rating_gap=_projected_gap(
                    snapshot.players, source, target, moved
                ),
                reason=choice.reason,
            )
        )

    if len(selected) < min(count, max_switches):
        blocked.append("Nicht genügend zulässige Kandidaten")
    return BalancePlan(
        source_team=source,
        target_team=target,
        required_switches=count,
        candidates=selected,
        blocked_reasons=blocked,
    )
