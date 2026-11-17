"""Synthetic concurrent scan reservations against disposable PostgreSQL."""
from concurrent.futures import ThreadPoolExecutor
from threading import Barrier, Event
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from contextvars import copy_context
import asyncio
from datetime import datetime
import time

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import inspect, select

from rcon import barricade_scan_journal as journal
from rcon import barricade_scan_dispatch as adapter
from rcon.barricade_scan_identity import integration_namespace
from rcon.models import PlayerID, PlayerSession
from tests.test_blacklist_sync_journal_postgres import database


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
    monkeypatch.setattr(journal, 'get_session_maker', lambda: database)
    with engine.begin() as connection:
        with Operations.context(MigrationContext.configure(connection)):
            migration.upgrade()
        assert inspect(connection).has_table('barricade_scan_delivery')
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
    PlayerID.__table__.create(engine)
    PlayerSession.__table__.create(engine)
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
    PlayerID.__table__.create(engine)
    PlayerSession.__table__.create(engine)
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
    PlayerID.__table__.create(engine)
    PlayerSession.__table__.create(engine)
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
    PlayerID.__table__.create(engine)
    PlayerSession.__table__.create(engine)
    with database.begin() as session:
        for player_id in ('stale', 'unknown', 'present'):
            player = PlayerID(player_id=player_id)
            session.add(player)
            session.flush()
            session.add(PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2026, 1, 1)))
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


def test_scan_does_not_confuse_old_and_current_session_of_same_player(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    PlayerID.__table__.create(engine)
    PlayerSession.__table__.create(engine)
    with database.begin() as session:
        player = PlayerID(player_id='synthetic-eos')
        session.add(player)
        session.flush()
        old = PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2026, 1, 1))
        current = PlayerSession(player_id_id=player.id, server_number=3, start=datetime(2026, 1, 2))
        session.add_all([old, current])
        session.flush()
        current_id = current.id
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
