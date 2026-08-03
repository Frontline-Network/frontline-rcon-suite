from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Iterable, Mapping

from .models import PlayerSnapshot, SkillRating

NEUTRAL_RATING = 50.0


@dataclass(slots=True)
class HistoricalSample:
    time_seconds: int
    kills: int
    combat: int
    offense: int
    defense: int
    support: int


def _finite(value: object, default: float = 0.0) -> float:
    try:
        number = float(value)  # type: ignore[arg-type]
    except (TypeError, ValueError):
        return default
    return number if math.isfinite(number) else default


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
    present = {
        key: _finite(value)
        for key, value in values.items()
        if value is not None and math.isfinite(_finite(value))
    }
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


def _rates(samples: Iterable[HistoricalSample]) -> tuple[dict[str, float], int]:
    samples = list(samples)
    seconds = sum(max(0, sample.time_seconds) for sample in samples)
    if seconds <= 0:
        return {}, 0
    minutes = seconds / 60.0
    return (
        {
            "kills": sum(sample.kills for sample in samples) / minutes,
            "combat": sum(sample.combat for sample in samples) / minutes,
            "team": sum(
                sample.offense + sample.defense + sample.support for sample in samples
            )
            / minutes,
        },
        seconds,
    )


def calculate_ratings(
    players: list[PlayerSnapshot],
    history: Mapping[str, Iterable[HistoricalSample]] | None = None,
) -> dict[str, SkillRating]:
    """Rate the online cohort and shrink sparse evidence back towards 50.

    Historical maps are filtered by the repository adapter. This pure function only
    aggregates the supplied last-20 samples and applies the documented weighting.
    """
    history = history or {}
    ids = [player.player_id for player in players]
    levels = normalized_percentiles(
        {
            player.player_id: float(player.level) if player.level is not None else None
            for player in players
        }
    )

    history_rates: dict[str, dict[str, float]] = {}
    history_seconds: dict[str, int] = {}
    for player_id in ids:
        rates, seconds = _rates(history.get(player_id, []))
        history_rates[player_id] = rates
        history_seconds[player_id] = seconds

    history_kills = normalized_percentiles(
        {player_id: history_rates[player_id].get("kills") for player_id in ids}
    )
    history_combat = normalized_percentiles(
        {player_id: history_rates[player_id].get("combat") for player_id in ids}
    )
    history_team = normalized_percentiles(
        {player_id: history_rates[player_id].get("team") for player_id in ids}
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
    live_kills = normalized_percentiles(
        {player_id: (live_rates[player_id] or {}).get("kills") for player_id in ids}
    )
    live_combat = normalized_percentiles(
        {player_id: (live_rates[player_id] or {}).get("combat") for player_id in ids}
    )
    live_team = normalized_percentiles(
        {player_id: (live_rates[player_id] or {}).get("team") for player_id in ids}
    )

    ratings: dict[str, SkillRating] = {}
    for player in players:
        player_id = player.player_id
        history_raw = (
            0.65 * ((history_kills[player_id] + history_combat[player_id]) / 2.0)
            + 0.35 * history_team[player_id]
        )
        history_confidence = min(1.0, history_seconds[player_id] / (5 * 3600))
        history_component = NEUTRAL_RATING + history_confidence * (
            history_raw - NEUTRAL_RATING
        )

        live_raw = (
            0.65 * ((live_kills[player_id] + live_combat[player_id]) / 2.0)
            + 0.35 * live_team[player_id]
        )
        live_confidence = min(1.0, player.map_playtime_seconds / (30 * 60))
        if live_rates[player_id] is None:
            live_confidence = 0.0
        live_component = NEUTRAL_RATING + live_confidence * (live_raw - NEUTRAL_RATING)

        level_present = player.level is not None
        level_component = levels[player_id] if level_present else NEUTRAL_RATING
        value = (
            0.25 * level_component + 0.60 * history_component + 0.15 * live_component
        )
        confidence = (
            0.25 * (1.0 if level_present else 0.0)
            + 0.60 * history_confidence
            + 0.15 * live_confidence
        )
        ratings[player_id] = SkillRating(
            value=round(min(100.0, max(0.0, value)), 4),
            confidence=round(min(1.0, max(0.0, confidence)), 4),
            level_component=round(level_component, 4),
            history_component=round(history_component, 4),
            live_component=round(live_component, 4),
        )
    return ratings
