from datetime import datetime, timedelta, timezone

from rcon.autobalancer.history import reconstruct_round_timeline


def team_events(start, allies, axis):
    event_time = start + timedelta(seconds=1)
    return [
        (event_time, f"allied-{index}", "TEAMSWITCH", "(None > Allies)")
        for index in range(allies)
    ] + [
        (event_time, f"axis-{index}", "TEAMSWITCH", "(None > Axis)")
        for index in range(axis)
    ]


def analyze(allies, axis):
    start = datetime(2026, 8, 3, 18, 0, tzinfo=timezone.utc)
    return reconstruct_round_timeline(
        start,
        start + timedelta(minutes=20),
        team_events(start, allies, axis),
        target_difference=2,
        minimum_players=40,
        round_start_protection_seconds=0,
        round_end_protection_seconds=0,
        stable_difference_seconds=45,
        sample_seconds=30,
    )


def test_historical_round_is_balanced_inside_target_difference():
    result = analyze(41, 40)

    assert result["status"] == "balanced"
    assert result["quality"]["reliable"] is True
    assert result["metrics"]["balanced_ratio"] == 1
    assert result["metrics"]["maximum_difference"] == 1
    assert result["metrics"]["incident_count"] == 0


def test_historical_round_detects_stable_unbalance():
    result = analyze(44, 40)

    assert result["status"] == "unbalanced"
    assert result["metrics"]["maximum_difference"] == 4
    assert result["metrics"]["incident_count"] == 1
    assert result["metrics"]["longest_unbalanced_seconds"] >= 45


def test_short_unbalance_does_not_count_as_incident():
    start = datetime(2026, 8, 3, 18, 0, tzinfo=timezone.utc)
    events = team_events(start, 44, 40)
    events += [
        (
            start + timedelta(seconds=31),
            f"allied-{index}",
            "TEAMSWITCH",
            "(Allies > None)",
        )
        for index in range(2)
    ]
    result = reconstruct_round_timeline(
        start,
        start + timedelta(minutes=20),
        events,
        target_difference=2,
        minimum_players=40,
        round_start_protection_seconds=0,
        round_end_protection_seconds=0,
        stable_difference_seconds=45,
        sample_seconds=30,
    )

    assert result["status"] == "transient"
    assert result["metrics"]["incident_count"] == 0


def test_historical_round_without_enough_players_is_not_measurable():
    result = analyze(10, 8)

    assert result["status"] == "not_measurable"
    assert result["quality"]["reliable"] is False
    assert result["metrics"]["balanced_ratio"] is None
