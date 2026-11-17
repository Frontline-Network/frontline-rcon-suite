"""Concurrent VIP reconciliation tests against a disposable PostgreSQL schema."""
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from threading import Event
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from rcon import models, utils
from rcon.automods import action_guard
from rcon.expiring_vips import service
from rcon.vip_rewards.locking import vip_lock


@pytest.fixture
def database(monkeypatch):
    dsn = os.getenv('TEST_POSTGRES_DSN')
    if not dsn:
        pytest.skip('requires a disposable PostgreSQL database')
    root = create_engine(dsn)
    schema = 'vip_restore_' + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={'options': f'-csearch_path={schema}'})
    for model in (models.PlayerID, models.PlayerName, models.PlayerVIP):
        model.__table__.create(engine)
    action_guard.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)

    @contextmanager
    def enter_session():
        with maker() as session:
            with session.begin():
                yield session

    monkeypatch.setattr(models, 'get_engine', lambda: engine)
    monkeypatch.setattr(action_guard, 'get_session_maker', lambda: maker)
    monkeypatch.setattr(utils, 'get_server_number', lambda: '3')
    monkeypatch.setattr(service, 'get_server_number', lambda: '3')
    monkeypatch.setattr(service, 'enter_session', enter_session)
    with maker.begin() as session:
        player = models.PlayerID(player_id='fictional-player')
        session.add(player)
        session.flush()
        session.add(models.PlayerVIP(player=player, server_number=3,
                                     expiration=datetime.now(timezone.utc) + timedelta(days=1)))
    try:
        yield maker
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def fake_api():
    api = Mock()
    api.get_vip_ids.return_value = []
    api.without_retries.side_effect = nullcontext
    api.add_vip.return_value = True
    return api


def test_revoke_after_scan_prevents_restore(database, monkeypatch):
    original = service.enter_session
    scans = 0

    @contextmanager
    def revoke_after_first_scan():
        nonlocal scans
        with original() as session:
            yield session
        scans += 1
        if scans == 1:
            with vip_lock('fictional-player'):
                with database.begin() as session:
                    session.delete(session.scalar(select(models.PlayerVIP)))

    monkeypatch.setattr(service, 'enter_session', revoke_after_first_scan)
    api = fake_api()
    assert service.restore_missing_vips(api) == 0
    api.add_vip.assert_not_called()


def test_revoke_waits_for_restore_then_wins(database):
    api = fake_api()
    entered, release, revoke_started = Event(), Event(), Event()
    live = set()

    def add_vip(**kwargs):
        entered.set()
        assert release.wait(10)
        live.add(kwargs['player_id'])
        return True

    api.add_vip.side_effect = add_vip

    def revoke():
        revoke_started.set()
        with vip_lock('fictional-player'):
            with database.begin() as session:
                session.delete(session.scalar(select(models.PlayerVIP)))
            live.discard('fictional-player')

    with ThreadPoolExecutor(max_workers=2) as executor:
        restore = executor.submit(service.restore_missing_vips, api)
        assert entered.wait(10)
        removal = executor.submit(revoke)
        assert revoke_started.wait(10)
        try:
            assert not removal.done()
        finally:
            release.set()
        assert restore.result(timeout=15) == 1
        removal.result(timeout=15)
    assert live == set()
    with database() as session:
        assert session.scalar(select(models.PlayerVIP)) is None


@pytest.mark.parametrize('result', [None, 'timeout'])
def test_uncertain_restore_survives_restart_and_is_not_replayed(database, result):
    api = fake_api()
    if result == 'timeout':
        api.add_vip.side_effect = TimeoutError('simulated lost response')
    else:
        api.add_vip.return_value = None
    assert service.restore_missing_vips(api) == 0
    assert service.restore_missing_vips(api) == 0
    api.add_vip.assert_called_once()
    assert action_guard.pending_players(3, 'VietnamVipRestore') == {'fictional-player'}


def test_explicit_rejection_releases_reservation_for_later_retry(database):
    api = fake_api()
    api.add_vip.side_effect = [False, True]
    assert service.restore_missing_vips(api) == 0
    assert service.restore_missing_vips(api) == 1
    assert api.add_vip.call_count == 2
    assert action_guard.pending_players(3, 'VietnamVipRestore') == set()


def test_transition_hold_blocks_restore_until_audited_release(database):
    token = action_guard.reserve(3, '*', ['VietnamVipRestore'], 'vip', legacy_global=True)
    api = fake_api()
    assert service.restore_missing_vips(api) == 0
    api.add_vip.assert_not_called()
    assert action_guard.review(3, '*', token, 'operator', 'Prior operation checked') == 1
    assert service.restore_missing_vips(api) == 1
