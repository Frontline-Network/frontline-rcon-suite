import datetime
from collections import defaultdict
from types import SimpleNamespace
from unittest import mock

import orjson

from rcon import game_logs, recent_actions
from rcon.logs.recorder import LOG_HISTORY_PAGE_SIZE, LogRecorder
from rcon.logs.stream import LogStream
from rcon.utils import LogsHistory, LogsHistorySnapshot


def test_recent_logs_reads_only_requested_page(monkeypatch):
    log_history = mock.MagicMock()
    log_history.iter_range.return_value = iter([])
    log_history.__iter__.side_effect = AssertionError("full Redis list was read")
    monkeypatch.setattr(game_logs.LogLoop, "get_log_history_list", lambda: log_history)

    result = game_logs.get_recent_logs(start=0, end=250)

    assert result["logs"] == []
    log_history.iter_range.assert_called_once_with(start=0, stop=250)
    log_history.__iter__.assert_not_called()


def test_dashboard_log_summary_bounds_and_projects_payload():
    def line(index, action="KILL", message=""):
        return {
            "timestamp_ms": 2_000 - index,
            "action": action,
            "message": message,
            "player_name_1": "one",
            "player_id_1": "1",
            "player_name_2": "two",
            "player_id_2": "2",
            "raw": "large field not needed by dashboard",
            "weapon": "not needed",
        }

    source = [line(index) for index in range(150)]
    source.extend(
        [
            line(151, "CHAT[Team]", "normal"),
            line(152, "CHAT[Team]", "!admin help"),
        ]
    )
    history = mock.Mock()
    history.iter_range.return_value = iter(source)

    result = game_logs.get_recent_logs_summary(
        end=15_000,
        per_action_limit=100,
        log_history=history,
    )
    groups = {item["group"]: item["logs"] for item in result["groups"]}

    assert len(groups["KILL"]) == 100
    assert groups["KILL"][0] == {
        "player_id_1": "1",
        "player_name_1": "one",
        "player_id_2": "2",
        "player_name_2": "two",
        "message": "",
        "timestamp_ms": 2_000,
        "action": "KILL",
    }
    assert [item["message"] for item in result["admin_logs"]] == ["!admin help"]
    history.iter_range.assert_called_once_with(start=0, stop=15_000)


def test_fixed_len_list_iter_range_stops_after_short_page():
    history = LogsHistory.__new__(LogsHistory)
    history.red = mock.Mock()
    history.key = "logs_history"
    history.deserializer = lambda value: int(value)
    history.red.lrange.side_effect = [[b"5", b"4"], [b"3"]]

    assert list(history.iter_range(start=0, stop=10, page_size=2)) == [5, 4, 3]
    assert history.red.lrange.call_args_list == [
        mock.call("logs_history", 0, 1),
        mock.call("logs_history", 2, 3),
    ]


def test_recent_logs_timestamp_filter_does_not_fetch_older_pages():
    new_log = {
        "timestamp_ms": 2_000,
        "action": "CHAT",
        "player_name_1": "new",
        "player_name_2": None,
    }
    old_log = {
        "timestamp_ms": 999,
        "action": "CHAT",
        "player_name_1": "old",
        "player_name_2": None,
    }
    history = LogsHistory.__new__(LogsHistory)
    history.red = mock.Mock()
    history.key = "logs_history"
    history.deserializer = orjson.loads
    history.red.lrange.return_value = [
        orjson.dumps(new_log),
        orjson.dumps(old_log),
        *[orjson.dumps(old_log) for _ in range(498)],
    ]

    result = game_logs.get_recent_logs(
        min_timestamp=1.0,
        log_history=history,
    )

    assert result["logs"] == [new_log]
    history.red.lrange.assert_called_once_with("logs_history", 0, 499)


def test_log_history_snapshot_reuses_pages():
    source = mock.Mock()
    source.iter_range.side_effect = [iter(["new", "middle"]), iter(["old"])]
    snapshot = LogsHistorySnapshot(history=source, page_size=2)

    assert list(snapshot.iter_range(stop=3)) == ["new", "middle", "old"]
    assert list(snapshot.iter_range(stop=3)) == ["new", "middle", "old"]
    assert source.iter_range.call_args_list == [
        mock.call(start=0, stop=2, page_size=2),
        mock.call(start=2, stop=4, page_size=2),
    ]


def test_log_recorder_pages_until_last_persisted_log():
    last_timestamp = datetime.datetime.fromtimestamp(1, datetime.UTC)
    new_log = {
        "timestamp_ms": 2_000,
        "line_without_time": "CHAT: new",
    }
    last_log = {
        "timestamp_ms": 1_000,
        "line_without_time": "CHAT: saved",
    }
    older_log = {
        "timestamp_ms": 500,
        "line_without_time": "CHAT: old",
    }
    history = mock.Mock()
    history.iter_range.return_value = iter([new_log, last_log, older_log])
    session = mock.Mock()
    session.query.return_value.filter.return_value.order_by.return_value.limit.return_value.one_or_none.return_value = SimpleNamespace(
        event_time=last_timestamp,
        raw="[0 ms (1)] CHAT: saved",
    )
    recorder = LogRecorder.__new__(LogRecorder)
    recorder.server_id = "1"
    recorder.log_history_fn = lambda: history

    assert recorder._get_new_logs(session) == [new_log]
    history.iter_range.assert_called_once_with(page_size=LOG_HISTORY_PAGE_SIZE)


def test_recent_actions_invalidates_exact_cache_key(monkeypatch):
    clear_for = mock.Mock()
    cache_clear = mock.Mock()
    monkeypatch.setattr(recent_actions.get_recent_actions, "clear_for", clear_for)
    monkeypatch.setattr(recent_actions.get_recent_actions, "cache_clear", cache_clear)

    actions = defaultdict(recent_actions.MostRecentEvents)
    recent_actions.set_recent_actions(actions)

    assert recent_actions.RECENT_ACTIONS is actions
    clear_for.assert_called_once_with()
    cache_clear.assert_not_called()


def test_log_stream_skips_ids_at_or_before_stream_tail():
    stream = LogStream.__new__(LogStream)
    stream.log_stream = mock.Mock()
    stream.log_stream.add.return_value = "103-0"
    logs = [
        {"timestamp_ms": 103_000},
        {"timestamp_ms": 102_000},
        {"timestamp_ms": 101_000},
    ]

    last_seen_id, new_logs = stream._append_new_logs(logs, "102-0")

    assert last_seen_id == "103-0"
    assert new_logs == 1
    stream.log_stream.add.assert_called_once_with(
        custom_id="103-0", obj={"timestamp_ms": 103_000}
    )


def test_log_stream_id_comparison_uses_numeric_parts():
    assert LogStream._stream_id_parts("10-12") > LogStream._stream_id_parts("9-99")
