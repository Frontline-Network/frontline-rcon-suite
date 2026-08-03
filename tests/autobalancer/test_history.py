from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from rcon.autobalancer import history as history_module
from rcon.autobalancer.history import (
    RoundHistoryRepository,
    _snapshot_player,
    analyze_snapshot_timeline,
    reconstruct_round_timeline,
    summarize_rating_quality,
    summarize_round_analyses,
)


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


def test_kills_supply_team_evidence_when_team_switch_logs_are_missing():
    start = datetime(2026, 8, 3, 18, 0, tzinfo=timezone.utc)
    events = []
    for index in range(20):
        event_time = start + timedelta(seconds=index + 1)
        events.extend(
            [
                {
                    "event_time": event_time,
                    "player1_name": f"allied-{index}",
                    "player1_id": f"a-{index}",
                    "player2_name": f"axis-{index}",
                    "player2_id": f"x-{index}",
                    "action": "KILL",
                    "content": "",
                    "raw": (
                        f"KILL: allied-{index}(Allies/a-{index}) -> "
                        f"axis-{index}(Axis/x-{index}) with RIFLE"
                    ),
                }
            ]
        )
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

    assert result["quality"]["team_switch_events"] == 0
    assert result["quality"]["team_evidence_events"] == 20
    assert result["quality"]["reliable"] is True
    assert result["status"] == "balanced"


def test_summary_excludes_unmeasurable_rounds_from_balance_rate():
    balanced = analyze(41, 40)
    balanced["round"] = {
        "start": "2026-08-03T18:00:00+00:00",
        "end": "2026-08-03T18:20:00+00:00",
        "map_name": "Carentan",
    }
    missing = analyze(10, 8)
    missing["round"] = {
        "start": "2026-08-04T18:00:00+00:00",
        "end": "2026-08-04T18:20:00+00:00",
        "map_name": "Foy",
    }

    summary = summarize_round_analyses([balanced, missing])

    assert summary["rounds_analyzed"] == 2
    assert summary["measurable_rounds"] == 1
    assert summary["coverage_ratio"] == 0.5
    assert summary["balanced_time_ratio"] == 1


def test_rating_quality_uses_only_valid_exact_snapshots_and_compares_strategies():
    start = datetime(2026, 8, 4, 18, 0, tzinfo=timezone.utc)
    game = SimpleNamespace(
        start=start,
        end=start + timedelta(minutes=20),
        map_name="Carentan",
    )
    round_id = f"{int(start.timestamp())}:Carentan"
    snapshots = []
    for index in range(38):
        snapshots.append(
            SimpleNamespace(
                round_id=round_id,
                captured_at=start + timedelta(seconds=index * 30),
                counts_match=True,
                fail_count=0,
                stable_map=True,
                allies_count=50,
                axis_count=47,
                rating_model_version="role-aware-v2",
                players=[
                    {
                        "rating": {
                            "confidence": 0.7,
                            "role_family": "support",
                        }
                    },
                    {
                        "rating": {
                            "confidence": 0.5,
                            "role_family": "combat_infantry",
                        }
                    },
                ],
            )
        )
    snapshots.append(
        SimpleNamespace(
            round_id=round_id,
            captured_at=start + timedelta(seconds=120),
            counts_match=False,
            fail_count=0,
            stable_map=True,
            allies_count=50,
            axis_count=47,
            rating_model_version="role-aware-v2",
            players=[],
        )
    )
    decision = SimpleNamespace(
        reason={
            "plan": {
                "rating_gap_before": 6.0,
                "projected_rating_gap": 4.0,
            },
            "strategies": {
                strategy: {
                    "projected_rating_gap": gap,
                    "candidates": [{"player_id": "same-player"}],
                }
                for strategy, gap in (
                    ("squad-first", 5.0),
                    ("balanced-v2", 4.0),
                    ("skill-first", 2.0),
                )
            },
        }
    )

    quality = summarize_rating_quality(
        [game],
        snapshots,
        [decision],
        round_start_protection_seconds=0,
        round_end_protection_seconds=0,
    )

    assert quality["expected_snapshots"] == 40
    assert quality["valid_snapshots"] == 38
    assert quality["snapshot_coverage"] == 0.95
    assert quality["exact_rounds"] == 1
    assert quality["median_rating_confidence"] == 0.6
    assert quality["strategy_agreement_rate"] == 1.0
    assert quality["gap_guardrail_rate"] == 1.0
    assert quality["model_versions"] == {"role-aware-v2": 38}
    role_confidence = {row["role_family"]: row for row in quality["role_confidence"]}
    assert role_confidence["support"]["median_confidence"] == 0.7
    assert role_confidence["combat_infantry"]["median_confidence"] == 0.5


def test_candidate_what_if_is_only_built_from_exact_roster_snapshots():
    start = datetime(2026, 8, 4, 18, 0, tzinfo=timezone.utc)
    players = [
        {
            "player_id": "candidate",
            "name": "Candidate",
            "team": "allies",
            "connected_seconds": 600,
            "rating": {"value": 45, "confidence": 0.8},
        },
        {
            "player_id": "axis",
            "name": "Axis",
            "team": "axis",
            "connected_seconds": 600,
            "unit_id": "dog",
            "unit_name": "Dog",
            "unit_size": 3,
            "rating": {"value": 55, "confidence": 0.8},
        },
    ]
    snapshots = [
        SimpleNamespace(
            round_id=f"{int(start.timestamp())}:Carentan",
            captured_at=start + timedelta(seconds=index * 30),
            map_name="Carentan",
            map_elapsed_seconds=index * 30,
            time_remaining_seconds=3600 - index * 30,
            allies_count=50,
            axis_count=47,
            counts_match=True,
            fail_count=0,
            stable_map=True,
            players=players,
            rating_model_version="role-aware-v2",
        )
        for index in range(4)
    ]
    analysis = analyze_snapshot_timeline(
        start,
        start + timedelta(minutes=20),
        snapshots,
        target_difference=2,
        minimum_players=40,
        round_start_protection_seconds=0,
        round_end_protection_seconds=0,
        stable_difference_seconds=45,
    )
    what_if = analysis["candidate_what_if"]
    assert what_if["rating_model_version"] == "role-aware-v2"
    assert set(what_if["strategies"]) == {
        "squad-first",
        "balanced-v2",
        "skill-first",
    }
    assert (
        what_if["strategies"]["balanced-v2"]["candidates"][0]["player_id"]
        == "candidate"
    )


def test_legacy_numeric_snapshot_rating_is_normalized_and_confidence_is_capped():
    player = _snapshot_player(
        {
            "player_id": "legacy-player",
            "name": "Legacy",
            "team": "allies",
            "rating": 67.5,
            "rating_confidence": 0.9,
        }
    )

    assert player is not None
    assert player.rating.version == "legacy"
    assert player.rating.value == 67.5
    assert player.rating.raw_value == 67.5
    assert player.rating.confidence == 0.4
    assert player.rating.role_family == "legacy"


class _QueryResult:
    def __init__(self, rows):
        self.rows = rows

    def all(self):
        return self.rows


class _DashboardSession:
    def __init__(self, rows_by_query):
        self.rows_by_query = list(rows_by_query)

    def execute(self, _query):
        return _QueryResult(self.rows_by_query.pop(0))


def test_dashboard_materializes_rows_before_database_sessions_close(monkeypatch):
    start = datetime(2026, 8, 3, 18, 0, tzinfo=timezone.utc)
    end = start + timedelta(minutes=20)
    game = SimpleNamespace(
        id=7,
        start=start,
        end=end,
        server_number=1,
        map_name="Carentan",
    )
    analysis = reconstruct_round_timeline(
        start,
        end,
        team_events(start, 41, 40),
        target_difference=2,
        minimum_players=40,
        round_start_protection_seconds=0,
        round_end_protection_seconds=0,
        stable_difference_seconds=45,
    )
    analysis["round"] = {
        "map_id": 7,
        "round_id": f"{int(start.timestamp())}:Carentan",
        "map_name": "Carentan",
        "start": start.isoformat(),
        "end": end.isoformat(),
    }
    sessions = [
        _DashboardSession([[game]]),
        _DashboardSession([[(7, analysis)]]),
        _DashboardSession([[], []]),
    ]

    @contextmanager
    def fake_enter_session():
        yield sessions.pop(0)

    monkeypatch.setattr(history_module, "enter_session", fake_enter_session)

    result = RoundHistoryRepository(1).dashboard(
        target_difference=2,
        minimum_players=40,
        round_start_protection_seconds=0,
        round_end_protection_seconds=0,
        stable_difference_seconds=45,
    )

    assert result["backfill"] == {
        "requested_rounds": 1,
        "analyzed_rounds": 1,
        "remaining_rounds": 0,
        "complete": True,
    }
    assert sessions == []
