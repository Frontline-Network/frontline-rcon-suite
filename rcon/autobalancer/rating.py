from __future__ import annotations

import math
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Iterable, Mapping

from .models import PlayerSnapshot, SkillRating

NEUTRAL_RATING = 50.0
RATING_MODEL_VERSION = "role-aware-v2"
ROLE_COHORT_MIN_SIZE = 8

COMMANDER_ROLES = {"armycommander", "commander"}
LEADER_ROLES = {"officer", "squadleader"}
SUPPORT_ROLES = {"support", "engineer", "medic"}
SPECIAL_ROLE_FAMILIES = {
    "tankcommander": "specialist",
    "crewman": "specialist",
    "tankcrew": "specialist",
    "spotter": "specialist",
    "sniper": "specialist",
    "artilleryobserver": "specialist",
}
SPECIAL_UNITS = {"armor", "armour", "recon", "artillery"}
ROLE_WEIGHTS = {
    "combat_infantry": (0.60, 0.40),
    "support": (0.35, 0.65),
    "leader": (0.35, 0.65),
    "specialist": (0.65, 0.35),
    "commander": (0.0, 0.0),
}


@dataclass(slots=True)
class HistoricalSample:
    time_seconds: int
    kills: int
    combat: int
    offense: int
    defense: int
    support: int
    deaths: int = 0
    teamkills: int = 0
    role_family: str = "legacy"
    map_key: str = ""
    observed_at: datetime | None = None
    exact: bool = False


def _finite(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


def role_family(player: PlayerSnapshot | Mapping[str, object]) -> str:
    def value(name: str, default: object = "") -> object:
        if isinstance(player, Mapping):
            return player.get(name, default)
        return getattr(player, name, default)

    role = str(value("role") or "").replace(" ", "").lower()
    unit_type = str(value("unit_type") or "").lower()
    is_leader = bool(value("is_leader", False))
    if role in COMMANDER_ROLES or unit_type == "commander":
        return "commander"
    if unit_type in SPECIAL_UNITS or role in SPECIAL_ROLE_FAMILIES:
        return "specialist"
    if is_leader or role in LEADER_ROLES:
        return "leader"
    if role in SUPPORT_ROLES:
        return "support"
    return "combat_infantry"


def percentile(values: list[float], quantile: float) -> float:
    """Linear percentile equivalent to the common inclusive definition."""
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * min(1.0, max(0.0, quantile))
    lower = math.floor(position)
    upper = math.ceil(position)
    if lower == upper:
        return ordered[lower]
    fraction = position - lower
    return ordered[lower] + (ordered[upper] - ordered[lower]) * fraction


def normalized_percentiles(values: Mapping[str, float | None]) -> dict[str, float]:
    present: dict[str, float] = {}
    for key, value in values.items():
        if value is None:
            continue
        number = _finite(value, math.nan)
        if math.isfinite(number):
            present[key] = number
    if not present:
        return {key: NEUTRAL_RATING for key in values}
    low = percentile(list(present.values()), 0.05)
    high = percentile(list(present.values()), 0.95)
    if math.isclose(low, high):
        scaled = {key: NEUTRAL_RATING for key in present}
    else:
        scaled = {
            key: round(
                min(
                    100.0,
                    max(
                        0.0,
                        100.0 * (min(high, max(low, value)) - low) / (high - low),
                    ),
                ),
                10,
            )
            for key, value in present.items()
        }
    return {key: scaled.get(key, NEUTRAL_RATING) for key in values}


def role_normalized_percentiles(
    values: Mapping[str, float | None], families: Mapping[str, str]
) -> dict[str, float]:
    """Blend small role cohorts with the online population instead of overfitting."""
    global_scores = normalized_percentiles(values)
    family_members: dict[str, list[str]] = defaultdict(list)
    for player_id, family in families.items():
        if family != "commander":
            family_members[family].append(player_id)
    result = dict(global_scores)
    for family, members in family_members.items():
        subset = {player_id: values.get(player_id) for player_id in members}
        family_scores = normalized_percentiles(subset)
        blend = min(1.0, len(members) / ROLE_COHORT_MIN_SIZE)
        for player_id in members:
            result[player_id] = round(
                blend * family_scores[player_id]
                + (1.0 - blend) * global_scores[player_id],
                10,
            )
    for player_id, family in families.items():
        if family == "commander":
            result[player_id] = NEUTRAL_RATING
    return result


def _age_days(value: datetime | None, now: datetime) -> float:
    if value is None:
        return 0.0
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    if now.tzinfo is None:
        now = now.replace(tzinfo=timezone.utc)
    return max(0.0, (now - value).total_seconds() / 86400.0)


def _rates(
    samples: Iterable[HistoricalSample],
    now: datetime,
    half_life_days: int,
) -> tuple[dict[str, float], int, int]:
    samples = list(samples)
    seconds = sum(max(0, sample.time_seconds) for sample in samples)
    maps = len({sample.map_key or str(index) for index, sample in enumerate(samples)})
    weighted_seconds = 0.0
    totals = {"kills": 0.0, "combat": 0.0, "team": 0.0}
    for sample in samples:
        sample_seconds = max(0, sample.time_seconds)
        if not sample_seconds:
            continue
        weight = math.pow(0.5, _age_days(sample.observed_at, now) / half_life_days)
        weighted_seconds += sample_seconds * weight
        totals["kills"] += sample.kills * weight
        totals["combat"] += sample.combat * weight
        totals["team"] += (sample.offense + sample.defense + sample.support) * weight
    if weighted_seconds <= 0:
        return {}, seconds, maps
    minutes = weighted_seconds / 60.0
    return ({key: value / minutes for key, value in totals.items()}, seconds, maps)


def _history_for_player(
    samples: Iterable[HistoricalSample],
    family: str,
    now: datetime,
    half_life_days: int,
) -> tuple[dict[str, float], int, int, float, str]:
    samples = list(samples)
    exact = [
        sample for sample in samples if sample.exact and sample.role_family == family
    ]
    legacy = [sample for sample in samples if not sample.exact]
    exact_rates, exact_seconds, exact_maps = _rates(exact, now, half_life_days)
    legacy_rates, legacy_seconds, legacy_maps = _rates(legacy, now, half_life_days)
    exact_confidence = min(
        1.0,
        exact_seconds / (5 * 3600),
        exact_maps / 5 if exact_maps else 0.0,
    )
    legacy_confidence = min(
        0.4,
        legacy_seconds / (5 * 3600),
        legacy_maps / 5 if legacy_maps else 0.0,
    )
    if exact_rates and exact_confidence >= legacy_confidence:
        return (
            exact_rates,
            exact_seconds,
            exact_maps,
            exact_confidence,
            "exact_role",
        )
    if legacy_rates:
        return (
            legacy_rates,
            legacy_seconds,
            legacy_maps,
            legacy_confidence,
            "legacy",
        )
    return {}, 0, 0, 0.0, "none"


def _component(
    player_id: str,
    family: str,
    kills: Mapping[str, float],
    combat: Mapping[str, float],
    team: Mapping[str, float],
) -> float:
    if family == "commander":
        return NEUTRAL_RATING
    combat_weight, team_weight = ROLE_WEIGHTS[family]
    combat_component = (kills[player_id] + combat[player_id]) / 2.0
    return combat_weight * combat_component + team_weight * team[player_id]


def calculate_ratings(
    players: list[PlayerSnapshot],
    history: Mapping[str, Iterable[HistoricalSample]] | None = None,
    *,
    now: datetime | None = None,
    half_life_days: int = 30,
) -> dict[str, SkillRating]:
    """Calculate transparent role-aware ratings and reliability-adjust them."""
    history = history or {}
    now = now or datetime.now(timezone.utc)
    half_life_days = max(1, int(half_life_days))
    ids = [player.player_id for player in players]
    families = {player.player_id: role_family(player) for player in players}
    levels = normalized_percentiles(
        {
            player.player_id: float(player.level) if player.level is not None else None
            for player in players
        }
    )

    history_rates: dict[str, dict[str, float]] = {}
    history_seconds: dict[str, int] = {}
    history_maps: dict[str, int] = {}
    history_confidence: dict[str, float] = {}
    history_source: dict[str, str] = {}
    for player_id in ids:
        rates, seconds, maps, confidence, source = _history_for_player(
            history.get(player_id, []),
            families[player_id],
            now,
            half_life_days,
        )
        history_rates[player_id] = rates
        history_seconds[player_id] = seconds
        history_maps[player_id] = maps
        history_confidence[player_id] = confidence
        history_source[player_id] = source

    history_kills = role_normalized_percentiles(
        {player_id: history_rates[player_id].get("kills") for player_id in ids},
        families,
    )
    history_combat = role_normalized_percentiles(
        {player_id: history_rates[player_id].get("combat") for player_id in ids},
        families,
    )
    history_team = role_normalized_percentiles(
        {player_id: history_rates[player_id].get("team") for player_id in ids},
        families,
    )

    live_rates: dict[str, dict[str, float] | None] = {}
    for player in players:
        if player.map_playtime_seconds <= 0:
            live_rates[player.player_id] = None
            continue
        minutes = player.map_playtime_seconds / 60.0
        live_rates[player.player_id] = {
            "kills": player.kills / minutes,
            "combat": player.combat / minutes,
            "team": (player.offense + player.defense + player.support) / minutes,
        }
    live_kills = role_normalized_percentiles(
        {player_id: (live_rates[player_id] or {}).get("kills") for player_id in ids},
        families,
    )
    live_combat = role_normalized_percentiles(
        {player_id: (live_rates[player_id] or {}).get("combat") for player_id in ids},
        families,
    )
    live_team = role_normalized_percentiles(
        {player_id: (live_rates[player_id] or {}).get("team") for player_id in ids},
        families,
    )

    ratings: dict[str, SkillRating] = {}
    for player in players:
        player_id = player.player_id
        family = families[player_id]
        if family == "commander":
            ratings[player_id] = SkillRating(
                version=RATING_MODEL_VERSION,
                role_family=family,
            )
            continue
        history_component = _component(
            player_id,
            family,
            history_kills,
            history_combat,
            history_team,
        )
        live_component = _component(
            player_id,
            family,
            live_kills,
            live_combat,
            live_team,
        )
        live_confidence = min(1.0, player.map_playtime_seconds / (30 * 60))
        if live_rates[player_id] is None:
            live_confidence = 0.0
        level_present = player.level is not None
        level_component = levels[player_id] if level_present else NEUTRAL_RATING
        raw_value = (
            0.15 * level_component + 0.70 * history_component + 0.15 * live_component
        )
        confidence = (
            0.15 * (1.0 if level_present else 0.0)
            + 0.70 * history_confidence[player_id]
            + 0.15 * live_confidence
        )
        value = NEUTRAL_RATING + confidence * (raw_value - NEUTRAL_RATING)
        ratings[player_id] = SkillRating(
            version=RATING_MODEL_VERSION,
            value=round(min(100.0, max(0.0, value)), 4),
            raw_value=round(min(100.0, max(0.0, raw_value)), 4),
            confidence=round(min(1.0, max(0.0, confidence)), 4),
            role_family=family,
            level_component=round(level_component, 4),
            history_component=round(history_component, 4),
            live_component=round(live_component, 4),
            history_seconds=history_seconds[player_id],
            history_maps=history_maps[player_id],
            history_source=history_source[player_id],
        )
    return ratings
