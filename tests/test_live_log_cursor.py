import pytest

from rcon.live_log_cursor import event_cursor, get_live_log_page


def line(i, stamp=1000, action="CHAT[Team]"):
    return {
        "timestamp_ms": stamp,
        "line_without_time": f"event {i}",
        "action": action,
        "message": f"event {i}",
        "player_name_1": "Test",
        "player_name_2": None,
    }


def test_equal_timestamps_and_metadata_changes_do_not_lose_events():
    history = [line(i) for i in range(5)]
    first = get_live_log_page(log_history=history, limit=2)
    assert len(first["logs"]) == 2 and first["has_older"]
    history[0]["player_id_1"] = "enriched"
    history.insert(0, line("new"))
    delta = get_live_log_page(log_history=history, after=first["newest"], limit=2)
    assert [x["message"] for x in delta["logs"]] == ["event new"]
    older = get_live_log_page(log_history=history, before=first["oldest"], limit=2)
    assert [x["message"] for x in older["logs"]] == ["event 2", "event 3"]
    assert older["has_older"] and not older["reset"]


def test_filtered_empty_pages_advance_cursor():
    history = [line(1, action="KILL"), line(2, action="KILL"), line(3)]
    first = get_live_log_page(log_history=history, limit=2, action_filter=["CHAT"])
    assert first["logs"] == [] and first["oldest"] and first["has_older"]
    next_page = get_live_log_page(
        log_history=history, limit=2, before=first["oldest"], action_filter=["CHAT"]
    )
    assert len(next_page["logs"]) == 1 and not next_page["has_older"]


def test_exclusion_and_player_filters_are_preserved():
    history = [line(1), line(2, action="KILL")]
    page = get_live_log_page(
        log_history=history,
        action_filter=["CHAT"],
        inclusive_filter=False,
        player_search=["Test"],
    )
    assert [x["message"] for x in page["logs"]] == ["event 2"]


@pytest.mark.parametrize("direction", ["after", "before"])
def test_missing_anchor_explicitly_resets_to_latest_page(direction):
    page = get_live_log_page(
        log_history=[line(i) for i in range(4)], limit=2, **{direction: "f" * 64}
    )
    assert page["reset"] and page["has_older"] and len(page["logs"]) == 2


def test_larger_gap_does_not_silently_skip_events():
    history = [line(i) for i in range(5)]
    page = get_live_log_page(
        log_history=history, limit=2, after=event_cursor(history[-1])
    )
    assert page["reset"] == "window_exceeded" and page["has_older"]


def test_idle_poll_keeps_newest_anchor():
    anchor = event_cursor(line(1))
    page = get_live_log_page(log_history=[line(1)], after=anchor)
    assert page["logs"] == [] and page["newest"] == anchor and not page["reset"]


def test_empty_history_after_restart_is_an_explicit_reset():
    assert (
        get_live_log_page(log_history=[], after="f" * 64)["reset"] == "cursor_expired"
    )


def test_overlapping_pages_from_concurrent_prepends_are_deduplicated():
    class History:
        def iter_range(self, **kwargs):
            yield from [line(1), line(2), line(2), line(3), line(4)]

    result = get_live_log_page(log_history=History(), limit=4)
    assert len(result["logs"]) == 4 and not result["has_older"]


@pytest.mark.parametrize(
    "kwargs",
    [
        {"after": "invalid"},
        {"before": "a" * 65},
        {"after": "a" * 64, "before": "b" * 64},
        {"limit": 0},
        {"limit": 2001},
        {"limit": True},
        {"limit": 1.5},
    ],
)
def test_invalid_cursor_requests_are_rejected(kwargs):
    with pytest.raises(ValueError):
        get_live_log_page(log_history=[], **kwargs)
