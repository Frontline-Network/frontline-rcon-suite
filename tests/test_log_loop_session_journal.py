from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon import player_history, session_event_review
from rcon.logs import loop as log_loop
from rcon.session_event_journal import SessionEventJournal


def make_loop(tmp_path, monkeypatch, logs):
    instance = object.__new__(log_loop.LogLoop)
    instance.session_server_number = 3
    instance.session_journal = SessionEventJournal(tmp_path / "session-events.sqlite")
    instance.session_cutover_us = instance.session_journal.cutover_us(1000)
    instance.GET_LOGS_SINCE_MIN = 180
    instance.rcon = Mock()
    instance.rcon.get_structured_logs.return_value = {"logs": logs}
    instance.record_line = Mock(return_value=None)  # duplicate or older log
    instance.process_hooks = Mock()
    monkeypatch.setattr(log_loop, "MapsHistory", lambda: SimpleNamespace(get_current_map=lambda: None))
    return instance


def test_duplicate_or_late_logs_reach_session_writer_without_replaying_hooks(tmp_path, monkeypatch):
    logs = [{"action": "DISCONNECTED", "player_id_1": "console-1", "timestamp_ms": 2000}]
    instance = make_loop(tmp_path, monkeypatch, logs)
    end = Mock()
    monkeypatch.setattr(player_history, "save_end_player_session", end)
    instance.process_logs()
    end.assert_called_once_with("console-1", 2.0)
    instance.process_hooks.assert_not_called()
    instance.process_logs()
    end.assert_called_once()


def test_database_failure_survives_restart_and_retry_does_not_run_other_hooks(tmp_path, monkeypatch):
    logs = [{"action": "CONNECTED", "player_id_1": "console-1", "timestamp_ms": 2000}]
    instance = make_loop(tmp_path, monkeypatch, logs)
    start = Mock(side_effect=RuntimeError("database unavailable"))
    monkeypatch.setattr(player_history, "save_start_player_session", start)
    instance.process_logs()
    instance.process_hooks.assert_not_called()
    start.reset_mock(side_effect=True)
    start.return_value = True
    instance.session_journal = SessionEventJournal(tmp_path / "session-events.sqlite")
    instance.rcon.get_structured_logs.return_value = {"logs": []}
    instance.process_logs()
    start.assert_called_once_with("console-1", 2.0, server_number=3)
    instance.process_hooks.assert_not_called()


def test_failed_local_commit_prevents_general_log_processing(tmp_path, monkeypatch):
    logs = [{"action": "CONNECTED", "player_id_1": "console-1", "timestamp_ms": 2000}]
    instance = make_loop(tmp_path, monkeypatch, logs)
    monkeypatch.setattr(instance.session_journal, "remember_batch", Mock(side_effect=OSError("disk full")))
    with pytest.raises(OSError):
        instance.process_logs()
    instance.record_line.assert_not_called()
    instance.process_hooks.assert_not_called()
    assert instance.GET_LOGS_SINCE_MIN == 180


def test_anonymous_log_is_retained_for_review_without_creating_a_session(tmp_path, monkeypatch):
    logs = [{"action": "DISCONNECTED", "player_id_1": None, "player_name_1": None,
             "timestamp_ms": 2000, "raw": "DISCONNECTED ()"}]
    instance = make_loop(tmp_path, monkeypatch, logs)
    end = Mock()
    record = Mock()
    monkeypatch.setattr(session_event_review, "record_unidentified", record)
    monkeypatch.setattr(player_history, "save_end_player_session", end)
    instance.process_logs()
    assert instance.session_journal.list_unidentified(3) == [("disconnect", 2000000, "", "DISCONNECTED ()")]
    record.assert_called_once_with(3, "disconnect", 2000000, "", "DISCONNECTED ()")
    end.assert_not_called()
