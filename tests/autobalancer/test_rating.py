import os

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.autobalancer.models import PlayerSnapshot
from rcon.autobalancer.rating import (
    HistoricalSample,
    calculate_ratings,
    normalized_percentiles,
    percentile,
)


def test_percentile_and_five_ninety_five_winsorization():
    values = [0, 10, 20, 30, 1000]
    assert percentile(values, 0.5) == 20
    normalized = normalized_percentiles(
        {str(index): value for index, value in enumerate(values)}
    )
    assert normalized["0"] == 0
    assert normalized["4"] == 100
    assert 0 < normalized["2"] < 100


def test_player_without_any_data_is_neutral_with_no_confidence():
    newcomer = PlayerSnapshot(player_id="new", name="New", team="allies")
    rating = calculate_ratings([newcomer])["new"]
    assert rating.value == 50
    assert rating.confidence == 0


def test_level_is_only_twenty_five_percent_of_rating():
    low = PlayerSnapshot(player_id="low", name="Low", team="allies", level=1)
    high = PlayerSnapshot(player_id="high", name="High", team="axis", level=500)
    ratings = calculate_ratings([low, high])
    assert ratings["low"].value == 37.5
    assert ratings["high"].value == 62.5
    assert ratings["high"].confidence == 0.25


def test_history_and_live_evidence_ramp_linearly():
    first = PlayerSnapshot(
        player_id="first",
        name="First",
        team="allies",
        map_playtime_seconds=15 * 60,
        kills=30,
        combat=300,
        offense=100,
        defense=100,
        support=100,
    )
    second = PlayerSnapshot(
        player_id="second",
        name="Second",
        team="axis",
        map_playtime_seconds=15 * 60,
        kills=1,
        combat=10,
    )
    history = {
        "first": [HistoricalSample(2.5 * 3600, 100, 1000, 400, 400, 400)],
        "second": [HistoricalSample(2.5 * 3600, 10, 100, 10, 10, 10)],
    }
    ratings = calculate_ratings([first, second], history)
    assert ratings["first"].history_component == pytest.approx(75)
    assert ratings["first"].live_component == pytest.approx(75)
    assert ratings["first"].confidence == pytest.approx(0.375)
    assert ratings["first"].value > ratings["second"].value


def test_missing_history_is_neutral_not_zero_skill():
    known = PlayerSnapshot(player_id="known", name="Known", team="allies", level=50)
    unknown = PlayerSnapshot(player_id="unknown", name="Unknown", team="axis")
    ratings = calculate_ratings([known, unknown])
    assert ratings["unknown"].history_component == 50
    assert ratings["unknown"].live_component == 50
