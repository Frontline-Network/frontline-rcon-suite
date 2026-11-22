"""Concurrent VIP reconciliation tests against a disposable PostgreSQL schema."""
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager, nullcontext
from datetime import datetime, timedelta, timezone
from threading import Event
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from rcon import models, utils
from rcon.automods import action_guard
from rcon.expiring_vips import service
from rcon.types import GameEnum
from rcon.vip_rewards.locking import vip_lock


@pytest.fixture
def database(monkeypatch):
    dsn = os.getenv('TEST_POSTGRES_DSN') or os.getenv('VIP_REWARDS_TEST_DB_URL')
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


@pytest.fixture
def vip_admin(database, monkeypatch):
    from rcon import rcon as rcon_module
    from rcon.rcon import Rcon, ServerCtl

    monkeypatch.setenv("SERVER_NUMBER", "3")
    monkeypatch.setattr(rcon_module, "enter_session", service.enter_session)
    members = {"fictional-player": "Example"}
    read = Mock(side_effect=lambda: [{"player_id": k, "name": v} for k, v in members.items()])

    def add(_api, player_id, description):
        members[player_id] = description
        return True

    def remove(player_id):
        return members.pop(player_id, None) is not None

    removal = Mock(side_effect=remove)
    monkeypatch.setattr(ServerCtl, "get_vip_ids", lambda self: read())
    monkeypatch.setattr(ServerCtl, "add_vip", add)
    monkeypatch.setattr(ServerCtl, "remove_vip", lambda self, player_id: removal(player_id))
    api = object.__new__(Rcon)
    api.config = SimpleNamespace(game=GameEnum.HLL_VIETNAM)
    snapshot = Mock(side_effect=api.get_live_vip_ids)
    monkeypatch.setattr(Rcon, "get_vip_ids", snapshot)
    return api, members, read, removal, snapshot


@pytest.mark.parametrize("original", ["missing", "legacy"])
@pytest.mark.parametrize("action", ["limit", "revoke", "unchanged"])
def test_backfill_respects_current_entitlement(database, vip_admin, original, action):
    api, members, _, _, snapshot = vip_admin
    pid = "fictional-player"
    limited = datetime.now(timezone.utc).replace(microsecond=0) + timedelta(days=7)
    with database.begin() as db:
        row = db.scalar(select(models.PlayerVIP))
        if original == "legacy":
            row.expiration = limited + timedelta(days=365 * 150)
        else:
            db.delete(row)

    def scan_then_change():
        rows = api.get_live_vip_ids()
        snapshot.side_effect = api.get_live_vip_ids
        if action == "limit":
            assert api.add_vip(pid, "Example", limited.isoformat()) is True
        elif action == "revoke":
            assert api.remove_vip(pid) is True
        return rows

    snapshot.side_effect = scan_then_change
    service.remove_expired_vips(api)
    assert service.restore_missing_vips(api) == 0
    with database() as db:
        row = db.scalar(select(models.PlayerVIP))
        if action == "revoke":
            assert row is None and pid not in members
        else:
            expected = limited if action == "limit" else utils.INDEFINITE_VIP_DATE
            assert row.expiration == expected and pid in members


@pytest.mark.parametrize("state", ["listed", "missing", "restored", "rejected", "unknown"])
def test_bulk_revoke_includes_stored_entitlements(database, vip_admin, state):
    from rcon.commands import HLLCommandFailedError

    api, members, read, removal, _ = vip_admin
    pid = "fictional-player"
    with database.begin() as db:
        primary = db.scalar(select(models.PlayerVIP))
        db.add(models.PlayerVIP(player_id_id=primary.player_id_id, server_number=4, expiration=primary.expiration))
    if state == "missing":
        members.clear()
    elif state == "restored":
        # Game membership reappears between the first scan and the player lock.
        read.side_effect = [[], [{"player_id": pid, "name": "Example"}], []]
    elif state == "rejected":
        removal.side_effect = None
        removal.return_value = False
    elif state == "unknown":
        read.side_effect = [[], TimeoutError("game unreachable")]

    if state in ("rejected", "unknown"):
        error = TimeoutError if state == "unknown" else HLLCommandFailedError
        with pytest.raises(error):
            api.remove_all_vips()
    else:
        assert api.remove_all_vips() is True
        assert pid not in members
        read.side_effect = lambda: []
        assert service.restore_missing_vips(api) == 0

    with database() as db:
        servers = set(db.scalars(select(models.PlayerVIP.server_number)))
    assert servers == ({3, 4} if state in ("rejected", "unknown") else {4})


def test_bulk_revoke_reports_partial_failure_and_keeps_rejected_right(database, vip_admin):
    from rcon.commands import HLLCommandFailedError

    api, members, _, removal, _ = vip_admin
    blocked = "fictional-player"
    accepted = "second-player"
    with database.begin() as db:
        db.add(models.PlayerID(player_id=accepted))
    assert api.add_vip(accepted, "Second", utils.INDEFINITE_VIP_DATE.isoformat())
    removal.side_effect = lambda player_id: player_id != blocked and members.pop(player_id, None) is not None
    with pytest.raises(HLLCommandFailedError, match="1 player"):
        api.remove_all_vips()
    assert set(members) == {blocked}
    with database() as db:
        assert db.scalar(select(models.PlayerVIP)).player.player_id == blocked
        assert db.query(models.PlayerVIP).count() == 1


@pytest.mark.parametrize("listed", [False, True])
def test_vietnam_single_revoke_survives_restore_and_preserves_other_server(database, vip_admin, listed):
    api, members, _, removal, _ = vip_admin
    pid = "fictional-player"
    with database.begin() as db:
        current = db.scalar(select(models.PlayerVIP))
        db.add(models.PlayerVIP(player_id_id=current.player_id_id, server_number=4,
                                expiration=current.expiration))
    if not listed:
        members.clear()
    assert api.remove_vip(pid) is True
    assert removal.call_count == int(listed)
    assert service.restore_missing_vips(api) == 0
    assert pid not in members
    with database() as db:
        assert list(db.scalars(select(models.PlayerVIP.server_number))) == [4]


@pytest.mark.parametrize("failure", ["read_timeout", "rejected", "lost_reply"])
def test_vietnam_single_revoke_keeps_record_until_confirmed(database, vip_admin, failure):
    api, members, read, removal, _ = vip_admin
    pid = "fictional-player"
    if failure == "rejected":
        removal.side_effect = None
        removal.return_value = False
        assert api.remove_vip(pid) is False
        assert pid in members
    else:
        if failure == "read_timeout":
            read.side_effect = TimeoutError("unconfirmed list")
        else:
            def lose_reply(player_id):
                members.pop(player_id)
                raise TimeoutError("unconfirmed removal")
            removal.side_effect = lose_reply
        with pytest.raises(TimeoutError):
            api.remove_vip(pid)
    assert removal.call_count == int(failure != "read_timeout")
    with database() as db:
        assert db.scalar(select(models.PlayerVIP)).expiration > datetime.now(timezone.utc)
    if failure == "lost_reply":
        assert api.remove_vip(pid) is True
        removal.assert_called_once()
        assert service.restore_missing_vips(api) == 0


def test_vietnam_single_revoke_waits_for_concurrent_restore(database, vip_admin, monkeypatch):
    from rcon.rcon import ServerCtl

    api, members, _, removal, _ = vip_admin
    pid = "000200000000000000000000000000ab"
    with database.begin() as db:
        db.scalar(select(models.PlayerID)).player_id = pid
    members.clear()
    restoring, release, revoking = Event(), Event(), Event()

    def add(_api, player_id, description):
        restoring.set()
        assert release.wait(10)
        members[player_id] = description
        return True

    def revoke():
        revoking.set()
        return api.remove_vip(pid.upper())

    monkeypatch.setattr(ServerCtl, "add_vip", add)
    with ThreadPoolExecutor(max_workers=2) as pool:
        restore = pool.submit(service.restore_missing_vips, api)
        try:
            assert restoring.wait(5)
            removal_result = pool.submit(revoke)
            assert revoking.wait(5)
            with pytest.raises(TimeoutError):
                removal_result.result(timeout=0.25)
        finally:
            release.set()
        assert restore.result(timeout=10) == 1
        assert removal_result.result(timeout=10) is True
    removal.assert_called_once_with(pid)
    assert service.restore_missing_vips(api) == 0
    assert pid not in members
    with database() as db:
        assert db.scalar(select(models.PlayerVIP)) is None
