import os
from datetime import datetime, timedelta, timezone

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.autobalancer.models import PlayerSnapshot
from rcon.autobalancer.rating import (
    RATING_MODEL_VERSION,
    ROLE_WEIGHTS,
    HistoricalSample,
    _rates,
    calculate_ratings,
    normalized_percentiles,
    percentile,
    role_family,
    role_normalized_percentiles,
)

NOW = datetime(2026, 8, 4, tzinfo=timezone.utc)


def sample(
    *,
    map_key,
    role="combat_infantry",
    kills=0,
    combat=0,
    team=0,
    hours=1,
    age_days=0,
    exact=True,
    deaths=0,
    teamkills=0,
):
    return HistoricalSample(
        time_seconds=int(hours * 3600),
        kills=kills,
        combat=combat,
        offense=team,
        defense=0,
        support=0,
        deaths=deaths,
        teamkills=teamkills,
        role_family=role,
        map_key=map_key,
        observed_at=NOW - timedelta(days=age_days),
        exact=exact,
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


@pytest.mark.parametrize(
    "player,expected",
    [
        (
            PlayerSnapshot("rifle", "Rifle", "allies", role="rifleman"),
            "combat_infantry",
        ),
        (PlayerSnapshot("support", "Support", "allies", role="support"), "support"),
        (PlayerSnapshot("engineer", "Engineer", "allies", role="engineer"), "support"),
        (PlayerSnapshot("medic", "Medic", "allies", role="medic"), "support"),
        (PlayerSnapshot("leader", "Leader", "allies", role="officer"), "leader"),
        (PlayerSnapshot("tank", "Tank", "allies", unit_type="armor"), "specialist"),
        (PlayerSnapshot("recon", "Recon", "allies", role="sniper"), "specialist"),
        (PlayerSnapshot("arty", "Arty", "allies", unit_type="artillery"), "specialist"),
        (
            PlayerSnapshot("mortar", "Mortar", "allies", unit_type="mortar"),
            "specialist",
        ),
        (
            PlayerSnapshot("pilot", "Pilot", "allies", role="helicopterpilot"),
            "specialist",
        ),
        (
            PlayerSnapshot(
                "observer",
                "Observer",
                "allies",
                role="mortarobserver",
                is_leader=True,
            ),
            "leader",
        ),
        (
            PlayerSnapshot(
                "mortar-support",
                "Support",
                "allies",
                role="mortarsupport",
            ),
            "support",
        ),
        (
            PlayerSnapshot("commander", "Commander", "allies", role="armycommander"),
            "commander",
        ),
    ],
)
def test_role_family_mapping(player, expected):
    assert role_family(player) == expected


def test_documented_role_weights_are_stable():
    assert ROLE_WEIGHTS["combat_infantry"] == (0.60, 0.40)
    assert ROLE_WEIGHTS["support"] == (0.35, 0.65)
    assert ROLE_WEIGHTS["leader"] == (0.35, 0.65)
    assert ROLE_WEIGHTS["specialist"] == (0.65, 0.35)


def test_small_role_cohort_is_blended_with_global_population():
    values = {"s-low": 40, "s-high": 60}
    values.update({f"c-{index}": index * 10 for index in range(8)})
    families = {
        **{"s-low": "support", "s-high": "support"},
        **{f"c-{index}": "combat_infantry" for index in range(8)},
    }
    global_scores = normalized_percentiles(values)
    role_scores = role_normalized_percentiles(values, families)
    assert 0 < role_scores["s-low"] < global_scores["s-low"]
    assert global_scores["s-high"] < role_scores["s-high"] < 100


def test_player_without_any_data_is_neutral_with_no_confidence():
    newcomer = PlayerSnapshot(player_id="new", name="New", team="allies")
    rating = calculate_ratings([newcomer], now=NOW)["new"]
    assert rating.version == RATING_MODEL_VERSION
    assert rating.value == 50
    assert rating.raw_value == 50
    assert rating.confidence == 0


def test_level_is_fifteen_percent_and_is_shrunk_by_confidence():
    low = PlayerSnapshot(player_id="low", name="Low", team="allies", level=1)
    high = PlayerSnapshot(player_id="high", name="High", team="axis", level=500)
    ratings = calculate_ratings([low, high], now=NOW)
    assert ratings["low"].raw_value == 42.5
    assert ratings["high"].raw_value == 57.5
    assert ratings["low"].value == pytest.approx(48.875)
    assert ratings["high"].value == pytest.approx(51.125)
    assert ratings["high"].confidence == 0.15


def test_exact_history_reaches_full_history_confidence_after_five_hours_and_maps():
    first = PlayerSnapshot(
        player_id="first",
        name="First",
        team="allies",
        map_playtime_seconds=30 * 60,
        kills=30,
        combat=300,
        offense=300,
    )
    second = PlayerSnapshot(
        player_id="second",
        name="Second",
        team="axis",
        map_playtime_seconds=30 * 60,
        kills=1,
        combat=10,
    )
    history = {
        "first": [
            sample(map_key=f"first-{index}", kills=100, combat=1000, team=1200)
            for index in range(5)
        ],
        "second": [
            sample(map_key=f"second-{index}", kills=10, combat=100, team=20)
            for index in range(5)
        ],
    }
    ratings = calculate_ratings([first, second], history, now=NOW)
    assert ratings["first"].history_source == "exact_role"
    assert ratings["first"].history_maps == 5
    assert ratings["first"].history_seconds == 5 * 3600
    assert ratings["first"].history_component == pytest.approx(100)
    assert ratings["first"].live_component == pytest.approx(100)
    assert ratings["first"].confidence == pytest.approx(0.85)
    assert ratings["first"].value == pytest.approx(86.125)
    assert ratings["first"].value > ratings["second"].value


def test_legacy_history_confidence_never_exceeds_forty_percent():
    players = [
        PlayerSnapshot("high", "High", "allies"),
        PlayerSnapshot("low", "Low", "axis"),
    ]
    history = {
        "high": [
            sample(
                map_key=f"high-{index}",
                kills=100,
                combat=1000,
                team=1000,
                exact=False,
                role="legacy",
            )
            for index in range(10)
        ],
        "low": [
            sample(
                map_key=f"low-{index}",
                kills=1,
                combat=10,
                exact=False,
                role="legacy",
            )
            for index in range(10)
        ],
    }
    ratings = calculate_ratings(players, history, now=NOW)
    assert ratings["high"].history_source == "legacy"
    assert ratings["high"].confidence == pytest.approx(0.28)


def test_recent_history_is_weighted_more_than_thirty_day_old_history():
    rates, seconds, maps = _rates(
        [
            sample(map_key="recent", kills=0, age_days=0),
            sample(map_key="old", kills=60, age_days=30),
        ],
        NOW,
        30,
    )
    assert seconds == 2 * 3600
    assert maps == 2
    assert rates["kills"] == pytest.approx(1 / 3)


def test_deaths_and_teamkills_are_diagnostic_only():
    players = [
        PlayerSnapshot("a", "A", "allies"),
        PlayerSnapshot("b", "B", "axis"),
    ]
    base = sample(map_key="a", kills=10, combat=100, team=100)
    diagnostic = sample(
        map_key="b",
        kills=10,
        combat=100,
        team=100,
        deaths=99,
        teamkills=12,
    )
    ratings = calculate_ratings(
        players,
        {"a": [base], "b": [diagnostic]},
        now=NOW,
    )
    assert ratings["a"].raw_value == ratings["b"].raw_value
    assert ratings["a"].value == ratings["b"].value


def test_missing_history_is_neutral_not_zero_skill():
    known = PlayerSnapshot(player_id="known", name="Known", team="allies", level=50)
    unknown = PlayerSnapshot(player_id="unknown", name="Unknown", team="axis")
    ratings = calculate_ratings([known, unknown], now=NOW)
    assert ratings["unknown"].history_component == 50
    assert ratings["unknown"].live_component == 50
