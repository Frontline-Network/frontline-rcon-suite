from collections import defaultdict
from unittest import mock

from rcon import game_logs, recent_actions
from rcon.logs.stream import LogStream


def test_recent_logs_reads_only_requested_page(monkeypatch):
    log_history = mock.MagicMock()
    log_history.__len__.return_value = 100_000
    log_history.__getitem__.return_value = []
    log_history.__iter__.side_effect = AssertionError("full Redis list was read")
    monkeypatch.setattr(game_logs.LogLoop, "get_log_history_list", lambda: log_history)

    result = game_logs.get_recent_logs(start=0, end=250)

    assert result["logs"] == []
    log_history.__getitem__.assert_called_once_with(slice(0, 250))
    log_history.__iter__.assert_not_called()


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
