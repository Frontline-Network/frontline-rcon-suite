"""Registration-scoped activation using disposable PostgreSQL and a local journal."""
from unittest.mock import Mock
from sqlalchemy import select

from rcon import barricade_scan_journal as journal, session_journal_observation as observation
from rcon.logs import loop as log_loop
from tests.test_barricade_scan_journal_postgres import database, prepare
from tests.test_log_loop_session_journal import make_loop


def test_registration_activates_only_its_server_without_environment_flags(database, monkeypatch, tmp_path):
    prepare(database, monkeypatch)
    monkeypatch.delenv('HLL_BARRICADE_DURABLE_SCANS', raising=False)
    monkeypatch.delenv('HLL_BARRICADE_JOURNAL_OBSERVATIONS', raising=False)
    monkeypatch.setenv('HLL_DB_URL', 'postgresql://synthetic@localhost/test')
    peer = '01234567-89ab-4def-8012-0123456789ab'
    assert journal.set_integration_credential(3, peer, expected_credential_id=None,
        new_credential_id=1, actor='test', reason='test')
    actual_check = journal.has_registered_integration
    calls = Mock(side_effect=actual_check)
    red = Mock()
    red.time.side_effect = [(1000, 0), (1001, 0)]
    invalidate, publish = Mock(), Mock()
    monkeypatch.setattr(log_loop, 'get_redis_client', lambda **_kwargs: red)
    monkeypatch.setattr(observation, 'invalidate', invalidate)
    monkeypatch.setattr(observation, 'publish', publish)
    for server in (3, 4):
        directory = tmp_path / str(server)
        directory.mkdir()
        events = [{'action': 'CONNECTED', 'player_id_1': 'synthetic', 'timestamp_ms': 2000}]
        collector = make_loop(directory, monkeypatch, events)
        collector.session_server_number = server
        collector._drain_session_events = Mock()
        monkeypatch.setattr(journal, 'has_registered_integration', calls)
        collector.process_logs()
    assert [call.args[0] for call in calls.call_args_list] == [3, 4]
    invalidate.assert_called_once()
    publish.assert_called_once()
    with database() as session:
        records = session.scalars(select(journal.BarricadeConnectObservation)).all()
        assert len(records) == 1 and records[0].server_number == 3


def test_missing_registration_table_does_not_interrupt_collector(database, monkeypatch, tmp_path):
    monkeypatch.delenv('HLL_BARRICADE_DURABLE_SCANS', raising=False)
    monkeypatch.delenv('HLL_BARRICADE_JOURNAL_OBSERVATIONS', raising=False)
    real_check = journal.has_registered_integration
    collector = make_loop(tmp_path, monkeypatch, [])
    collector._drain_session_events = Mock()
    monkeypatch.setattr(journal, 'has_registered_integration', real_check)
    monkeypatch.setattr(journal, 'get_session_maker', lambda: database)
    redis_client = Mock(side_effect=AssertionError('must not touch Redis'))
    monkeypatch.setattr(log_loop, 'get_redis_client', redis_client)
    collector.process_logs()
    collector.rcon.get_structured_logs.assert_called_once()
    redis_client.assert_not_called()
