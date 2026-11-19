from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4
import os

import pytest
import redis

from rcon import player_history, session_event_review
from rcon import barricade_scan_journal
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
    monkeypatch.setattr(barricade_scan_journal, 'has_registered_integration', lambda _server: False)
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


def test_optional_backlog_observation_runs_after_log_processing(tmp_path, monkeypatch):
    from rcon import session_journal_observation as observations
    instance = make_loop(tmp_path, monkeypatch, [])
    monkeypatch.setattr(barricade_scan_journal, 'has_registered_integration', lambda _server: True)
    monkeypatch.setenv('HLL_BARRICADE_JOURNAL_OBSERVATIONS', '1')
    monkeypatch.setenv('HLL_DB_URL', 'postgresql://synthetic@localhost/test')
    red = Mock()
    red.time.side_effect = [(1000, 0), (1001, 0)]
    publish = Mock()
    monkeypatch.setattr(log_loop, 'get_redis_client', lambda **_kwargs: red)
    monkeypatch.setattr(observations, 'publish', publish)
    instance.process_logs()
    publish.assert_called_once()
    assert publish.call_args.args == (red, instance.session_journal)
    assert publish.call_args.kwargs['server_number'] == 3
    assert publish.call_args.kwargs['poll_started_at'] == 1000
    assert publish.call_args.kwargs['poll_finished_at'] == 1001


def test_unregistered_server_does_not_publish_observations(tmp_path, monkeypatch):
    instance = make_loop(tmp_path, monkeypatch, [])
    monkeypatch.delenv('HLL_BARRICADE_JOURNAL_OBSERVATIONS', raising=False)
    redis_client = Mock(side_effect=AssertionError('must not access Redis'))
    monkeypatch.setattr(log_loop, 'get_redis_client', redis_client)
    instance.process_logs()
    redis_client.assert_not_called()


@pytest.mark.parametrize('flag', ['HLL_BARRICADE_DURABLE_SCANS', 'HLL_BARRICADE_JOURNAL_OBSERVATIONS'])
def test_explicit_disable_skips_registration_and_observation(tmp_path, monkeypatch, flag):
    instance = make_loop(tmp_path, monkeypatch, [])
    check = Mock(side_effect=AssertionError('must not query'))
    monkeypatch.setattr(barricade_scan_journal, 'has_registered_integration', check)
    monkeypatch.setenv(flag, '0')
    redis_client = Mock(side_effect=AssertionError('must not use Redis'))
    monkeypatch.setattr(log_loop, 'get_redis_client', redis_client)
    instance.process_logs()
    check.assert_not_called()
    redis_client.assert_not_called()


def test_registration_database_failure_does_not_interrupt_log_loop(tmp_path, monkeypatch):
    instance = make_loop(tmp_path, monkeypatch, [])
    monkeypatch.delenv('HLL_BARRICADE_JOURNAL_OBSERVATIONS', raising=False)
    monkeypatch.delenv('HLL_BARRICADE_DURABLE_SCANS', raising=False)
    monkeypatch.setattr(barricade_scan_journal, 'has_registered_integration', Mock(side_effect=RuntimeError('offline')))
    redis_client = Mock(side_effect=AssertionError('must not use Redis'))
    monkeypatch.setattr(log_loop, 'get_redis_client', redis_client)
    instance.process_logs()
    instance.rcon.get_structured_logs.assert_called_once()
    redis_client.assert_not_called()


def test_observation_failure_never_interrupts_log_processing(tmp_path, monkeypatch, caplog):
    from rcon import session_journal_observation as observations
    instance = make_loop(tmp_path, monkeypatch, [])
    monkeypatch.setattr(barricade_scan_journal, 'has_registered_integration', lambda _server: True)
    monkeypatch.setenv('HLL_BARRICADE_JOURNAL_OBSERVATIONS', '1')
    monkeypatch.setenv('HLL_DB_URL', 'postgresql://synthetic@localhost/test')
    red = Mock()
    red.time.side_effect = [(1000, 0), (1001, 0), (1002, 0), (1003, 0)]
    monkeypatch.setattr(log_loop, 'get_redis_client', lambda **_kwargs: red)
    publish = Mock(side_effect=OSError('sensitive synthetic detail'))
    monkeypatch.setattr(observations, 'publish', publish)
    instance.process_logs()
    instance.process_logs()
    assert publish.call_count == 2
    assert 'sensitive synthetic detail' not in caplog.text
    assert caplog.text.count('Session journal observation unavailable') == 1


def test_failed_log_fetch_does_not_publish_new_observation(tmp_path, monkeypatch):
    instance = make_loop(tmp_path, monkeypatch, [])
    instance.rcon.get_structured_logs.side_effect = OSError('synthetic outage')
    instance._publish_session_journal_observation = Mock()
    with pytest.raises(OSError):
        instance.process_logs()
    instance._publish_session_journal_observation.assert_not_called()


@pytest.mark.skipif(not os.environ.get('TEST_REDIS_URL'), reason='requires isolated Redis')
def test_log_loop_publishes_bounded_backlog_observation_to_real_redis(tmp_path, monkeypatch):
    from rcon.player_presence import database_scope
    from rcon import session_journal_observation as observations
    instance = make_loop(tmp_path, monkeypatch, [])
    monkeypatch.setattr(barricade_scan_journal, 'has_registered_integration', lambda _server: True)
    url = f'postgresql://synthetic@localhost/db_{uuid4().hex}'
    scope = database_scope(url)
    client = redis.Redis.from_url(os.environ['TEST_REDIS_URL'], decode_responses=True)
    key = observations.observation_key(scope, 3)
    monkeypatch.setenv('HLL_BARRICADE_JOURNAL_OBSERVATIONS', '1')
    monkeypatch.setenv('HLL_DB_URL', url)
    monkeypatch.setattr(log_loop, 'get_redis_client', lambda **_kwargs: client)
    try:
        instance.process_logs()
        value = observations.read(client, scope=scope, server_number=3)
        assert value is not None
        assert value.poll_started_at <= value.poll_finished_at <= value.started_at <= value.finished_at
        assert (value.pending, value.unpublished_anonymous) == (0, 0)
        assert client.ttl(key) > 0
    finally:
        client.delete(key)
        client.close()
