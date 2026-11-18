"""Synthetic concurrent scan reservations against disposable PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from contextvars import copy_context
import asyncio
from datetime import datetime
import time
import os
import subprocess
import sys

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import func, inspect, select, text

from rcon import barricade_scan_journal as journal
from rcon import barricade_scan_dispatch as adapter
from rcon.barricade_scan_identity import integration_namespace
from rcon.models import PlayerID, PlayerSession, SessionEventResolution
from tests.test_blacklist_sync_journal_postgres import database, queue
from rcon.blacklist_sync_journal import BlacklistSyncDelivery


async def verified(_session_id, _player_id):
    return True


@pytest.mark.parametrize(('event_us', 'expected'), [
    (1_000_000, 'before'), (2_000_000, 'ambiguous'), (3_000_000, 'after'),
    (None, 'unknown'), (2_400_000, 'unknown'), (True, 'unknown'),
])
def test_activation_boundary_retains_second_resolution_uncertainty(event_us, expected):
    assert journal.classify_activation_start(2_500_000, event_us) == expected


def test_activation_boundary_at_exact_second_does_not_assume_event_order():
    assert journal.classify_activation_start(2_000_000, 2_000_000) == 'ambiguous'
    with pytest.raises(ValueError):
        journal.classify_activation_start(True, 2_000_000)


def prepare(database, monkeypatch):
    PlayerID.__table__.create(database.kw['bind'], checkfirst=True)
    PlayerSession.__table__.create(database.kw['bind'], checkfirst=True)
    SessionEventResolution.__table__.create(database.kw['bind'], checkfirst=True)
    journal.BarricadeConnectObservation.__table__.create(database.kw['bind'])
    journal.BarricadeRosterSnapshot.__table__.create(database.kw['bind'])
    journal.BarricadeScanBaseline.__table__.create(database.kw['bind'])
    journal.BarricadeScanDelivery.__table__.create(database.kw['bind'])
    journal.BarricadeScanIntegration.__table__.create(database.kw['bind'])
    journal.BarricadeScanIntegrationAudit.__table__.create(database.kw['bind'])
    journal.BarricadeScanReviewAudit.__table__.create(database.kw['bind'])
    monkeypatch.setattr(journal, 'get_session_maker', lambda: database)


def prepare_adapter(database, monkeypatch):
    prepare(database, monkeypatch)
    monkeypatch.setattr(adapter, 'key_is_live', lambda _credential_id: True)
    assert journal.set_integration_credential(3, '01234567-89ab-4def-8012-0123456789ab',
        expected_credential_id=None, new_credential_id=1, actor='test', reason='register')


def establish_synthetic_join_evidence(database, selected=None):
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    journal.record_roster_snapshot(3, namespace, frozenset())
    with database() as session:
        rows = session.execute(select(PlayerID.player_id, PlayerSession.start_event_us)
                               .join(PlayerSession, PlayerSession.player_id_id == PlayerID.id)).all()
    journal.record_collector_connects([(3, player_id, 'connect', event_us) for player_id, event_us in rows
                                      if event_us is not None and (selected is None or player_id in selected)])


def test_baseline_records_existing_sessions_without_claiming_success(database, monkeypatch):
    prepare(database, monkeypatch)
    peer = '01234567-89ab-4def-8012-0123456789ab'
    with database.begin() as session:
        player = PlayerID(player_id='00000000000000000000000000000001')
        session.add(player)
        session.flush()
        old = PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2026, 1, 1))
        session.add(old)
        session.flush()
        old_id = old.id
    assert journal.set_integration_credential(3, peer, expected_credential_id=None,
        new_credential_id=1, actor='test', reason='synthetic cutover')
    with database.begin() as session:
        assert session.get(journal.BarricadeScanBaseline, (3, peer, old_id)) is not None
        assert session.scalar(select(journal.BarricadeScanDelivery.id)) is None
        fresh = PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2026, 1, 2))
        session.add(fresh)
        session.flush()
        fresh_id = fresh.id
    rows = journal.find_unreserved_open_sessions(3, f'integration:{peer}')
    assert [row[0] for row in rows] == [fresh_id]


def test_collector_events_are_deduplicated_and_ordered_by_database_cutover(database, monkeypatch):
    prepare(database, monkeypatch)
    peer = '01234567-89ab-4def-8012-0123456789ab'
    old_player, new_player = '00000000000000000000000000000001', '00000000000000000000000000000002'
    event_us = 1_700_000_000_000_000
    journal.record_collector_connects([(3, old_player, 'connect', event_us)])
    journal.set_integration_credential(3, peer, expected_credential_id=None, new_credential_id=1,
                                       actor='test', reason='cutover')
    journal.record_roster_snapshot(3, f'integration:{peer}', frozenset())
    journal.record_collector_connects([(3, old_player, 'connect', event_us),
                                       (3, new_player, 'connect', event_us),
                                       (3, new_player, 'connect', event_us)])
    with database.begin() as session:
        boundary = session.get(journal.BarricadeScanIntegration, (3, peer)).registered_at_us
        ids = []
        for player_id in (old_player, new_player):
            player = PlayerID(player_id=player_id)
            session.add(player)
            session.flush()
            row = PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2023, 1, 1), start_event_us=event_us)
            session.add(row)
            session.flush()
            ids.append(row.id)
        assert session.scalar(select(func.count()).select_from(journal.BarricadeConnectObservation)) == 2
    namespace = f'integration:{peer}'
    assert not journal.live_connect_after_cutover(3, namespace, ids[0], old_player, boundary)
    assert journal.live_connect_after_cutover(3, namespace, ids[1], new_player, boundary)


def test_roster_absence_must_precede_connect_and_new_rejoin_can_be_scanned(database, monkeypatch):
    prepare(database, monkeypatch)
    peer = '01234567-89ab-4def-8012-0123456789ab'
    namespace = f'integration:{peer}'
    player_id = '00000000000000000000000000000001'
    journal.set_integration_credential(3, peer, expected_credential_id=None, new_credential_id=1,
                                       actor='test', reason='cutover')
    journal.record_roster_snapshot(3, namespace, frozenset({player_id}))
    journal.record_collector_connects([(3, player_id, 'connect', 1_700_000_000_000_000)])
    journal.record_roster_snapshot(3, namespace, frozenset())
    journal.record_collector_connects([(3, player_id, 'connect', 1_700_000_100_000_000)])
    with database.begin() as session:
        boundary = session.get(journal.BarricadeScanIntegration, (3, peer)).registered_at_us
        player = PlayerID(player_id=player_id)
        session.add(player)
        session.flush()
        rows = [PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2023, 1, 1), start_event_us=event)
                for event in (1_700_000_000_000_000, 1_700_000_100_000_000)]
        session.add_all(rows)
        session.flush()
        first, second = (row.id for row in rows)
    assert not journal.live_connect_after_cutover(3, namespace, first, player_id, boundary)
    assert journal.live_connect_after_cutover(3, namespace, second, player_id, boundary)


def test_roster_transition_dispatches_vietnam_eos_once_and_persists_confirmation(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    eos = '00026a3466a244829409f77af0a752d9'
    journal.record_roster_snapshot(3, namespace, frozenset())
    journal.record_collector_connects([(3, eos, 'connect', 1_700_000_100_000_000)])
    with database.begin() as session:
        player = PlayerID(player_id=eos)
        session.add(player)
        session.flush()
        row = PlayerSession(player_id_id=player.id, server_number=3,
                            start=datetime(2023, 1, 1), start_event_us=1_700_000_100_000_000)
        session.add(row)
        session.flush()
        session_id = row.id
    sent = []
    async def sender(player_id, game):
        sent.append((player_id, game))
    async def roster():
        return frozenset({eos})
    async def run():
        for _ in range(2):
            await adapter.scan_once(3, namespace, 'HLLV', sender, verified,
                                    credential_id=1, get_roster=roster)
    asyncio.run(run())
    assert sent == [(eos, 'HLLV')]
    with database() as session:
        delivery = session.scalar(select(journal.BarricadeScanDelivery).where(
            journal.BarricadeScanDelivery.player_session_id == session_id))
        assert delivery is not None and delivery.status == 'done'


def test_twenty_vietnam_joins_dispatch_once_with_individual_checks(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    ids = [f'{number:032x}' for number in range(20)]
    event_us = 1_700_000_100_000_000
    journal.record_roster_snapshot(3, namespace, frozenset())
    journal.record_collector_connects([(3, player_id, 'connect', event_us) for player_id in ids])
    with database.begin() as session:
        for player_id in ids:
            player = PlayerID(player_id=player_id)
            session.add(player)
            session.flush()
            session.add(PlayerSession(player_id_id=player.id, server_number=3,
                start=datetime(2023, 1, 1), start_event_us=event_us))
    checked, sent = [], []
    async def present(session_id, player_id):
        checked.append((session_id, player_id))
        return True
    async def sender(player_id, game):
        sent.append((player_id, game))
    async def roster():
        return frozenset(ids)
    async def run():
        for _ in range(2):
            await adapter.scan_once(3, namespace, 'HLLV', sender, present,
                                    credential_id=1, get_roster=roster, page_size=7)
    asyncio.run(run())
    assert len(checked) == 20 and {player for _, player in checked} == set(ids)
    assert len(sent) == 20 and {player for player, game in sent if game == 'HLLV'} == set(ids)


def test_key_rotation_preserves_registered_namespace_and_rejects_other_keys(database, monkeypatch):
    prepare(database, monkeypatch)
    peer = '01234567-89ab-4def-8012-0123456789ab'
    query = f'frontline_integration={peer}'.encode()
    assert integration_namespace(query, server_number=3, credential_id=1) is None
    before_registration = time.time_ns() // 1000
    assert journal.set_integration_credential(3, peer, expected_credential_id=None, new_credential_id=1,
                                              actor='test-operator', reason='register synthetic peer')
    with database() as session:
        registered_at = session.get(journal.BarricadeScanIntegration, (3, peer)).registered_at_us
    assert before_registration <= registered_at <= time.time_ns() // 1000
    namespace = integration_namespace(query, server_number=3, credential_id=1)
    assert namespace == f'integration:{peer}'
    assert integration_namespace(b'', server_number=3, credential_id=1) == namespace
    assert integration_namespace(b'frontline_integration=invalid', server_number=3, credential_id=1) is None
    assert integration_namespace(query, server_number=3, credential_id=2) is None
    assert integration_namespace(query, server_number=4, credential_id=1) is None
    for invalid in (None, 0, -1, True, '1'):
        assert integration_namespace(query, server_number=3, credential_id=invalid) is None
    with journal.delivery_scope(3, namespace):
        assert journal.reserve(3, namespace, 77, 'synthetic-eos', 'HLLV') is not None
    # Caller authorization must be enforced at the management boundary.
    assert journal.set_integration_credential(3, peer, expected_credential_id=1, new_credential_id=2,
                                              actor='test-operator', reason='synthetic rotation')
    with database() as session:
        assert session.get(journal.BarricadeScanIntegration, (3, peer)).registered_at_us == registered_at
    assert integration_namespace(query, server_number=3, credential_id=1) is None
    assert integration_namespace(query, server_number=3, credential_id=2) == namespace
    with journal.delivery_scope(3, namespace):
        assert journal.reserve(3, namespace, 77, 'synthetic-eos', 'HLLV') is None
    with pytest.raises(ValueError, match='credential changed'):
        journal.set_integration_credential(3, peer, expected_credential_id=1, new_credential_id=3,
                                           actor='test-operator', reason='stale operation')
    with database() as session:
        audits = session.scalars(select(journal.BarricadeScanIntegrationAudit).order_by(
            journal.BarricadeScanIntegrationAudit.id)).all()
        assert [(row.old_credential_id, row.new_credential_id) for row in audits] == [(None, 1), (1, 2)]


def test_rotation_waits_for_active_delivery(database, monkeypatch):
    prepare(database, monkeypatch)
    peer = '01234567-89ab-4def-8012-0123456789ab'
    assert journal.set_integration_credential(3, peer, expected_credential_id=None, new_credential_id=1,
                                             actor='test', reason='register')
    started, done = Event(), Event()
    def rotate():
        started.set()
        result = journal.set_integration_credential(3, peer, expected_credential_id=1, new_credential_id=2,
                                                    actor='test', reason='rotate')
        done.set()
        return result
    with ThreadPoolExecutor(max_workers=1) as pool:
        with journal.delivery_scope(3, f'integration:{peer}'):
            delivery_id = journal.reserve(3, f'integration:{peer}', 77, 'synthetic-eos', 'HLLV')
            future = pool.submit(rotate)
            assert started.wait(5)
            assert not done.wait(0.25)
            assert journal.finish(delivery_id, 3, f'integration:{peer}', confirmed=True)
        assert future.result(timeout=5)
        assert done.is_set()


def test_migration_roundtrip_and_protects_delivery_history(database, monkeypatch):
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/f3970a1b2c3d_barricade_scan_journal.py'
    spec = spec_from_file_location('barricade_scan_migration', path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    with engine.begin() as connection:
        connection.execute(text('DROP INDEX ix_player_sessions_server_id_scan'))
        connection.execute(text('DROP INDEX ix_player_sessions_server_open_id_scan'))
    monkeypatch.setattr(journal, 'get_session_maker', lambda: database)
    for index in range(5):
        assert queue(database, f'synthetic-{index}'.encode(), 1 << 3) == 1
    def existing_queue():
        with database() as session:
            return [(row.id, row.server_number, row.command, row.status)
                    for row in session.scalars(select(BlacklistSyncDelivery).order_by(BlacklistSyncDelivery.id))]
    before = existing_queue()
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert inspect(connection).has_table('barricade_scan_delivery')
    assert existing_queue() == before
    with journal.delivery_scope(3, 'integration-a'):
        assert journal.reserve(3, 'integration-a', 1, 'synthetic', 'HLLV') is not None
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            with pytest.raises(RuntimeError, match='prevents duplicate scans'):
                migration.downgrade()
        connection.execute(journal.BarricadeScanDelivery.__table__.delete())
        with Operations.context(MigrationContext.configure(connection)):
            migration.downgrade()
        assert not inspect(connection).has_table('barricade_scan_delivery')
    assert existing_queue() == before


def test_migration_index_lock_timeout_rolls_back_and_allows_retry(database):
    """A busy legacy writer cannot leave a half-installed scan migration."""
    path = Path(__file__).resolve().parents[1] / 'alembic/versions/f3970a1b2c3d_barricade_scan_journal.py'
    spec = spec_from_file_location('barricade_scan_retry_migration', path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    with engine.begin() as conn:
        conn.execute(text('DROP INDEX ix_player_sessions_server_id_scan'))
        conn.execute(text('DROP INDEX ix_player_sessions_server_open_id_scan'))
    blocker = engine.connect()
    transaction = blocker.begin()
    blocker.execute(text('LOCK TABLE player_sessions IN ROW EXCLUSIVE MODE'))
    def upgrade():
        with engine.begin() as connection:
            with Operations.context(MigrationContext.configure(connection)):
                migration.upgrade()
    try:
        with ThreadPoolExecutor(max_workers=1) as pool:
            result = pool.submit(upgrade)
            with pytest.raises(Exception, match='lock timeout'):
                result.result(timeout=5)
        with engine.connect() as conn:
            assert not inspect(conn).has_table('barricade_scan_delivery')
            assert 'ix_player_sessions_server_id_scan' not in {item['name'] for item in inspect(conn).get_indexes('player_sessions')}
        transaction.commit()
        upgrade()
        with engine.connect() as conn:
            assert inspect(conn).has_table('barricade_scan_delivery')
    finally:
        if transaction.is_active:
            transaction.rollback()
        blocker.close()


def test_concurrent_reservation_is_once_and_isolated_by_server_and_integration(database, monkeypatch):
    prepare(database, monkeypatch)
    barrier = Barrier(2)
    def reserve():
        barrier.wait(timeout=5)
        with journal.delivery_scope(3, 'integration-a'):
            return journal.reserve(3, 'integration-a', 77, 'synthetic-eos', 'HLLV')
    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(lambda _: reserve(), range(2)))
    assert sum(value is not None for value in results) == 1
    with journal.delivery_scope(3, 'integration-b'):
        assert journal.reserve(3, 'integration-b', 77, 'synthetic-eos', 'HLLV') is not None
    with journal.delivery_scope(4, 'integration-a'):
        assert journal.reserve(4, 'integration-a', 77, 'synthetic-eos', 'HLLV') is not None
    with journal.delivery_scope(3, 'integration-a'):
        with pytest.raises(ValueError, match='Conflicting'):
            journal.reserve(3, 'integration-a', 77, 'other-player', 'HLLV')
        with pytest.raises(ValueError, match='Conflicting'):
            journal.reserve(3, 'integration-a', 77, 'synthetic-eos', 'HLL')


def test_discovery_catches_late_commits_and_preserves_integration_isolation(database, monkeypatch):
    prepare(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    with database.begin() as session:
        session.add_all([PlayerID(player_id='slow'), PlayerID(player_id='fast')])
    with database() as delayed, database() as fast:
        slow_id = delayed.scalar(select(PlayerID.id).where(PlayerID.player_id == 'slow'))
        fast_id = fast.scalar(select(PlayerID.id).where(PlayerID.player_id == 'fast'))
        first = PlayerSession(player_id_id=slow_id, server_number=3, start=datetime(2026, 1, 1))
        second = PlayerSession(player_id_id=fast_id, server_number=3, start=datetime(2026, 1, 1))
        delayed.add(first)
        delayed.flush()
        fast.add(second)
        fast.commit()
        assert journal.find_unreserved_open_sessions(3, 'integration-a') == [(second.id, 'fast')]
        with journal.delivery_scope(3, 'integration-a'):
            assert journal.reserve(3, 'integration-a', second.id, 'fast', 'HLLV') is not None
        delayed.commit()
        # A page cursor must be discarded at the end of a traversal: the
        # later commit can carry a lower ID than the preceding page.
        assert journal.find_unreserved_open_sessions(3, 'integration-a', after_id=second.id) == []
        assert journal.find_unreserved_open_sessions(3, 'integration-a') == [(first.id, 'slow')]
        assert journal.find_unreserved_open_sessions(3, 'integration-b', limit=1) == [(first.id, 'slow')]
        assert journal.find_unreserved_open_sessions(3, 'integration-b', after_id=first.id, limit=1) == [(second.id, 'fast')]
        assert journal.find_unreserved_open_sessions(4, 'integration-a') == []


def test_discovery_rejects_session_with_absolute_disconnect_even_if_legacy_end_is_missing(database, monkeypatch):
    prepare(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    with database.begin() as session:
        player = PlayerID(player_id='synthetic')
        session.add(player)
        session.flush()
        session.add(PlayerSession(player_id_id=player.id, server_number=3,
                                  start=datetime(2026, 1, 1), end=None, end_event_us=1234567))
    assert journal.find_unreserved_open_sessions(3, 'integration-a') == []


def test_explicit_boundary_excludes_legacy_and_pre_activation_sessions(database, monkeypatch):
    prepare(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    with database.begin() as session:
        for pid, event_us in [('legacy', None), ('old', 99), ('boundary', 100), ('new', 101)]:
            player = PlayerID(player_id=pid)
            session.add(player)
            session.flush()
            session.add(PlayerSession(player_id_id=player.id, server_number=3,
                                      start=datetime(2026, 1, 1), start_event_us=event_us))
    found = journal.find_unreserved_open_sessions(3, 'integration-a', after_event_us=100)
    assert [player for _, player in found] == ['new']
    with pytest.raises(ValueError):
        journal.find_unreserved_open_sessions(3, 'integration-a', after_event_us=True)


def test_unconfirmed_and_crashed_reservations_are_never_replayed(database, monkeypatch):
    prepare(database, monkeypatch)
    with journal.delivery_scope(3, 'integration-a'):
        review_id = journal.reserve(3, 'integration-a', 77, 'synthetic-eos', 'HLLV')
        assert journal.finish(review_id, 3, 'integration-a', confirmed=False)
        assert journal.reserve(3, 'integration-a', 77, 'synthetic-eos', 'HLLV') is None
        assert not journal.finish(review_id, 3, 'integration-a', confirmed=True)
        crash_id = journal.reserve(3, 'integration-a', 78, 'synthetic-eos', 'HLLV')
    with journal.delivery_scope(3, 'integration-a'):
        assert journal.recover_interrupted(3, 'integration-a') == 1
        assert journal.reserve(3, 'integration-a', 78, 'synthetic-eos', 'HLLV') is None
    with database() as session:
        assert session.get(journal.BarricadeScanDelivery, review_id).status == 'review'
        assert session.get(journal.BarricadeScanDelivery, crash_id).status == 'review'
    with journal.delivery_scope(3, 'integration-a'):
        assert not journal.finish(crash_id, 3, 'integration-a', confirmed=True)
        assert not journal.finish(crash_id, 3, 'integration-a', confirmed=False)
    with database() as session:
        assert session.scalar(select(journal.BarricadeScanDelivery.status).where(
            journal.BarricadeScanDelivery.id == crash_id)) == 'review'


def test_process_restart_does_not_replay_confirmed_or_crashed_scan(database, monkeypatch):
    """Separate interpreters exercise a real process exit after reservation."""
    prepare_adapter(database, monkeypatch)
    with database.kw['bind'].connect() as connection:
        schema = connection.scalar(text('SELECT current_schema()'))
    script = r'''
import asyncio, os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import rcon.models
from rcon import barricade_scan_dispatch as adapter, barricade_scan_journal as journal
engine = create_engine(os.environ['TEST_POSTGRES_DSN'],
    connect_args={'options': '-csearch_path=' + os.environ['BARRICADE_TEST_SCHEMA']})
maker = sessionmaker(bind=engine, expire_on_commit=False)
rcon.models.get_engine = lambda: engine
journal.get_session_maker = lambda: maker
adapter.key_is_live = lambda _: True
async def verified(_session_id, _player_id): return True
async def sender(_player_id, _game):
    print('SYNTHETIC_SEND', flush=True)
    if os.environ['BARRICADE_TEST_CRASH'] == '1': os._exit(17)
async def main():
    result = await adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab',
        int(os.environ['BARRICADE_TEST_SESSION']), 'synthetic-eos', 'HLLV', sender,
        credential_id=1, verify_session=verified)
    print('RESULT', result, flush=True)
asyncio.run(main())
'''
    def invoke(session_id, crash=False):
        env = os.environ.copy()
        env.update(BARRICADE_TEST_SCHEMA=schema, BARRICADE_TEST_SESSION=str(session_id),
                   BARRICADE_TEST_CRASH='1' if crash else '0')
        return subprocess.run([sys.executable, '-c', script], env=env, text=True,
                              capture_output=True, timeout=20)
    confirmed = invoke(201)
    assert confirmed.returncode == 0 and 'RESULT done' in confirmed.stdout
    repeated = invoke(201)
    assert repeated.returncode == 0 and 'RESULT already_recorded' in repeated.stdout
    assert 'SYNTHETIC_SEND' not in repeated.stdout
    crashed = invoke(202, crash=True)
    assert crashed.returncode == 17 and 'SYNTHETIC_SEND' in crashed.stdout
    recovered = invoke(202)
    assert recovered.returncode == 0 and 'RESULT already_recorded' in recovered.stdout
    assert 'SYNTHETIC_SEND' not in recovered.stdout
    with database() as session:
        assert session.scalars(select(journal.BarricadeScanDelivery.status).order_by(
            journal.BarricadeScanDelivery.player_session_id)).all() == ['done', 'review']


def test_journal_refuses_work_without_matching_scope(database, monkeypatch):
    prepare(database, monkeypatch)
    with pytest.raises(RuntimeError, match='scope lock'):
        journal.reserve(3, 'integration-a', 1, 'synthetic', 'HLLV')
    with journal.delivery_scope(3, 'integration-a'):
        with pytest.raises(RuntimeError, match='scope lock'):
            journal.recover_interrupted(3, 'integration-b')


def test_review_requires_explicit_decision_before_retry(database, monkeypatch):
    prepare(database, monkeypatch)
    with journal.delivery_scope(3, 'integration-a'):
        delivery = journal.reserve(3, 'integration-a', 99, 'synthetic', 'HLLV')
        assert journal.finish(delivery, 3, 'integration-a', confirmed=False)
    with pytest.raises(ValueError):
        journal.resolve_review(4, 'integration-a', delivery, decision='retry', actor='test', reason='reviewed')
    with pytest.raises(ValueError):
        journal.resolve_review(3, 'integration-a', delivery, decision='retry', actor='test', reason=' ')
    with journal.delivery_scope(3, 'integration-a'):
        assert journal.reserve(3, 'integration-a', 99, 'synthetic', 'HLLV') is None
    journal.resolve_review(3, 'integration-a', delivery, decision='retry', actor='test', reason='remote scan confirmed absent')
    with journal.delivery_scope(3, 'integration-a'):
        assert journal.reserve(3, 'integration-a', 99, 'synthetic', 'HLLV') == delivery
        assert journal.finish(delivery, 3, 'integration-a', confirmed=True)
        assert journal.reserve(3, 'integration-a', 99, 'synthetic', 'HLLV') is None
    with pytest.raises(ValueError, match='not awaiting review'):
        journal.resolve_review(3, 'integration-a', delivery, decision='retry', actor='test', reason='duplicate')
    with database() as session:
        audit = session.scalar(select(journal.BarricadeScanReviewAudit))
        assert (audit.delivery_id, audit.decision, audit.actor) == (delivery, 'retry', 'test')


def test_copied_scope_cannot_outlive_or_move_its_lock(database, monkeypatch):
    prepare(database, monkeypatch)
    with journal.delivery_scope(3, 'integration-a'):
        copied = copy_context()
        with ThreadPoolExecutor(max_workers=1) as pool:
            future = pool.submit(copied.run, journal.recover_interrupted, 3, 'integration-a')
            with pytest.raises(RuntimeError, match='scope lock'):
                future.result(timeout=5)
    with pytest.raises(RuntimeError, match='scope lock'):
        copied.run(journal.recover_interrupted, 3, 'integration-a')


def test_recovery_waits_for_active_sender(database, monkeypatch):
    prepare(database, monkeypatch)
    started, finished = Event(), Event()
    def recover():
        started.set()
        with journal.delivery_scope(3, 'integration-a'):
            count = journal.recover_interrupted(3, 'integration-a')
        finished.set()
        return count
    with ThreadPoolExecutor(max_workers=1) as pool:
        with journal.delivery_scope(3, 'integration-a'):
            delivery_id = journal.reserve(3, 'integration-a', 99, 'synthetic', 'HLLV')
            future = pool.submit(recover)
            assert started.wait(5)
            assert not finished.wait(0.25)
            assert journal.finish(delivery_id, 3, 'integration-a', confirmed=True)
        assert future.result(timeout=5) == 0
        assert finished.is_set()


def test_async_dispatch_confirmed_and_unconfirmed_are_not_repeated(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    async def run():
        seen = []
        async def sender(player_id, game):
            seen.append((player_id, game))
            if player_id == 'failed':
                raise OSError('synthetic response loss')
            return None
        assert await adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab', 1, 'eos', 'HLLV', sender, verify_session=verified, credential_id=1) == 'done'
        assert await adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab', 1, 'eos', 'HLLV', sender, verify_session=verified, credential_id=1) == 'already_recorded'
        assert await adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab', 2, 'failed', 'HLLV', sender, verify_session=verified, credential_id=1) == 'review'
        assert await adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab', 2, 'failed', 'HLLV', sender, verify_session=verified, credential_id=1) == 'already_recorded'
        assert seen == [('eos', 'HLLV'), ('failed', 'HLLV')]
    asyncio.run(run())
    with database() as session:
        assert session.scalars(select(journal.BarricadeScanDelivery.status).order_by(
            journal.BarricadeScanDelivery.player_session_id)).all() == ['done', 'review']


def test_revoked_credential_during_presence_check_does_not_send(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    authorized = {'value': True}
    monkeypatch.setattr(adapter, 'key_is_live', lambda _credential_id: authorized['value'])
    async def run():
        async def verify_then_revoke(_session_id, _player_id):
            authorized['value'] = False
            return True
        async def sender(*_args):
            pytest.fail('a revoked credential must not start a scan')
        return await adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab',
            123, 'synthetic-eos', 'HLLV', sender, credential_id=1, verify_session=verify_then_revoke)
    assert asyncio.run(run()) == 'unauthorized'
    with database() as session:
        assert session.scalars(select(journal.BarricadeScanDelivery)).all() == []


def test_operator_can_surface_interrupted_send_without_connected_peer(database, monkeypatch):
    prepare(database, monkeypatch)
    with journal.delivery_scope(3, 'integration-a'):
        delivery_id = journal.reserve(3, 'integration-a', 123, 'synthetic-eos', 'HLLV')
    listed = journal.list_reviews(3)
    assert listed['total'] == 1 and listed['results'][0]['status'] == 'sending'
    journal.resolve_review(3, 'integration-a', delivery_id, decision='recover',
                           actor='operator', reason='Peer disconnected; result unknown')
    listed = journal.list_reviews(3)
    assert listed['results'][0]['status'] == 'review'
    assert listed['results'][0]['review_cause'] == 'uncertain_delivery'
    with database() as session:
        audit = session.scalar(select(journal.BarricadeScanReviewAudit))
        assert audit.decision == 'recover' and audit.actor == 'operator'


def test_operator_recovery_cannot_override_active_successful_send(database, monkeypatch):
    prepare(database, monkeypatch)
    started = Event()
    def recover(delivery_id):
        started.set()
        journal.resolve_review(3, 'integration-a', delivery_id, decision='recover',
                               actor='operator', reason='Check interrupted send')
    with ThreadPoolExecutor(max_workers=1) as pool:
        with journal.delivery_scope(3, 'integration-a'):
            delivery_id = journal.reserve(3, 'integration-a', 123, 'synthetic-eos', 'HLLV')
            future = pool.submit(recover, delivery_id)
            assert started.wait(3)
            with pytest.raises(TimeoutError):
                future.result(timeout=0.2)
            assert journal.finish(delivery_id, 3, 'integration-a', confirmed=True)
        with pytest.raises(ValueError, match='not awaiting review'):
            future.result(timeout=5)
    with database() as session:
        assert session.get(journal.BarricadeScanDelivery, delivery_id).status == 'done'
        assert session.scalars(select(journal.BarricadeScanReviewAudit)).all() == []


def test_revoked_credential_during_reservation_requires_review_without_send(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    authorized = {'value': True}
    monkeypatch.setattr(adapter, 'key_is_live', lambda _credential_id: authorized['value'])
    reserve = journal.reserve
    def reserve_then_revoke(*args):
        result = reserve(*args)
        authorized['value'] = False
        return result
    monkeypatch.setattr(journal, 'reserve', reserve_then_revoke)
    async def run():
        async def sender(*_args):
            pytest.fail('a revoked credential must not start a scan')
        return await adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab',
            124, 'synthetic-eos', 'HLLV', sender, credential_id=1, verify_session=verified)
    assert asyncio.run(run()) == 'review'
    with database() as session:
        assert session.scalar(select(journal.BarricadeScanDelivery.status)) == 'review'


def test_old_connection_cannot_dispatch_after_key_rotation(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    peer = '01234567-89ab-4def-8012-0123456789ab'
    namespace = f'integration:{peer}'
    assert journal.set_integration_credential(3, peer, expected_credential_id=1,
        new_credential_id=2, actor='test', reason='rotate')
    async def run():
        seen = []
        async def sender(*args):
            seen.append(args)
        assert await adapter.dispatch(3, namespace, 10, 'synthetic', 'HLLV', sender, verify_session=verified, credential_id=1) == 'unauthorized'
        assert seen == []
        assert await adapter.dispatch(3, namespace, 10, 'synthetic', 'HLLV', sender, verify_session=verified, credential_id=2) == 'done'
        assert seen == [('synthetic', 'HLLV')]
    asyncio.run(run())


def test_revoked_key_does_not_create_or_send_a_delivery(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    monkeypatch.setattr(adapter, 'key_is_live', lambda _credential_id: False)
    async def run():
        async def sender(*_args):
            pytest.fail('revoked key must not send')
        assert await adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab',
                                      10, 'synthetic', 'HLLV', sender, verify_session=verified, credential_id=1) == 'unauthorized'
    asyncio.run(run())
    with database() as session:
        assert session.scalars(select(journal.BarricadeScanDelivery)).all() == []


def test_scan_traverses_past_unverified_sessions_without_sending_them(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    with database.begin() as session:
        for player_id in ('stale', 'unknown', 'present'):
            player = PlayerID(player_id=player_id)
            session.add(player)
            session.flush()
            session.add(PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2026, 1, 1),
                                      start_event_us=(int(time.time()) + 2) * 1_000_000))
    establish_synthetic_join_evidence(database)
    async def run():
        seen = []
        async def present(session_id, player_id):
            assert session_id > 0
            return {'stale': False, 'unknown': None, 'present': True}[player_id]
        async def sender(player_id, game):
            seen.append((player_id, game))
        await adapter.scan_once(3, 'integration:01234567-89ab-4def-8012-0123456789ab', 'HLLV', sender, present, credential_id=1, page_size=1)
        await adapter.scan_once(3, 'integration:01234567-89ab-4def-8012-0123456789ab', 'HLLV', sender, present, credential_id=1, page_size=1)
        assert seen == [('present', 'HLLV')]
    asyncio.run(run())


@pytest.mark.parametrize('roster', [None, frozenset()])
def test_scan_recovers_interrupted_send_even_without_roster(database, monkeypatch, roster):
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    with journal.delivery_scope(3, namespace):
        delivery_id = journal.reserve(3, namespace, 999, 'synthetic-eos', 'HLLV')
    async def run():
        async def get_roster():
            return roster
        async def sender(*_args):
            pytest.fail('an interrupted send must not be replayed automatically')
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified,
                                credential_id=1, get_roster=get_roster)
    asyncio.run(run())
    with database() as session:
        row = session.get(journal.BarricadeScanDelivery, delivery_id)
        assert (row.status, row.review_cause) == ('review', 'uncertain_delivery')


def test_scan_does_not_confuse_old_and_current_session_of_same_player(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    with database.begin() as session:
        player = PlayerID(player_id='synthetic-eos')
        session.add(player)
        session.flush()
        event_time = (int(time.time()) + 2) * 1_000_000
        old = PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2026, 1, 1), start_event_us=event_time)
        current = PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2026, 1, 2), start_event_us=event_time)
        session.add_all([old, current])
        session.flush()
        current_id = current.id
    establish_synthetic_join_evidence(database)
    async def run():
        seen = []
        async def present(session_id, player_id):
            return session_id == current_id and player_id == 'synthetic-eos'
        async def sender(player_id, game):
            seen.append((player_id, game))
        await adapter.scan_once(3, 'integration:01234567-89ab-4def-8012-0123456789ab', 'HLLV', sender, present, credential_id=1, page_size=1)
        assert seen == [('synthetic-eos', 'HLLV')]
    asyncio.run(run())
    with database() as session:
        rows = session.scalars(select(journal.BarricadeScanDelivery)).all()
        assert len(rows) == 1 and rows[0].player_session_id == current_id


def test_scan_activation_never_automatically_resends_old_or_ambiguous_sessions(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    peer = '01234567-89ab-4def-8012-0123456789ab'
    namespace = f'integration:{peer}'
    with database() as session:
        boundary = session.get(journal.BarricadeScanIntegration, (3, peer)).registered_at_us
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    floor = (boundary // 1_000_000) * 1_000_000
    with database.begin() as session:
        for pid, event_us in [('legacy', None), ('old', floor - 1_000_000),
                              ('ambiguous', floor), ('new', floor + 1_000_000)]:
            player = PlayerID(player_id=pid)
            session.add(player)
            session.flush()
            session.add(PlayerSession(player_id_id=player.id, server_number=3,
                                      start=datetime(2026, 1, 1), start_event_us=event_us))
    establish_synthetic_join_evidence(database, {'new'})
    async def run():
        sent = []
        async def sender(player_id, game):
            sent.append((player_id, game))
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, is_observed=verified, page_size=1)
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, is_observed=verified, page_size=1)
        assert sent == [('new', 'HLLV')]
        assert await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=2) == 'unauthorized'
    asyncio.run(run())
    with database() as session:
        rows = session.scalars(select(journal.BarricadeScanDelivery)).all()
        assert {row.player_id: (row.status, row.review_cause) for row in rows} == {
            'legacy': ('review', 'missing_live_connect'),
            'old': ('review', 'missing_live_connect'),
            'ambiguous': ('review', 'missing_live_connect'),
            'new': ('done', None),
        }
        ambiguous_id = next(row.id for row in rows if row.player_id == 'ambiguous')
    visible = journal.list_reviews(3)
    assert {row['review_cause'] for row in visible['results']} == {'missing_live_connect'}
    assert journal.list_reviews(4)['total'] == 0
    journal.resolve_review(3, namespace, ambiguous_id, decision='retry', actor='operator', reason='synthetic review')
    async def retry():
        sent = []
        async def sender(player_id, game):
            sent.append((player_id, game))
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, page_size=1)
        assert sent == [('ambiguous', 'HLLV')]
    asyncio.run(retry())
    with database() as session:
        row = session.get(journal.BarricadeScanDelivery, ambiguous_id)
        assert (row.status, row.review_cause) == ('done', None)


def test_activation_reviews_defer_unobserved_and_unavailable_roster(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    with database.begin() as session:
        for pid in ('offline-stale', 'later-observed'):
            player = PlayerID(player_id=pid)
            session.add(player)
            session.flush()
            session.add(PlayerSession(player_id_id=player.id, server_number=3,
                                      start=datetime(2020, 1, 1), start_event_us=None))
    async def run():
        async def sender(*_args):
            pytest.fail('historical session must not be sent')
        async def unavailable(_session_id, _player_id):
            return None
        async def one_online(_session_id, player_id):
            return player_id == 'later-observed'
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, is_observed=unavailable)
        assert journal.list_reviews(3)['total'] == 0
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, is_observed=one_online)
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, is_observed=one_online)
    asyncio.run(run())
    review = journal.list_reviews(3)
    assert review['total'] == 1 and review['results'][0]['player_id'] == 'later-observed'


def test_roster_limits_open_scan_but_preserves_closed_session_review(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    event = (int(time.time()) + 2) * 1_000_000
    with database.begin() as session:
        for pid in ('present', 'not-observed', 'ended'):
            player = PlayerID(player_id=pid)
            session.add(player)
            session.flush()
            session.add(PlayerSession(player_id_id=player.id, server_number=3,
                start=datetime(2026, 1, 1), start_event_us=event,
                end=datetime(2026, 1, 1) if pid == 'ended' else None,
                end_event_us=event + 1_000_000 if pid == 'ended' else None))
    establish_synthetic_join_evidence(database)
    async def run():
        sent = []
        async def sender(player_id, game):
            sent.append((player_id, game))
        async def unavailable():
            return None
        async def available():
            return frozenset({'present'})
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, get_roster=unavailable)
        assert sent == []
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, get_roster=available)
        assert sent == [('present', 'HLLV')]
    asyncio.run(run())
    with database() as session:
        assert {row.player_id: row.status for row in session.scalars(select(journal.BarricadeScanDelivery))} == {
            'present': 'done', 'ended': 'review'}


def test_scan_revisits_delayed_lower_session_id_after_later_commit(database, monkeypatch):
    """A per-pass page cursor must not become a permanent high-water mark."""
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    with database.begin() as session:
        session.add_all([PlayerID(player_id='late'), PlayerID(player_id='early')])
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    seen = []
    async def sender(player_id, game):
        seen.append((player_id, game))
    async def scan():
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, page_size=1)
    event_time = (int(time.time()) + 2) * 1_000_000
    journal.record_roster_snapshot(3, namespace, frozenset())
    journal.record_collector_connects([(3, player_id, 'connect', event_time) for player_id in ('late', 'early')])
    with database() as delayed, database() as fast:
        late_player = delayed.scalar(select(PlayerID.id).where(PlayerID.player_id == 'late'))
        early_player = fast.scalar(select(PlayerID.id).where(PlayerID.player_id == 'early'))
        late = PlayerSession(player_id_id=late_player, server_number=3, start=datetime(2026, 1, 1),
                             start_event_us=event_time)
        early = PlayerSession(player_id_id=early_player, server_number=3, start=datetime(2026, 1, 1),
                              start_event_us=event_time)
        delayed.add(late)
        delayed.flush()
        fast.add(early)
        fast.commit()
        assert late.id < early.id
        asyncio.run(scan())
        assert seen == [('early', 'HLLV')]
        delayed.commit()
        asyncio.run(scan())
        asyncio.run(scan())
        assert seen == [('early', 'HLLV'), ('late', 'HLLV')]
    with database() as session:
        assert session.scalars(select(journal.BarricadeScanDelivery.status).order_by(
            journal.BarricadeScanDelivery.id)).all() == ['done', 'done']


@pytest.mark.parametrize('acknowledged', [True, False])
def test_parallel_scan_passes_share_one_inflight_delivery(database, monkeypatch, acknowledged):
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    with database.begin() as session:
        player = PlayerID(player_id='synthetic-eos')
        session.add(player)
        session.flush()
        session.add(PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2026, 1, 1),
                                  start_event_us=(int(time.time()) + 2) * 1_000_000))
    establish_synthetic_join_evidence(database)
    async def run():
        entered = asyncio.Event()
        release = asyncio.Event()
        sent = []
        async def sender(player_id, game):
            sent.append((player_id, game))
            entered.set()
            await release.wait()
            if not acknowledged:
                raise OSError('synthetic lost reply')
        async def scan():
            await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1)
        first = asyncio.create_task(scan())
        await asyncio.wait_for(entered.wait(), 5)
        second = asyncio.create_task(scan())
        await asyncio.sleep(0.1)
        release.set()
        await asyncio.wait_for(asyncio.gather(first, second), 10)
        await scan()
        assert sent == [('synthetic-eos', 'HLLV')]
    asyncio.run(run())
    with database() as session:
        assert session.scalars(select(journal.BarricadeScanDelivery.status)).all() == [
            'done' if acknowledged else 'review']


def test_disconnected_sessions_are_visible_without_replaying_ended_session(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    event = (int(time.time()) + 2) * 1_000_000
    with database.begin() as session:
        for pid in ('never-sent', 'previously-uncertain'):
            player = PlayerID(player_id=pid)
            session.add(player)
            session.flush()
            session.add(PlayerSession(player_id_id=player.id, server_number=3,
                start=datetime(2026, 1, 1), start_event_us=event,
                end=datetime(2026, 1, 1), end_event_us=event + 1_000_000))
    with database() as session:
        ended = session.scalar(select(PlayerSession.id).join(PlayerID).where(
            PlayerID.player_id == 'previously-uncertain'))
    with journal.delivery_scope(3, namespace):
        delivery = journal.reserve(3, namespace, ended, 'previously-uncertain', 'HLLV')
        assert journal.finish(delivery, 3, namespace, confirmed=False)
    journal.resolve_review(3, namespace, delivery, decision='retry', actor='operator', reason='synthetic review')
    async def run():
        async def sender(*_args):
            pytest.fail('must not scan a disconnected session')
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, page_size=1)
        await adapter.scan_once(3, namespace, 'HLLV', sender, verified, credential_id=1, page_size=1)
    asyncio.run(run())
    with database() as session:
        rows = session.scalars(select(journal.BarricadeScanDelivery)).all()
        assert {r.player_id: (r.status, r.review_cause) for r in rows} == {
            'never-sent': ('review', 'session_ended_before_scan'),
            'previously-uncertain': ('review', 'session_ended_before_scan')}
    with pytest.raises(ValueError, match='session ended'):
        journal.resolve_review(3, namespace, delivery, decision='retry', actor='operator', reason='synthetic')


def test_closed_discovery_combines_recent_and_queued_without_duplicates(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine, checkfirst=True)
    PlayerSession.__table__.create(engine, checkfirst=True)
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    identifiers = {}
    with database.begin() as session:
        for name in ('queued-old', 'queued-recent', 'done-recent', 'review-recent', 'fresh-recent', 'fresh-old'):
            player = PlayerID(player_id=name)
            session.add(player)
            session.flush()
            event = 1_000_000 if name.endswith('old') else 3_000_000
            row = PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2026, 1, 1),
                                start_event_us=event, end=datetime(2026, 1, 1), end_event_us=event)
            session.add(row)
            session.flush()
            identifiers[name] = row.id
    for name in ('queued-old', 'queued-recent', 'done-recent', 'review-recent'):
        with journal.delivery_scope(3, namespace):
            delivery = journal.reserve(3, namespace, identifiers[name], name, 'HLLV')
            assert journal.finish(delivery, 3, namespace, confirmed=name == 'done-recent')
        if name.startswith('queued'):
            journal.resolve_review(3, namespace, delivery, decision='retry', actor='test', reason='synthetic')
    rows = journal.find_unreserved_recent_closed_sessions(3, namespace, 2_000_100)
    assert rows == [(identifiers[name], name) for name in ('queued-old', 'queued-recent', 'fresh-recent', 'fresh-old')]
    first = journal.find_unreserved_recent_closed_sessions(3, namespace, 2_000_100, limit=1)
    rest = journal.find_unreserved_recent_closed_sessions(3, namespace, 2_000_100, after_id=first[0][0])
    assert first + rest == rows


def test_async_dispatch_cancellation_before_lock_does_not_send(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    async def run():
        called = []
        async def sender(*args):
            called.append(args)
        with journal.delivery_scope(3, 'integration:01234567-89ab-4def-8012-0123456789ab'):
            task = asyncio.create_task(adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab', 3, 'eos', 'HLLV', sender, verify_session=verified, credential_id=1))
            await asyncio.sleep(0.2)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        await asyncio.sleep(0.4)
        assert called == []
    asyncio.run(run())
    with database() as session:
        assert session.scalars(select(journal.BarricadeScanDelivery)).all() == []


def test_async_dispatch_cancellation_during_send_keeps_lock_until_result(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    async def run():
        started, release = asyncio.Event(), asyncio.Event()
        async def sender(*args):
            started.set()
            await release.wait()
        first = asyncio.create_task(adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab', 4, 'eos', 'HLLV', sender, verify_session=verified, credential_id=1))
        await asyncio.wait_for(started.wait(), 5)
        first.cancel()
        with pytest.raises(asyncio.CancelledError):
            await first
        second = asyncio.create_task(adapter.dispatch(3, 'integration:01234567-89ab-4def-8012-0123456789ab', 4, 'eos', 'HLLV', sender, verify_session=verified, credential_id=1))
        await asyncio.sleep(0.25)
        assert not second.done()
        release.set()
        assert await asyncio.wait_for(second, 5) == 'already_recorded'
    asyncio.run(run())
    with database() as session:
        assert session.scalar(select(journal.BarricadeScanDelivery.status)) == 'done'


def test_dispatch_rechecks_session_after_waiting_for_lock(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    async def run():
        online = True
        seen = []
        async def presence(_session_id, _player_id):
            return online
        async def sender(*args):
            seen.append(args)
        with journal.delivery_scope(3, namespace):
            task = asyncio.create_task(adapter.dispatch(3, namespace, 5, 'eos', 'HLLV', sender,
                                                        credential_id=1, verify_session=presence))
            await asyncio.sleep(0.2)
            online = False
        assert await asyncio.wait_for(task, 5) == 'deferred'
        assert seen == []
    asyncio.run(run())
    with database() as session:
        assert session.scalars(select(journal.BarricadeScanDelivery)).all() == []
