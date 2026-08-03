import os

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.autobalancer.telemetry import snapshot_role_deltas


def player(player_id="p1", role_family="combat_infantry", **counters):
    return {
        "player_id": player_id,
        "role_family": role_family,
        "kills": 0,
        "deaths": 0,
        "teamkills": 0,
        "combat": 0,
        "offense": 0,
        "defense": 0,
        "support": 0,
        **counters,
    }


def test_snapshot_delta_persists_complete_role_diagnostics():
    rows = snapshot_role_deltas(
        [player(kills=3, deaths=2, teamkills=1, combat=100, support=40)],
        [
            player(
                kills=5,
                deaths=5,
                teamkills=2,
                combat=160,
                offense=20,
                defense=10,
                support=70,
            )
        ],
        30,
    )
    assert rows == [
        {
            "player_id": "p1",
            "role_family": "combat_infantry",
            "time_seconds": 30,
            "valid_intervals": 1,
            "ambiguous_intervals": 0,
            "invalid_intervals": 0,
            "kills": 2,
            "deaths": 3,
            "teamkills": 1,
            "combat": 60,
            "offense": 20,
            "defense": 10,
            "support": 30,
        }
    ]


def test_role_change_is_marked_ambiguous_without_assigning_score_deltas():
    rows = snapshot_role_deltas(
        [player(role_family="combat_infantry", kills=3)],
        [player(role_family="support", kills=4)],
        30,
    )
    assert rows[0]["role_family"] == "support"
    assert rows[0]["ambiguous_intervals"] == 1
    assert rows[0]["time_seconds"] == 0
    assert rows[0]["kills"] == 0


def test_counter_reset_is_invalid_and_not_counted():
    rows = snapshot_role_deltas(
        [player(kills=8, combat=300)],
        [player(kills=1, combat=20)],
        30,
    )
    assert rows[0]["invalid_intervals"] == 1
    assert rows[0]["valid_intervals"] == 0
    assert rows[0]["time_seconds"] == 0


def test_stale_interval_is_ambiguous_and_new_player_is_ignored():
    rows = snapshot_role_deltas(
        [player("p1")],
        [player("p1", kills=1), player("new", kills=1)],
        91,
    )
    assert len(rows) == 1
    assert rows[0]["player_id"] == "p1"
    assert rows[0]["ambiguous_intervals"] == 1
