from copy import deepcopy
from datetime import datetime, timedelta, timezone

import pytest

from rcon.playtime_reconstruction import reconstruct, utc


def evidence():
    start = datetime(2026, 10, 24, 17, tzinfo=timezone.utc)
    end = start + timedelta(hours=1)
    joined = end - timedelta(seconds=51)
    left = end + timedelta(minutes=10)
    return {
        "before": {
            "time_seconds": -49,
            "playersteamid_id": 10,
            "kills": 0,
            "deaths": 0,
            "teamkills": 0,
            "deaths_by_tk": 0,
        },
        "round": {"start": start, "end": end, "server_number": 3},
        "markers": [
            {"event_time": start, "type": "MATCH START"},
            {"event_time": end, "type": "MATCH ENDED"},
        ],
        "transitions": [
            {"event_time": joined, "type": "CONNECTED"},
            {"event_time": left, "type": "DISCONNECTED"},
        ],
        "sessions": [{"start": joined, "end": left, "server_number": 3}],
        "activity": [],
    }


def test_late_join_uses_real_round_end_without_cooldown():
    assert reconstruct(evidence())["after"]["time_seconds"] == 51


def test_early_leave_clips_prior_connection_to_start_without_warmup():
    e = evidence()
    a = e["round"]["start"] - timedelta(hours=1)
    b = e["round"]["start"] + timedelta(seconds=10)
    e["transitions"][0]["event_time"] = e["sessions"][0]["start"] = a
    e["transitions"][1]["event_time"] = e["sessions"][0]["end"] = b
    assert reconstruct(e)["after"]["time_seconds"] == 10


def test_reconnect_and_duplicate_events_do_not_double_count():
    e = evidence()
    a = e["round"]["start"]
    b = a + timedelta(seconds=100)
    e["transitions"] += [
        {"event_time": a, "type": "CONNECTED"},
        {"event_time": b, "type": "DISCONNECTED"},
    ]
    e["transitions"] += deepcopy(e["transitions"])
    e["sessions"] += [{"start": a, "end": b, "server_number": 3}]
    assert reconstruct(e)["after"]["time_seconds"] == 151


@pytest.mark.parametrize("field", ["markers", "transitions", "sessions"])
def test_missing_evidence_never_becomes_zero(field):
    e = evidence()
    e[field] = []
    result = reconstruct(e)
    assert result["status"] == "unresolved"
    assert "after" not in result


def test_missing_disconnect_is_not_assumed_to_be_round_end():
    e = evidence()
    e["transitions"].pop()
    assert reconstruct(e)["reason"] == "connection_end_missing"


def test_cross_server_session_not_accepted():
    e = evidence()
    e["sessions"][0]["server_number"] = 4
    assert reconstruct(e)["reason"] == "session_log_disagreement"


def test_duplicate_connect_at_different_time_is_ambiguous():
    e = evidence()
    e["transitions"].append(
        {
            "event_time": e["sessions"][0]["start"] + timedelta(seconds=1),
            "type": "CONNECTED",
        }
    )
    assert reconstruct(e)["reason"] == "ambiguous_connection_sequence"


def test_session_timestamp_disagreement_rejected():
    e = evidence()
    e["sessions"][0]["end"] += timedelta(seconds=1)
    assert reconstruct(e)["reason"] == "session_log_disagreement"


def test_unclosed_session_rejected():
    e = evidence()
    e["sessions"][0]["end"] = None
    assert reconstruct(e)["reason"] == "session_boundary_missing"


def test_activity_outside_connection_rejected():
    e = evidence()
    e["activity"] = [{"event_time": e["round"]["start"], "type": "CHAT"}]
    assert reconstruct(e)["reason"] == "activity_outside_connection"


def test_missing_combat_logs_rejected():
    e = evidence()
    e["before"]["kills"] = 1
    assert reconstruct(e)["reason"] == "combat_log_disagreement"


def test_rates_recomputed_but_combat_values_unchanged():
    e = evidence()
    a = e["round"]["end"] - timedelta(seconds=120)
    e["sessions"][0]["start"] = e["transitions"][0]["event_time"] = a
    e["before"]["kills"] = 1
    e["activity"] = [
        {"event_time": a, "type": "KILL", "player1_steamid": 10, "player2_steamid": 20}
    ]
    original = deepcopy(e)
    result = reconstruct(e)
    assert result["after"] == {
        "time_seconds": 120,
        "kills_per_minute": 0.5,
        "deaths_per_minute": 0.0,
    }
    assert e == original


def test_invalid_old_round_rejected():
    e = evidence()
    e["round"]["start"] -= timedelta(days=300)
    assert reconstruct(e)["reason"] == "invalid_or_unusually_long_round"


def test_positive_row_never_overwritten():
    e = evidence()
    e["before"]["time_seconds"] = 51
    assert reconstruct(e)["reason"] == "not_negative"


def test_intervening_match_boundary_rejected():
    e = evidence()
    e["markers"].append(
        {
            "event_time": e["round"]["start"] + timedelta(minutes=20),
            "type": "MATCH ENDED",
        }
    )
    assert reconstruct(e)["reason"] == "round_boundaries_not_confirmed"


def test_naive_db_utc_and_dst_offsets_normalize():
    assert utc("2026-10-25 01:30:00") == utc("2026-10-25T02:30:00+01:00")
    assert utc("2026-10-25 00:30:00") == utc("2026-10-25T02:30:00+02:00")


def manifest():
    e = evidence()
    e["before"].update(id=1, map_id=2)
    e["round"]["id"] = 2
    plan = {"rows": [{"id": 1, "map_id": 2, "server_number": 3, **reconstruct(e)}]}
    return e, plan


def test_manifest_accepts_only_recalculated_values():
    from scripts.repair_reconstructed_playtimes import validate_plan

    e, plan = manifest()
    assert len(validate_plan([e], {}, plan)) == 1
    plan["rows"][0]["after"]["time_seconds"] = 999
    with pytest.raises(AssertionError, match="Plan no longer matches"):
        validate_plan([e], {}, plan)


def test_manifest_refuses_other_servers_and_duplicate_rows():
    from scripts.repair_reconstructed_playtimes import validate_plan

    e, plan = manifest()
    with pytest.raises(AssertionError, match="Duplicate evidence"):
        validate_plan([e, e], {}, plan)
    e["round"]["server_number"] = 1
    with pytest.raises(AssertionError, match="Unauthorized server"):
        validate_plan([e], {}, plan)


def test_manifest_refuses_changed_round_identity():
    from scripts.repair_reconstructed_playtimes import validate_plan

    e, plan = manifest()
    plan["rows"][0]["map_id"] = 99
    with pytest.raises(AssertionError):
        validate_plan([e], {}, plan)
