"""Readiness is aggregate evidence, not a delivery or peer guarantee."""
import os
from contextlib import nullcontext
from types import SimpleNamespace
from uuid import uuid4

import pytest
import redis

from rcon import barricade_scan_journal as journal, barricade_scan_status as status
from rcon import session_journal_observation as observation
from rcon.player_presence import capture_observation, database_scope, redis_time, snapshot_key
from tests.test_barricade_scan_journal_postgres import database, prepare


def test_disabled_status_never_accesses_database(monkeypatch):
    monkeypatch.setenv('HLL_BARRICADE_DURABLE_SCANS', '0')
    monkeypatch.setattr(status, 'get_session_maker', lambda: pytest.fail('no database needed'))
    assert status.scan_status(3) == {'state': 'disabled'}


def test_unset_flag_checks_registration_and_database_failure_is_unavailable(monkeypatch):
    monkeypatch.delenv('HLL_BARRICADE_DURABLE_SCANS', raising=False)
    monkeypatch.setattr(status, 'get_session_maker', lambda: (_ for _ in ()).throw(RuntimeError('unavailable')))
    assert status.scan_status(3) == {'state': 'unavailable'}


def test_aggregate_status_requires_registration_roster_and_current_log_observation(database, monkeypatch):
    url = os.getenv('TEST_REDIS_URL')
    if not url:
        pytest.skip('requires disposable Redis')
    prepare(database, monkeypatch)
    monkeypatch.setattr(status, 'get_session_maker', lambda: database)
    monkeypatch.delenv('HLL_BARRICADE_DURABLE_SCANS', raising=False)
    db_url = f'postgresql://synthetic@localhost/db_{uuid4().hex}'
    monkeypatch.setenv('HLL_DB_URL', db_url)
    scope = database_scope(db_url)
    client = redis.Redis.from_url(url, decode_responses=True)
    monkeypatch.setattr(status, 'get_redis_client', lambda **_kwargs: client)
    try:
        assert status.scan_status(3) == {'state': 'unregistered'}
        journal.set_integration_credential(3, '01234567-89ab-4def-8012-0123456789ab',
            expected_credential_id=None, new_credential_id=1, actor='test', reason='synthetic')
        assert status.scan_status(4) == {'state': 'unregistered'}
        assert status.scan_status(3) == {'state': 'waiting_roster'}
        api = SimpleNamespace(without_retries=lambda: nullcontext(), get_player_ids=lambda: [])
        assert capture_observation(client, api, scope=scope, server_number=3)
        assert status.scan_status(3) == {'state': 'waiting_logs'}
        def publish(pending):
            start, finish = redis_time(client), redis_time(client)
            return observation.publish(client, SimpleNamespace(pending_counts=lambda _: (pending, 0)),
                scope=scope, server_number=3, poll_started_at=start, poll_finished_at=finish)
        assert publish(1)
        assert status.scan_status(3) == {'state': 'pending_logs'}
        assert publish(0)
        assert status.scan_status(3) == {'state': 'evidence_available'}
        observation.invalidate(client, scope=scope, server_number=3)
        assert status.scan_status(3) == {'state': 'waiting_logs'}
        monkeypatch.setattr(status, 'get_redis_client', lambda **_kwargs: (_ for _ in ()).throw(OSError('secret')))
        assert status.scan_status(3) == {'state': 'unavailable'}
    finally:
        client.delete(snapshot_key(scope, 3), observation.observation_key(scope, 3))
        client.close()
