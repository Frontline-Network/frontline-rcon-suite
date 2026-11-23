"""Exercise durable delivery with a disposable PostgreSQL schema and fake RCON."""
import os
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
from time import monotonic, sleep
from unittest import mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

import rcon.models
from rcon import blacklist_sync_journal as journal
from rcon import blacklist
from rcon.automods import action_guard
from rcon.models import Blacklist, BlacklistRecord, PlayerID, PlayerName
from rcon.types import BlacklistSyncMethod


@pytest.fixture
def database(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "blacklist_sync_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"}, pool_size=10)
    journal.BlacklistSyncDelivery.__table__.create(engine)
    action_guard.metadata.create_all(engine)
    action_guard.event_guard.metadata.create_all(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(journal, "get_session_maker", lambda: maker)
    monkeypatch.setattr(action_guard, "get_session_maker", lambda: maker)
    monkeypatch.setattr(rcon.models, "get_engine", lambda: engine)
    try:
        yield maker
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def queue(maker, command, mask):
    with maker() as session, session.begin():
        return journal.enqueue(session, command, mask)


def test_enqueue_rolls_back_with_source_transaction(database):
    with pytest.raises(ValueError):
        with database() as session, session.begin():
            journal.enqueue(session, b"event", 1)
            raise ValueError("abort source mutation")
    assert journal.process_one(1, lambda _: pytest.fail("must not deliver")) == "empty"


def test_delivery_is_per_target_ordered_and_server_32_is_supported(database):
    assert queue(database, b"first", (1 << 31) | 1) == 2
    assert queue(database, b"second", 1) == 1
    seen = []
    assert journal.process_one(1, seen.append) == "done"
    assert journal.process_one(1, seen.append) == "done"
    assert journal.process_one(32, seen.append) == "done"
    assert journal.process_one(1, seen.append) == "empty"
    assert seen == [b"first", b"second", b"first"]


def test_failed_target_does_not_block_another_target(database):
    queue(database, b"first", 3)
    assert journal.process_one(1, lambda _: False) == "review"
    seen = []
    assert journal.process_one(2, seen.append) == "done"
    assert seen == [b"first"]
    assert journal.process_one(1, lambda _: pytest.fail("must not retry")) == "review"


@pytest.mark.parametrize("readiness", [False, None, OSError("unavailable")])
def test_offline_target_defers_queued_delivery_without_losing_or_attempting_it(database, readiness):
    queue(database, b"first", 1)
    dispatch = mock.Mock()

    def probe():
        if isinstance(readiness, Exception):
            raise readiness
        return readiness

    assert journal.process_one(1, dispatch, is_ready=probe) == "deferred"
    dispatch.assert_not_called()
    with database() as session:
        assert session.scalar(select(journal.BlacklistSyncDelivery.status)) == "queued"
    assert journal.process_one(1, dispatch, is_ready=lambda: True) == "done"
    dispatch.assert_called_once_with(b"first")


def test_offline_probe_does_not_hide_an_uncertain_inflight_action(database):
    queue(database, b"first", 1)
    with database() as session, session.begin():
        row = session.scalar(select(journal.BlacklistSyncDelivery))
        row.status = "sending"
    assert journal.process_one(1, lambda _: pytest.fail("must not retry"),
                               is_ready=lambda: False) == "review"


def test_offline_server_does_not_block_an_online_server(database):
    queue(database, b"first", (1 << 2) | (1 << 3))
    offline = mock.Mock()
    online = mock.Mock()
    assert journal.process_one(4, offline, is_ready=lambda: False) == "deferred"
    assert journal.process_one(3, online, is_ready=lambda: True) == "done"
    offline.assert_not_called()
    online.assert_called_once_with(b"first")
    assert journal.process_one(4, offline, is_ready=lambda: True) == "done"
    offline.assert_called_once_with(b"first")


def test_slow_offline_probe_does_not_block_new_blacklist_mutation(database):
    queue(database, b"existing", (1 << 2) | (1 << 3))
    entered, release = Event(), Event()

    def slow_offline_probe():
        entered.set()
        assert release.wait(10)
        return False

    with ThreadPoolExecutor(max_workers=2) as executor:
        worker = executor.submit(journal.process_one, 4, mock.Mock(), is_ready=slow_offline_probe)
        assert entered.wait(10)
        writer = executor.submit(queue, database, b"new", (1 << 2) | (1 << 3))
        try:
            assert writer.result(timeout=2) == 2
        finally:
            release.set()
        assert worker.result(timeout=10) == "deferred"
    with database() as session:
        assert len(session.scalars(select(journal.BlacklistSyncDelivery)).all()) == 4


def test_stale_successful_probe_does_not_dispatch(database, monkeypatch):
    queue(database, b"existing", 1)
    times = iter((10.0, 16.0))
    monkeypatch.setattr(journal, 'monotonic', lambda: next(times))
    dispatch = mock.Mock()
    assert journal.process_one(1, dispatch, is_ready=lambda: True) == 'deferred'
    dispatch.assert_not_called()
    with database() as session:
        assert session.scalar(select(journal.BlacklistSyncDelivery.status)) == 'queued'


def test_slow_preparation_does_not_block_new_writes(database):
    queue(database, b'first', 1)
    started, release = Event(), Event()
    def prepare(command):
        assert command == b'first'
        started.set()
        assert release.wait(10)
        return 'synthetic snapshot'
    seen = mock.Mock()
    with ThreadPoolExecutor(max_workers=2) as pool:
        worker = pool.submit(journal.process_one, 1, seen, prepare=prepare)
        assert started.wait(10)
        writer = pool.submit(queue, database, b'second', 1)
        try:
            assert writer.result(timeout=2) == 1
        finally:
            release.set()
        assert worker.result(timeout=10) == 'done'
    seen.assert_called_once_with(b'first', 'synthetic snapshot')


def test_preparation_failure_leaves_delivery_queued(database):
    queue(database, b'first', 1)
    dispatch = mock.Mock()
    def unavailable(_command):
        raise TimeoutError('synthetic read failure')
    assert journal.process_one(1, dispatch, prepare=unavailable) == 'deferred'
    dispatch.assert_not_called()
    with database() as session:
        assert session.scalar(select(journal.BlacklistSyncDelivery.status)) == 'queued'


def test_snapshot_for_advanced_queue_is_not_dispatched(database):
    queue(database, b'first', 1)
    queue(database, b'second', 1)
    def advance(_command):
        with database() as session, session.begin():
            row = session.scalar(select(journal.BlacklistSyncDelivery).order_by(journal.BlacklistSyncDelivery.id))
            row.status = 'done'
        return 'snapshot for first'
    dispatch = mock.Mock()
    assert journal.process_one(1, dispatch, prepare=advance) == 'deferred'
    dispatch.assert_not_called()


def test_uncertain_inflight_delivery_is_reviewed_without_preparation(database):
    queue(database, b'first', 1)
    with database() as session, session.begin():
        session.scalar(select(journal.BlacklistSyncDelivery)).status = 'sending'
    prepare, dispatch = mock.Mock(), mock.Mock()
    assert journal.process_one(1, dispatch, prepare=prepare) == 'review'
    prepare.assert_not_called()
    dispatch.assert_not_called()


def test_empty_queue_does_not_probe_or_dispatch(database):
    probe = mock.Mock()
    dispatch = mock.Mock()
    assert journal.process_one(1, dispatch, is_ready=probe) == "empty"
    probe.assert_not_called()
    dispatch.assert_not_called()


@pytest.mark.parametrize("failure", [False, TimeoutError("response lost")])
def test_unconfirmed_action_requires_review_and_blocks_later_work(database, failure):
    queue(database, b"first", 1)
    queue(database, b"second", 1)
    calls = []
    def handler(command):
        calls.append(command)
        if isinstance(failure, Exception):
            raise failure
        return failure
    assert journal.process_one(1, handler) == "review"
    assert journal.process_one(1, handler) == "review"
    assert calls == [b"first"]


def test_unconfirmed_unban_is_reviewed_without_replay(database, monkeypatch):
    from contextlib import nullcontext

    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 1)
    monkeypatch.setattr(blacklist, 'lock', lambda _key: nullcontext())
    server = mock.Mock()
    server.get_temp_bans.return_value = [{'player_id': 'synthetic', 'ban_time': '2025-01-01T00:00:00Z'}]
    server.get_perma_bans.return_value = [{'player_id': 'synthetic', 'ban_time': '2025-01-01T00:00:00Z'}]
    server.remove_temp_ban.return_value = None
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = server
    queue(database, b'first', 1)
    dispatch = lambda _command: receiver.handle_expire_all(blacklist.BlacklistExpireAllCommand(player_id='synthetic', requested_at=datetime.now(timezone.utc)))
    assert journal.process_one(1, dispatch) == 'review'
    assert journal.process_one(1, dispatch) == 'review'
    server.remove_temp_ban.assert_called_once_with('synthetic')
    server.get_perma_bans.assert_not_called()
    server.remove_perma_ban.assert_not_called()


@pytest.mark.parametrize("temporary", [True, False], ids=["temporary", "permanent"])
@pytest.mark.parametrize("scenario,expected", [
    ("older", "done"), ("newer", "done"), ("absent", "done"),
    ("same_second", "review"), ("naive", "review"), ("legacy", "review"),
    ("read_failure", "review"),
])
def test_expiry_uses_fresh_bans_and_original_request_time(
        database, existing_blacklist, monkeypatch, temporary, scenario, expected):
    from functools import wraps
    from types import SimpleNamespace
    from rcon.rcon import Rcon
    from rcon.types import GameEnum

    player = "abcdef0123456789abcdef0123456789"
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 3)
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    ctl = receiver.rcon = Rcon.__new__(Rcon)
    ctl.game_profile = SimpleNamespace(game=GameEnum.HLL_VIETNAM)
    if scenario == "legacy":
        command = blacklist.BlacklistCommand(blacklist.BlacklistCommandType.EXPIRE_ALL, 4, {"player_id": player})
        queue(database, command.encode(), 4)
        requested = datetime.now(timezone.utc)
    else:
        before = datetime.now(timezone.utc)
        blacklist.expire_all_player_blacklists(player)
        with database() as session:
            delivery = session.scalar(select(journal.BlacklistSyncDelivery).where(
                journal.BlacklistSyncDelivery.server_number == 3))
            requested = datetime.fromisoformat(blacklist.BlacklistCommand.decode(delivery.command).payload["requested_at"])
            assert before <= requested <= delivery.created_at
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: False) == "deferred"

    stamp = {
        "newer": (requested + timedelta(seconds=1)).isoformat(),
        "same_second": requested.isoformat(timespec="seconds"),
        "naive": requested.replace(tzinfo=None).isoformat(),
    }.get(scenario, (requested - timedelta(days=1)).isoformat())
    ban = {"userId": player.upper(), "userName": "fixture", "timeOfBanning": stamp,
           "durationHours": 1, "banReason": "test", "adminName": "fixture"}
    kind = "Temporary" if temporary else "Permanent"
    def exchange(command, version):
        if command == f"Get{kind}Bans" and scenario == "read_failure":
            raise OSError("test read failure")
        rows = [ban] if command == f"Get{kind}Bans" and scenario != "absent" else []
        return SimpleNamespace(content_dict={"banList": rows})

    ctl.exchange = mock.Mock(side_effect=exchange)
    ctl.exchange_success = mock.Mock(return_value=True)
    # Emulate a populated GUI cache while preserving the real uncached reader.
    for name in ("get_temp_bans", "get_perma_bans"):
        @wraps(getattr(Rcon, name).__wrapped__)
        def cached(self):
            return [{"player_id": player, "ban_time": stamp}] if scenario == "absent" else []
        cached.cache_clear = mock.Mock()
        monkeypatch.setattr(Rcon, name, cached)

    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True) == expected
    assert ctl.exchange.called
    if scenario == "older":
        ctl.exchange_success.assert_called_once_with(f"Remove{kind}Ban", 2, {"PlayerId": player.upper()})
    else:
        ctl.exchange_success.assert_not_called()
    with database() as session:
        row = session.scalar(select(journal.BlacklistSyncDelivery).where(journal.BlacklistSyncDelivery.server_number == 3))
        assert row.status == expected
        if scenario == "newer":
            assert row.reason == "Newer game ban preserved"
    assert journal.process_one(3, receiver.dispatch) == ("review" if expected == "review" else "empty")


def test_interrupted_action_is_not_replayed(database):
    queue(database, b"first", 1)
    def interrupted(_command):
        raise KeyboardInterrupt()
    with pytest.raises(KeyboardInterrupt):
        journal.process_one(1, interrupted)
    assert journal.process_one(1, lambda _: pytest.fail("must not replay")) == "review"


def test_review_is_server_scoped_and_releases_following_delivery(database):
    queue(database, b"first", 1)
    queue(database, b"second", 1)
    assert journal.process_one(1, lambda _: False) == "review"
    with database() as session:
        delivery_id = session.scalar(select(journal.BlacklistSyncDelivery.id).order_by(journal.BlacklistSyncDelivery.id))
    assert not journal.acknowledge_review(2, delivery_id, "operator")
    with pytest.raises(ValueError):
        journal.acknowledge_review(1, delivery_id, "  ")
    assert journal.acknowledge_review(1, delivery_id, "operator")
    assert not journal.acknowledge_review(1, delivery_id, "operator")
    observed = []
    assert journal.process_one(1, observed.append) == "done"
    assert observed == [b"second"]
    with database() as session:
        row = session.get(journal.BlacklistSyncDelivery, delivery_id)
        assert row.status == "reviewed"
        assert "reviewed by operator" in row.reason


def test_review_list_is_server_scoped_and_decodes_event(database):
    cmd = blacklist.BlacklistCommand(
        command=blacklist.BlacklistCommandType.EXPIRE_ALL,
        server_mask=3,
        payload={"player_id": "synthetic-player"},
    )
    queue(database, cmd.encode(), 3)
    assert journal.process_one(1, lambda _: False) == "review"
    first = journal.list_reviews(1)
    assert first["total"] == 1
    assert first["results"][0]["command"] == "EXPIRE_ALL"
    assert first["results"][0]["payload"]["player_id"] == "synthetic-player"
    assert journal.list_reviews(2)["total"] == 0
    with pytest.raises(ValueError):
        journal.list_reviews(1, limit=101)


@pytest.mark.parametrize('error,kind', [
    (blacklist.HLLVSteamBanOwnershipUnverified('synthetic'), 'hllv_ownership'),
    (blacklist.HLLVSteamIdentityUnverified('synthetic'), 'hllv_identity'),
    (blacklist.BlacklistBanOwnershipUnverified('synthetic'), 'hllv_ownership'),
    (TimeoutError('synthetic'), None),
])
def test_review_kind_distinguishes_no_action_from_uncertain_action(database, error, kind):
    queue(database, b'first', 1)
    def fail(_command):
        raise error
    assert journal.process_one(1, fail) == 'review'
    assert journal.list_reviews(1)['results'][0]['review_kind'] == kind


def test_concurrent_workers_do_not_execute_one_command_twice(database):
    queue(database, b"first", 1)
    entered, release = Event(), Event()
    calls = []
    def handler(command):
        calls.append(command)
        entered.set()
        assert release.wait(10)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(journal.process_one, 1, handler)
        assert entered.wait(10)
        second = executor.submit(journal.process_one, 1, handler)
        try:
            assert not second.done()
        finally:
            release.set()
        assert {first.result(timeout=15), second.result(timeout=15)} == {"done", "empty"}
    assert calls == [b"first"]


def test_producer_cannot_commit_target_change_during_delivery(database):
    queue(database, b"first", 1)
    entered, release = Event(), Event()
    def handler(_command):
        entered.set()
        assert release.wait(10)
    with ThreadPoolExecutor(max_workers=2) as executor:
        worker = executor.submit(journal.process_one, 1, handler)
        assert entered.wait(10)
        producer = executor.submit(queue, database, b"second", 1)
        try:
            assert not producer.done()
        finally:
            release.set()
        assert worker.result(timeout=15) == "done"
        assert producer.result(timeout=15) == 1


def test_commit_order_is_preserved_across_concurrent_producers(database):
    staged, release = Event(), Event()
    def first():
        with database() as session, session.begin():
            journal.enqueue(session, b"first", 1)
            staged.set()
            assert release.wait(10)
    def second():
        assert staged.wait(10)
        queue(database, b"second", 1)
    with ThreadPoolExecutor(max_workers=2) as executor:
        a, b = executor.submit(first), executor.submit(second)
        assert staged.wait(10)
        assert not b.done()
        release.set()
        a.result(timeout=15)
        b.result(timeout=15)
    with database() as session:
        rows = session.scalars(select(journal.BlacklistSyncDelivery).order_by(journal.BlacklistSyncDelivery.id)).all()
        assert [row.command for row in rows] == [b"first", b"second"]


def test_writer_waiting_for_dispatch_leaves_other_targets_free(database):
    entered, release = Event(), Event()
    writer_pid = Future()
    queue(database, b"initial", 4)

    def dispatch(_):
        entered.set()
        assert release.wait(15)

    def enqueue_for_servers_one_and_three():
        with database.begin() as session:
            writer_pid.set_result(session.scalar(text("SELECT pg_backend_pid()")))
            return journal.enqueue(session, b"shared", 1 | 4)

    with ThreadPoolExecutor(max_workers=3) as pool:
        worker = pool.submit(journal.process_one, 3, dispatch)
        try:
            assert entered.wait(5)
            waiting = pool.submit(enqueue_for_servers_one_and_three)
            pid = writer_pid.result(timeout=5)
            deadline = monotonic() + 5
            with database() as observer:
                while not observer.scalar(text(
                    "SELECT EXISTS (SELECT FROM pg_locks WHERE pid = :pid "
                    "AND locktype = 'advisory' AND NOT granted)"
                ), {"pid": pid}):
                    assert monotonic() < deadline, "writer did not reach the busy target"
                    sleep(0.02)
            # Even target 1, earlier in the waiting writer's mask, is free.
            assert pool.submit(queue, database, b"independent", 1 | 8).result(timeout=3) == 2
            assert not waiting.done()
        finally:
            release.set()
        assert worker.result(timeout=5) == "done"
        assert waiting.result(timeout=5) == 2
    with database() as session:
        rows = session.scalars(select(journal.BlacklistSyncDelivery.command).where(
            journal.BlacklistSyncDelivery.server_number == 1).order_by(journal.BlacklistSyncDelivery.id))
        assert list(rows) == [b"independent", b"shared"]


@pytest.mark.parametrize("expire_first", [True, False])
def test_expiry_and_creation_for_distinct_players_dispatch_in_order(database, expire_first):
    kind = blacklist.BlacklistCommandType
    expiry = blacklist.BlacklistCommand(kind.EXPIRE_ALL, 4, {"player_id": "player-a"}).encode()
    create = blacklist.BlacklistCommand(kind.CREATE_RECORD, 4, {"player_id": "player-b", "record_id": 7}).encode()
    commands = [expiry, create] if expire_first else [create, expiry]
    for command in commands:
        queue(database, command, 4)
    seen = []
    for _ in commands:
        assert journal.process_one(3, seen.append) == "done"
    assert seen == commands
    assert journal.process_one(3, seen.append) == "empty"


@pytest.mark.parametrize("following", ["expiry", "eos_alias", "list", "missing_identity"])
def test_expiry_keeps_overlapping_or_unclear_work_in_review(database, following):
    kind = blacklist.BlacklistCommandType
    eos = "0123456789abcdef0123456789abcdef"
    expiry = blacklist.BlacklistCommand(kind.EXPIRE_ALL, 4, {"player_id": eos})
    next_command = {
        "expiry": expiry,
        "eos_alias": blacklist.BlacklistCommand(kind.CREATE_RECORD, 4, {
            "record_id": 7, "player_id": "steam-player", "connected_eos_id": eos}),
        "list": blacklist.BlacklistCommand(kind.DELETE_LIST, 4, {}),
        "missing_identity": blacklist.BlacklistCommand(kind.EXPIRE_ALL, 4, {"player_id": None}),
    }[following]
    for command in (expiry, next_command):
        queue(database, command.encode(), 4)
    assert journal.process_one(3, lambda _: pytest.fail("unexpected dispatch")) == "review"
    with database() as session:
        assert list(session.scalars(select(journal.BlacklistSyncDelivery.status))) == ["review", "review"]


@pytest.fixture
def existing_blacklist(database, monkeypatch):
    engine = database.kw["bind"]
    for model in (PlayerID, PlayerName, Blacklist, BlacklistRecord):
        model.__table__.create(engine)
    monkeypatch.setattr(blacklist, "get_session_maker", lambda: database)
    monkeypatch.setattr(blacklist, "update_penalty_count", lambda **_: None)
    with database() as session, session.begin():
        player = PlayerID(player_id="synthetic-player")
        first = Blacklist(name="first", sync=BlacklistSyncMethod.BAN_IMMEDIATELY, servers=1)
        second = Blacklist(name="second", sync=BlacklistSyncMethod.BAN_IMMEDIATELY, servers=2)
        session.add_all([player, first, second])
        session.flush()
        record = BlacklistRecord(player_id_id=player.id, blacklist_id=first.id, reason="old", admin_name="test")
        session.add(record)
        session.flush()
        return record.id, first.id, second.id


def test_hllv_steam_restriction_targets_verified_eos_with_real_database(database, existing_blacklist, monkeypatch):
    from contextlib import contextmanager
    from rcon import hooks

    eos = '0123456789abcdef0123456789abcdef'
    steam = '76561198036685843'
    record_id, first, _ = existing_blacklist
    with database() as session, session.begin():
        record = session.get(BlacklistRecord, record_id)
        record.player.player_id = steam
        record.blacklist.servers = 4  # RCON3 only.
        session.add(PlayerID(player_id=eos))
    @contextmanager
    def session_scope():
        with database() as session:
            yield session
    monkeypatch.setattr(hooks, 'enter_session', session_scope)
    monkeypatch.setattr(hooks, 'get_server_number', lambda: 3)
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', mock.Mock())
    api = mock.Mock()
    monkeypatch.setattr(hooks, 'prepare_online_steam_identity', lambda *_: {'steam_id': steam, 'eos_id': eos})
    api.perma_ban.return_value = True
    assert hooks.ban_if_blacklisted(api, eos, 'synthetic', verified_steam_id=steam) == (True, True)
    assert api.perma_ban.call_args.kwargs['player_id'] == eos
    assert action_guard.pending_players(3, 'BlacklistEnforcement') == set()


def test_hllv_connect_roster_lookup_does_not_block_other_blacklist_writes(database, existing_blacklist, monkeypatch):
    from contextlib import contextmanager
    from rcon import hooks

    eos, steam = '0123456789abcdef0123456789abcdef', '76561198036685843'
    record_id, _, _ = existing_blacklist
    with database() as session, session.begin():
        entry = session.get(BlacklistRecord, record_id)
        entry.player.player_id = steam
        entry.blacklist.servers = 4
        session.add(PlayerID(player_id=eos))
    @contextmanager
    def session_scope():
        with database() as session:
            yield session
    entered, release = Event(), Event()
    def slow_prepare(*_):
        entered.set()
        assert release.wait(10)
        return {'steam_id': steam, 'eos_id': eos}
    monkeypatch.setattr(hooks, 'enter_session', session_scope)
    monkeypatch.setattr(hooks, 'get_server_number', lambda: 3)
    monkeypatch.setattr(hooks, 'prepare_online_steam_identity', slow_prepare)
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', mock.Mock())
    api = mock.Mock()
    api.perma_ban.return_value = True
    with ThreadPoolExecutor(max_workers=2) as executor:
        worker = executor.submit(hooks.ban_if_blacklisted, api, eos, 'synthetic', steam)
        assert entered.wait(10)
        writer = executor.submit(queue, database, b'unrelated synthetic command', 4)
        try:
            assert writer.result(timeout=2) == 1
        finally:
            release.set()
        assert worker.result(timeout=10) == (True, True)
    assert api.perma_ban.call_count == 1


@pytest.mark.parametrize("game,alias,expected", [
    ("hllv", None, "review"), ("hll", None, "done"),
    ("hllv", "0" * 32, "done"), ("hllv", "ABCDEF" + "1" * 26, "review"),
])
@pytest.mark.parametrize("expire_first", [True, False])
def test_expiry_respects_game_and_verified_steam_eos_alias(database, game, alias, expected, expire_first):
    kind = blacklist.BlacklistCommandType
    eos = "abcdef" + "1" * 26
    expiry = blacklist.BlacklistCommand(kind.EXPIRE_ALL, 4, {"player_id": eos})
    payload = {"player_id": "76561198000000001", "record_id": 12}
    if alias:
        payload["connected_eos_id"] = alias
    create = blacklist.BlacklistCommand(kind.CREATE_RECORD, 4, payload)
    commands = [expiry, create] if expire_first else [create, expiry]
    for command in commands:
        queue(database, command.encode(), 4)
    seen = []
    for _ in commands:
        assert journal.process_one(3, seen.append, game=game) == expected
    assert seen == ([cmd.encode() for cmd in commands] if expected == "done" else [])


def test_connect_reconciliation_is_deduplicated_across_workers(database):
    steam = '76561198036685843'
    start = datetime.now(timezone.utc)
    with ThreadPoolExecutor(max_workers=8) as executor:
        results = list(executor.map(lambda _: journal.enqueue_connect_reconciliation(3, steam, 7, start), range(8)))
    assert sum(results) == 1
    with database() as session:
        assert len(session.scalars(select(journal.BlacklistSyncDelivery)).all()) == 1


def test_connect_reconciliation_does_not_hold_global_lock_waiting_for_target(database):
    from rcon.vip_rewards.locking import lock

    entered, release = Event(), Event()
    def hold_target():
        with lock('blacklist-sync:3'):
            entered.set()
            assert release.wait(10)
    with ThreadPoolExecutor(max_workers=3) as executor:
        holder = executor.submit(hold_target)
        assert entered.wait(10)
        deferred = executor.submit(journal.enqueue_connect_reconciliation, 3,
                                   '76561198036685843', 7, datetime.now(timezone.utc))
        try:
            assert deferred.result(timeout=2) is True
            other_server = executor.submit(queue, database, b'unrelated', 8)
            assert other_server.result(timeout=2) == 1
        finally:
            release.set()
        holder.result(timeout=10)


@pytest.mark.parametrize('uncertain', [False, True])
def test_connect_reconciliation_deduplicates_against_inflight_delivery(database, uncertain):
    steam = '76561198036685843'
    started = datetime.now(timezone.utc)
    command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.CREATE_RECORD,
        server_mask=4, payload={'player_id': steam, 'record_id': 7}).encode()
    queue(database, command, 4)
    entered, release = Event(), Event()
    def delivery(_):
        entered.set()
        assert release.wait(10)
        if uncertain:
            raise TimeoutError('synthetic lost response')
    with ThreadPoolExecutor(max_workers=3) as executor:
        worker = executor.submit(journal.process_one, 3, delivery)
        assert entered.wait(10)
        try:
            duplicate = executor.submit(journal.enqueue_connect_reconciliation, 3, steam, 7, started)
            assert duplicate.result(timeout=2) is False
            other_server = executor.submit(queue, database, b'unrelated', 8)
            assert other_server.result(timeout=2) == 1
        finally:
            release.set()
        assert worker.result(timeout=10) == ('review' if uncertain else 'done')
    with database() as session:
        rows = session.scalars(select(journal.BlacklistSyncDelivery).where(
            journal.BlacklistSyncDelivery.server_number == 3)).all()
        assert len(rows) == 1 and rows[0].status == ('review' if uncertain else 'done')


@pytest.mark.parametrize('command_type,payload', [
    (blacklist.BlacklistCommandType.EDIT_RECORD,
     {'old_record': {'id': 7, 'player_id': '76561198036685843'}}),
    (blacklist.BlacklistCommandType.DELETE_RECORD,
     {'old_record': {'id': 7, 'player_id': '76561198036685843'}}),
    (blacklist.BlacklistCommandType.EDIT_LIST, {'synthetic': True}),
])
def test_connect_reconciliation_marks_overlapping_inflight_change_for_review(database, command_type, payload):
    steam = '76561198036685843'
    started = datetime.now(timezone.utc)
    command = blacklist.BlacklistCommand(command=command_type, server_mask=4, payload=payload).encode()
    queue(database, command, 4)
    entered, release = Event(), Event()
    def delivery(_):
        entered.set()
        assert release.wait(10)
    with ThreadPoolExecutor(max_workers=2) as executor:
        worker = executor.submit(journal.process_one, 3, delivery)
        assert entered.wait(10)
        try:
            assert journal.enqueue_connect_reconciliation(3, steam, 7, started)
            with database() as session:
                rows = session.scalars(select(journal.BlacklistSyncDelivery).order_by(
                    journal.BlacklistSyncDelivery.id)).all()
                assert len(rows) == 2 and rows[1].status == 'review'
        finally:
            release.set()
        assert worker.result(timeout=10) == 'done'
    assert journal.process_one(3, lambda _: pytest.fail('must not replay')) == 'review'


def test_connect_reconciliation_keeps_unrelated_player_work_queued(database):
    started = datetime.now(timezone.utc)
    command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.EDIT_RECORD,
        server_mask=4, payload={'old_record': {'id': 8, 'player_id': '76561198036685844'}}).encode()
    queue(database, command, 4)
    assert journal.enqueue_connect_reconciliation(3, '76561198036685843', 7, started)
    with database() as session:
        rows = session.scalars(select(journal.BlacklistSyncDelivery).order_by(
            journal.BlacklistSyncDelivery.id)).all()
        assert rows[1].status == 'queued'


@pytest.mark.parametrize('command_type', [blacklist.BlacklistCommandType.CREATE_RECORD,
                                          blacklist.BlacklistCommandType.EDIT_RECORD,
                                          blacklist.BlacklistCommandType.EXPIRE_ALL])
def test_connect_reconciliation_detects_overlap_with_verified_eos_alias(database, command_type):
    eos, steam = '0123456789abcdef0123456789abcdef', '76561198036685843'
    started = datetime.now(timezone.utc)
    payload = ({'record_id': 8, 'player_id': eos} if command_type == blacklist.BlacklistCommandType.CREATE_RECORD
               else {'old_record': {'id': 8, 'player_id': eos}} if command_type == blacklist.BlacklistCommandType.EDIT_RECORD
               else {'player_id': eos})
    command = blacklist.BlacklistCommand(command=command_type, server_mask=4, payload=payload).encode()
    queue(database, command, 4)
    assert journal.enqueue_connect_reconciliation(3, steam, 7, started, connected_eos_id=eos)
    with database() as session:
        rows = session.scalars(select(journal.BlacklistSyncDelivery).order_by(
            journal.BlacklistSyncDelivery.id)).all()
        assert rows[-1].status == 'review'


def test_existing_connect_delivery_is_held_when_verified_eos_action_is_inflight(database):
    eos, steam = '0123456789abcdef0123456789abcdef', '76561198036685843'
    started = datetime.now(timezone.utc)
    eos_command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.CREATE_RECORD,
        server_mask=4, payload={'record_id': 8, 'player_id': eos}).encode()
    steam_command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.CREATE_RECORD,
        server_mask=4, payload={'record_id': 7, 'player_id': steam}).encode()
    queue(database, eos_command, 4)
    queue(database, steam_command, 4)
    entered, release = Event(), Event()
    def delivery(_):
        entered.set()
        assert release.wait(10)
    with ThreadPoolExecutor(max_workers=2) as executor:
        worker = executor.submit(journal.process_one, 3, delivery)
        assert entered.wait(10)
        try:
            assert not journal.enqueue_connect_reconciliation(3, steam, 7, started, connected_eos_id=eos)
            with database() as session:
                rows = session.scalars(select(journal.BlacklistSyncDelivery).order_by(
                    journal.BlacklistSyncDelivery.id)).all()
                assert len(rows) == 2 and rows[1].status == 'review'
        finally:
            release.set()
        assert worker.result(timeout=10) == 'done'
    assert journal.process_one(3, lambda _: pytest.fail('must not replay')) == 'review'


@pytest.mark.parametrize('command_type', [blacklist.BlacklistCommandType.CREATE_RECORD,
                                          blacklist.BlacklistCommandType.EDIT_RECORD,
                                          blacklist.BlacklistCommandType.EXPIRE_ALL])
def test_later_eos_change_overlaps_earlier_verified_steam_connect_intent(database, command_type):
    eos, steam = '0123456789abcdef0123456789abcdef', '76561198036685843'
    assert journal.enqueue_connect_reconciliation(3, steam, 7, datetime.now(timezone.utc),
                                                  connected_eos_id=eos)
    payload = ({'record_id': 8, 'player_id': eos} if command_type == blacklist.BlacklistCommandType.CREATE_RECORD
               else {'old_record': {'id': 8, 'player_id': eos}} if command_type == blacklist.BlacklistCommandType.EDIT_RECORD
               else {'player_id': eos})
    command = blacklist.BlacklistCommand(command=command_type, server_mask=4, payload=payload).encode()
    queue(database, command, 4)
    assert journal.process_one(3, lambda _: pytest.fail('must not execute overlapping action')) == 'review'
    with database() as session:
        rows = session.scalars(select(journal.BlacklistSyncDelivery).order_by(
            journal.BlacklistSyncDelivery.id)).all()
        assert [row.status for row in rows] == ['review', 'review']


def test_connect_reconciliation_reviews_recently_completed_overlapping_edit(database):
    steam = '76561198036685843'
    started = datetime.now(timezone.utc) - timedelta(seconds=1)
    command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.EDIT_RECORD,
        server_mask=4, payload={'old_record': {'id': 7, 'player_id': steam}}).encode()
    queue(database, command, 4)
    assert journal.process_one(3, lambda _: True) == 'done'
    assert journal.enqueue_connect_reconciliation(3, steam, 7, started)
    with database() as session:
        rows = session.scalars(select(journal.BlacklistSyncDelivery).order_by(
            journal.BlacklistSyncDelivery.id)).all()
        assert rows[-1].status == 'review'


def test_connect_reconciliation_does_not_repeat_recently_completed_delivery(database):
    steam = '76561198036685843'
    start = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert journal.enqueue_connect_reconciliation(3, steam, 7, start)
    with database() as session, session.begin():
        delivery = session.scalar(select(journal.BlacklistSyncDelivery))
        delivery.status = 'done'
        delivery.updated_at = datetime.now(timezone.utc)
    assert not journal.enqueue_connect_reconciliation(3, steam, 7, start)
    with database() as session:
        assert len(session.scalars(select(journal.BlacklistSyncDelivery)).all()) == 1


def test_unavailable_connect_identity_is_queued_then_enforced_once(database, existing_blacklist, monkeypatch):
    from contextlib import contextmanager, nullcontext
    from rcon import hooks
    from rcon.types import GameEnum

    eos, steam = '0123456789abcdef0123456789abcdef', '76561198036685843'
    record_id, _, _ = existing_blacklist
    with database() as session, session.begin():
        entry = session.get(BlacklistRecord, record_id)
        entry.player.player_id = steam
        entry.blacklist.servers = 4
        entry.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        session.add(PlayerID(player_id=eos))
    @contextmanager
    def session_scope():
        with database() as session:
            yield session
    monkeypatch.setattr(hooks, 'enter_session', session_scope)
    monkeypatch.setattr(hooks, 'get_server_number', lambda: 3)
    monkeypatch.setattr(hooks, 'prepare_online_steam_identity', mock.Mock(side_effect=OSError('offline')))
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', mock.Mock())
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [{'iD': eos, 'eosId': eos, 'steamId': steam,
                                             'platform': 'EPlatformFamily::Steam'}]
    api.get_uncached_detailed_player_info.return_value = {'player_id': eos, 'eos_id': eos, 'steam_id': steam,
                                                           'platform': 'EPlatformFamily::Steam', 'name': 'synthetic'}
    api.kick.return_value = True
    assert hooks.ban_if_blacklisted(api, eos, 'synthetic', steam) == (True, False)
    api.kick.assert_not_called()
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'done'
    assert api.kick.call_count == 1 and api.kick.call_args.kwargs['player_id'] == eos
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'empty'


def test_hllv_alias_respects_expiry_and_server_scope(database, existing_blacklist, monkeypatch):
    from rcon import hooks

    record_id, first, _ = existing_blacklist
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    with database() as session, session.begin():
        record = session.get(BlacklistRecord, record_id)
        record.player.player_id = '76561198036685843'
        record.blacklist.servers = 2  # Different server.
    with database() as session:
        assert hooks._connect_blacklist_record(session, 'synthetic-eos', '76561198036685843') is None
    with database() as session, session.begin():
        record = session.get(BlacklistRecord, record_id)
        record.blacklist.servers = 4
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    with database() as session:
        assert hooks._connect_blacklist_record(session, 'synthetic-eos', '76561198036685843') is None


def test_hllv_online_steam_record_journal_targets_eos_once(database, existing_blacklist, monkeypatch):
    from contextlib import nullcontext
    from rcon.types import GameEnum

    record_id, _, _ = existing_blacklist
    steam = '76561198036685843'
    eos = '0123456789abcdef0123456789abcdef'
    with database() as session, session.begin():
        record = session.get(BlacklistRecord, record_id)
        record.player.player_id = steam
        record.blacklist.servers = 4
        record.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        session.add(PlayerID(player_id=eos))
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', mock.Mock())
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [{'iD': eos, 'eosId': eos, 'steamId': steam,
                                             'platform': 'EPlatformFamily::Steam'}]
    api.get_uncached_detailed_player_info.return_value = {'player_id': eos, 'eos_id': eos, 'steam_id': steam,
                                                 'platform': 'EPlatformFamily::Steam', 'name': 'synthetic'}
    api.kick.return_value = True
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.CREATE_RECORD,
        server_mask=4, payload={'record_id': record_id, 'player_id': steam}).encode()
    queue(database, command, 4)
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'done'
    assert api.kick.call_count == 1 and api.kick.call_args.kwargs['player_id'] == eos
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'empty'
    assert action_guard.pending_players(3, 'BlacklistEnforcement') == set()


def test_hllv_kick_only_newly_applies_on_server_through_journal(database, existing_blacklist, monkeypatch):
    from contextlib import nullcontext
    from rcon.types import GameEnum

    record_id, _, _ = existing_blacklist
    steam, eos = '76561198036685843', '0123456789abcdef0123456789abcdef'
    with database() as session, session.begin():
        record = session.get(BlacklistRecord, record_id)
        record.player.player_id = steam
        record.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        record.blacklist.servers = 2
        old = record.to_dict()
        record.blacklist.servers = 4
        session.add(PlayerID(player_id=eos))
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', mock.Mock())
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [{'iD': eos, 'eosId': eos, 'steamId': steam,
                                             'platform': 'EPlatformFamily::Steam'}]
    api.get_uncached_detailed_player_info.return_value = {'player_id': eos, 'eos_id': eos, 'steam_id': steam,
                                                 'platform': 'EPlatformFamily::Steam', 'name': 'synthetic'}
    api.kick.return_value = True
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.EDIT_RECORD,
        server_mask=4, payload={'old_record': old}).encode()
    queue(database, command, 4)
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'done'
    assert api.kick.call_count == 1 and api.kick.call_args.kwargs['player_id'] == eos
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


def test_hllv_new_kick_list_deduplicates_verified_steam_and_eos(database, existing_blacklist, monkeypatch):
    from contextlib import nullcontext
    from rcon.types import GameEnum

    record_id, list_id, _ = existing_blacklist
    steam, eos = '76561198036685843', '0123456789abcdef0123456789abcdef'
    with database() as session, session.begin():
        entry = session.get(BlacklistRecord, record_id)
        entry.player.player_id = steam
        entry.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        entry.blacklist.servers = 2
        old = entry.blacklist.to_dict()
        entry.blacklist.servers = 4
        new = entry.blacklist.to_dict()
        linked = PlayerID(player_id=eos)
        session.add(linked)
        session.flush()
        session.add(BlacklistRecord(player_id_id=linked.id, blacklist_id=list_id,
                                    reason='synthetic', admin_name='test'))
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', mock.Mock())
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [{'iD': eos, 'eosId': eos, 'steamId': steam,
                                             'platform': 'EPlatformFamily::Steam'}]
    api.get_uncached_detailed_player_info.return_value = {'player_id': eos, 'eos_id': eos, 'steam_id': steam,
                                                           'platform': 'EPlatformFamily::Steam', 'name': 'synthetic'}
    api.kick.return_value = True
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.EDIT_LIST,
        server_mask=4, payload={'old_blacklist': old, 'new_blacklist': new}).encode()
    queue(database, command, 4)
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'done'
    api.kick.assert_called_once()
    assert api.kick.call_args.kwargs['player_id'] == eos
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'empty'
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


def test_hllv_new_kick_list_waits_for_complete_roster(database, existing_blacklist, monkeypatch):
    from contextlib import nullcontext
    from rcon.types import GameEnum

    record_id, _, _ = existing_blacklist
    eos = '0123456789abcdef0123456789abcdef'
    with database() as session, session.begin():
        entry = session.get(BlacklistRecord, record_id)
        entry.player.player_id = '76561198036685843'
        entry.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        entry.blacklist.servers = 2
        old = entry.blacklist.to_dict()
        entry.blacklist.servers = 4
        new = entry.blacklist.to_dict()
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [{'iD': eos, 'eosId': eos, 'steamId': None,
                                             'platform': 'EPlatformFamily::Steam'}]
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.EDIT_LIST,
        server_mask=4, payload={'old_blacklist': old, 'new_blacklist': new}).encode()
    queue(database, command, 4)
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'deferred'
    with database() as session:
        assert session.scalar(select(journal.BlacklistSyncDelivery.status)) == 'queued'
    api.kick.assert_not_called()


def test_hllv_new_kick_list_partial_timeout_requires_review_without_replay(database, existing_blacklist, monkeypatch):
    from contextlib import nullcontext
    from rcon.types import GameEnum

    record_id, list_id, _ = existing_blacklist
    steam, eos = '76561198036685843', '0123456789abcdef0123456789abcdef'
    console = 'fedcba9876543210fedcba9876543210'
    with database() as session, session.begin():
        entry = session.get(BlacklistRecord, record_id)
        entry.player.player_id = steam
        entry.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        entry.blacklist.servers = 2
        old = entry.blacklist.to_dict()
        entry.blacklist.servers = 4
        new = entry.blacklist.to_dict()
        second = PlayerID(player_id=console)
        session.add(second)
        session.flush()
        session.add(BlacklistRecord(player_id_id=second.id, blacklist_id=list_id,
                                    reason='synthetic', admin_name='test'))
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', mock.Mock())
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [
        {'iD': eos, 'eosId': eos, 'steamId': steam, 'platform': 'EPlatformFamily::Steam'},
        {'iD': console, 'eosId': console, 'steamId': None, 'platform': 'EPlatformFamily::PS5'},
    ]
    def details(player_id):
        return {'player_id': player_id, 'eos_id': player_id, 'name': 'synthetic',
                'steam_id': steam if player_id == eos else None,
                'platform': 'EPlatformFamily::Steam' if player_id == eos else 'EPlatformFamily::PS5'}
    api.get_uncached_detailed_player_info.side_effect = details
    api.kick.side_effect = [True, TimeoutError('synthetic lost response')]
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.EDIT_LIST,
        server_mask=4, payload={'old_blacklist': old, 'new_blacklist': new}).encode()
    queue(database, command, 4)
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'review'
    assert api.kick.call_count == 2
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'review'
    assert api.kick.call_count == 2
    with database() as session:
        delivery = session.scalar(select(journal.BlacklistSyncDelivery))
        assert delivery.reason == 'unconfirmed: RuntimeError'
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


@pytest.mark.parametrize('ban_mask', [None, 4, 8])
def test_hllv_expire_all_only_skips_unban_for_proven_kick_only_records(
        database, existing_blacklist, monkeypatch, ban_mask):
    from rcon.types import GameEnum

    record_id, _, second_id = existing_blacklist
    steam = '76561198036685843'
    with database() as session, session.begin():
        entry = session.get(BlacklistRecord, record_id)
        entry.player.player_id = steam
        entry.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        entry.blacklist.servers = 4
        if ban_mask is not None:
            second = session.get(Blacklist, second_id)
            second.servers = ban_mask
            session.add(BlacklistRecord(player_id_id=entry.player_id_id, blacklist_id=second.id,
                                        reason='synthetic', admin_name='test'))
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    blacklist.expire_all_player_blacklists(steam)
    with database() as session:
        delivery = session.scalar(select(journal.BlacklistSyncDelivery).where(
            journal.BlacklistSyncDelivery.server_number == 3))
        command = blacklist.BlacklistCommand.decode(delivery.command)
        assert command.payload['kick_only_server_mask'] == (0 if ban_mask == 4 else 4)
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    result = journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                                 prepare=receiver._prepare_delivery)
    assert result == ('review' if ban_mask == 4 else 'done')
    api.get_temp_bans.assert_not_called()
    api.get_perma_bans.assert_not_called()
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


@pytest.mark.parametrize('remaining_hours,expected', [(3, 'done'), (2, 'review'), (1, 'review')])
def test_hllv_deleted_kick_list_with_remaining_steam_restriction_uses_priority(
        database, existing_blacklist, monkeypatch, remaining_hours, expected):
    from rcon.types import GameEnum

    record_id, first_id, second_id = existing_blacklist
    now = datetime.now(timezone.utc)
    with database() as session, session.begin():
        entry = session.get(BlacklistRecord, record_id)
        entry.player.player_id = '76561198036685843'
        entry.created_at = now
        entry.expires_at = now + timedelta(hours=2)
        entry.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        entry.blacklist.servers = 4
        other = session.get(Blacklist, second_id)
        other.servers = 4
        session.add(BlacklistRecord(player_id_id=entry.player_id_id, blacklist_id=other.id,
                                    created_at=now, expires_at=now + timedelta(hours=remaining_hours),
                                    reason='synthetic', admin_name='test'))
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    assert blacklist.delete_blacklist(first_id)
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == expected
    api.kick.assert_not_called()
    api.temp_ban.assert_not_called()
    api.perma_ban.assert_not_called()
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


def test_hllv_list_mode_change_surfaces_ownership_review(database, existing_blacklist, monkeypatch):
    from rcon.types import GameEnum

    record_id, list_id, _ = existing_blacklist
    with database() as session, session.begin():
        entry = session.get(BlacklistRecord, record_id)
        entry.player.player_id = '76561198036685843'
        entry.blacklist.servers = 4
        entry.blacklist.sync = BlacklistSyncMethod.BAN_IMMEDIATELY
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    blacklist.edit_blacklist(list_id, sync=BlacklistSyncMethod.BAN_ON_CONNECT)
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'review'
    result = journal.list_reviews(3)
    assert result['total'] == 1 and result['results'][0]['review_kind'] == 'hllv_ownership'
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


@pytest.mark.parametrize('missing', ['name', 'steamId', 'platform'])
def test_hllv_malformed_roster_defers_then_recovers_without_losing_delivery(database, existing_blacklist, monkeypatch, missing):
    from contextlib import nullcontext
    from rcon.game.hllv.player_adapter import HLLVPlayerInfoAdapter
    from rcon.rcon import Rcon
    from rcon.types import GameEnum

    record_id, _, _ = existing_blacklist
    steam = '76561198036685843'
    eos = '0123456789abcdef0123456789abcdef'
    with database() as session, session.begin():
        record = session.get(BlacklistRecord, record_id)
        record.player.player_id = steam
        record.blacklist.servers = 4
        record.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        session.add(PlayerID(player_id=eos))
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', mock.Mock())
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.game_profile.player_adapter = HLLVPlayerInfoAdapter()
    api.without_retries.side_effect = nullcontext
    raw = {'iD': eos, 'eosId': eos, 'steamId': steam, 'platform': 'EPlatformFamily::Steam', 'name': 'synthetic'}
    incomplete = {key: value for key, value in raw.items() if key != missing}
    api.get_uncached_player_snapshot.side_effect = [{'players': [incomplete]}, {'players': [raw]}]
    api.get_all_player_info.side_effect = lambda **kwargs: Rcon.get_all_player_info(api, **kwargs)
    api.get_uncached_detailed_player_info.return_value = {'player_id': eos, 'eos_id': eos, 'steam_id': steam,
                                                 'platform': 'EPlatformFamily::Steam', 'name': 'synthetic'}
    api.kick.return_value = True
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.CREATE_RECORD,
        server_mask=4, payload={'record_id': record_id, 'player_id': steam}).encode()
    queue(database, command, 4)
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'deferred'
    with database() as session:
        assert session.scalar(select(journal.BlacklistSyncDelivery)).status == 'queued'
    api.kick.assert_not_called()
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'done'
    assert api.kick.call_count == 1 and api.kick.call_args.kwargs['player_id'] == eos


def test_hllv_online_uncertain_kick_is_never_replayed(database, existing_blacklist, monkeypatch):
    from contextlib import nullcontext
    from rcon.types import GameEnum

    record_id, _, _ = existing_blacklist
    steam, eos = '76561198036685843', '0123456789abcdef0123456789abcdef'
    with database() as session, session.begin():
        record = session.get(BlacklistRecord, record_id)
        record.player.player_id = steam
        record.blacklist.servers = 4
        record.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        session.add(PlayerID(player_id=eos))
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', mock.Mock())
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [{'iD': eos, 'eosId': eos, 'steamId': steam,
                                             'platform': 'EPlatformFamily::Steam'}]
    api.get_uncached_detailed_player_info.return_value = {'player_id': eos, 'eos_id': eos, 'steam_id': steam,
                                                 'platform': 'EPlatformFamily::Steam', 'name': 'synthetic'}
    api.kick.side_effect = TimeoutError('synthetic lost response')
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    command = blacklist.BlacklistCommand(command=blacklist.BlacklistCommandType.CREATE_RECORD,
        server_mask=4, payload={'record_id': record_id, 'player_id': steam}).encode()
    queue(database, command, 4)
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'review'
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'review'
    assert api.kick.call_count == 1
    assert action_guard.pending_players(3, 'BlacklistEnforcement') == {eos}


@pytest.mark.parametrize('sync,expected', [
    (BlacklistSyncMethod.KICK_ONLY, 'done'),
    (BlacklistSyncMethod.BAN_IMMEDIATELY, 'review'),
])
def test_hllv_steam_deletion_preserves_unowned_game_bans(database, existing_blacklist, monkeypatch, sync, expected):
    from contextlib import nullcontext
    from rcon.types import GameEnum

    record_id, _, _ = existing_blacklist
    steam, eos = '76561198036685843', '0123456789abcdef0123456789abcdef'
    with database() as session, session.begin():
        record = session.get(BlacklistRecord, record_id)
        record.player.player_id = steam
        record.blacklist.servers = 4
        record.blacklist.sync = sync
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    assert blacklist.remove_record_from_blacklist(record_id)
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [{'iD': eos, 'eosId': eos, 'steamId': steam,
                                             'platform': 'EPlatformFamily::Steam'}]
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == expected
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()
    api.kick.assert_not_called()
    if expected == 'review':
        with database() as session:
            row = session.scalar(select(journal.BlacklistSyncDelivery))
            assert 'HLLVSteamBanOwnershipUnverified' in row.reason


def test_hllv_list_move_from_kick_to_ban_targets_verified_eos(database, existing_blacklist, monkeypatch):
    from contextlib import nullcontext
    from rcon.types import GameEnum

    record_id, first, second = existing_blacklist
    steam, eos = '76561198036685843', '0123456789abcdef0123456789abcdef'
    with database() as session, session.begin():
        record = session.get(BlacklistRecord, record_id)
        record.player.player_id = steam
        record.blacklist.servers = 4
        record.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
        destination = session.get(Blacklist, second)
        destination.servers = 4
        destination.sync = BlacklistSyncMethod.BAN_IMMEDIATELY
        session.add(PlayerID(player_id=eos))
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 3)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', mock.Mock())
    assert blacklist.edit_record_from_blacklist(record_id, blacklist_id=second)
    api = mock.Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [{'iD': eos, 'eosId': eos, 'steamId': steam,
                                             'platform': 'EPlatformFamily::Steam'}]
    api.get_uncached_detailed_player_info.return_value = {'player_id': eos, 'eos_id': eos, 'steam_id': steam,
                                                 'platform': 'EPlatformFamily::Steam', 'name': 'synthetic'}
    api.perma_ban.return_value = True
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = api
    assert journal.process_one(3, receiver.dispatch, is_ready=lambda: True,
                               prepare=receiver._prepare_delivery) == 'done'
    assert api.perma_ban.call_args.kwargs['player_id'] == eos
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()
def test_edit_commits_both_target_deliveries_with_record(database, existing_blacklist):
    record_id, _first, second = existing_blacklist
    result = blacklist.edit_record_from_blacklist(record_id, blacklist_id=second, reason="new")
    assert result["blacklist"]["id"] == second
    with database() as session:
        record = session.get(BlacklistRecord, record_id)
        deliveries = session.scalars(select(journal.BlacklistSyncDelivery).order_by(journal.BlacklistSyncDelivery.id)).all()
        assert record.reason == "new"
        assert [row.server_number for row in deliveries] == [1, 2]
        assert all(blacklist.BlacklistCommand.decode(row.command).server_mask == 3 for row in deliveries)


def test_failed_journal_insert_rolls_back_blacklist_edit(database, existing_blacklist, monkeypatch):
    record_id, first, second = existing_blacklist
    def fail(*_args):
        raise RuntimeError("synthetic database failure")
    monkeypatch.setattr(journal, "enqueue", fail)
    with pytest.raises(RuntimeError, match="synthetic database failure"):
        blacklist.edit_record_from_blacklist(record_id, blacklist_id=second, reason="new")
    with database() as session:
        record = session.get(BlacklistRecord, record_id)
        assert (record.blacklist_id, record.reason) == (first, "old")
        assert session.scalars(select(journal.BlacklistSyncDelivery)).all() == []


def test_record_deletion_and_its_delivery_commit_together(database, existing_blacklist):
    record_id, _first, _second = existing_blacklist
    assert blacklist.remove_record_from_blacklist(record_id) is True
    with database() as session:
        assert session.get(BlacklistRecord, record_id) is None
        row = session.scalar(select(journal.BlacklistSyncDelivery))
        command = blacklist.BlacklistCommand.decode(row.command)
        assert row.server_number == 1
        assert command.command == blacklist.BlacklistCommandType.DELETE_RECORD
        assert command.payload["old_record"]["player_id"] == "synthetic-player"


@pytest.mark.parametrize("temporary", [False, True], ids=["permanent", "temporary"])
@pytest.mark.parametrize("case,expected", [
    ("newer", "done"), ("owned", "done"), ("absent", "done"), ("kick_only", "done"),
    ("other_admin", "review"), ("other_record", "review"), ("untagged", "review"),
    ("ambiguous_time", "review"), ("legacy_order", "review"), ("duplicates", "review"),
    ("unreadable", "review"), ("rejected", "review"), ("timeout", "review"),
    ("queued_edit", "done"),
])
def test_delayed_single_delete_preserves_independent_bans(
        database, existing_blacklist, monkeypatch, temporary, case, expected):
    from types import SimpleNamespace
    from rcon.rcon import Rcon
    from rcon.types import GameEnum

    record_id, list_id, other_list_id = existing_blacklist
    pid = "abcdef0123456789abcdef0123456789"
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 3)
    with database.begin() as db:
        record = db.get(BlacklistRecord, record_id)
        record.player.player_id = pid
        if temporary:
            record.expires_at = datetime.now(timezone.utc) + timedelta(hours=6)
        blocklist = db.get(Blacklist, list_id)
        blocklist.servers = 4
        blocklist.sync = BlacklistSyncMethod.KICK_ONLY if case == "kick_only" else BlacklistSyncMethod.BAN_ON_CONNECT
        actor = blacklist._blacklist_ban_actor(record)
        assert actor.startswith(f"BLACKLIST #{record_id}/") and actor.endswith(": test")
        if case == "queued_edit":
            other = db.get(Blacklist, other_list_id)
            other.servers, other.sync = 4, BlacklistSyncMethod.KICK_ONLY
    if case == "queued_edit":
        blacklist.edit_record_from_blacklist(record_id, blacklist_id=other_list_id)
    assert blacklist.remove_record_from_blacklist(record_id)
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    ctl = receiver.rcon = Rcon.__new__(Rcon)
    ctl.game_profile = SimpleNamespace(game=GameEnum.HLL_VIETNAM)
    def process(ready=True):
        return journal.process_one(3, receiver.dispatch, is_ready=lambda: ready,
                                   prepare=receiver._prepare_delivery, game=GameEnum.HLL_VIETNAM)
    assert process(False) == "deferred"
    with database.begin() as db:
        row = db.scalar(select(journal.BlacklistSyncDelivery).order_by(journal.BlacklistSyncDelivery.id.desc()))
        command = blacklist.BlacklistCommand.decode(row.command)
        requested = datetime.fromisoformat(command.payload["requested_at"])
        assert requested <= row.created_at
        if case == "legacy_order":
            del command.payload["requested_at"]
            row.command = command.encode()
    kind = "Temporary" if temporary else "Permanent"
    stamp = (requested - timedelta(seconds=5)).isoformat()
    if case in {"newer", "queued_edit"}:
        stamp = (requested + timedelta(seconds=5)).isoformat()
    elif case == "ambiguous_time":
        stamp = requested.isoformat(timespec="seconds")
    by = {"other_admin": "Moderator", "untagged": "BLACKLIST: test",
          "other_record": f"BLACKLIST #{record_id + 1}: test"}.get(case, actor)
    ban = {"userId": pid.upper(), "userName": "Fixture", "timeOfBanning": stamp,
           "durationHours": 2, "banReason": "Reason", "adminName": by}
    rows = [] if case == "absent" else [ban] * (2 if case == "duplicates" else 1)
    def read(command, version):
        if case == "unreadable":
            raise TimeoutError()
        return SimpleNamespace(content_dict={"banList": rows if command == f"Get{kind}Bans" else []})
    ctl.exchange = mock.Mock(side_effect=read)
    ctl.exchange_success = mock.Mock(return_value=case != "rejected",
                                     side_effect=TimeoutError() if case == "timeout" else None)
    assert process() == expected
    if case in {"owned", "rejected", "timeout"}:
        ctl.exchange_success.assert_called_once_with(f"Remove{kind}Ban", 2, {"PlayerId": pid.upper()})
    else:
        ctl.exchange_success.assert_not_called()
    if case == "kick_only":
        ctl.exchange.assert_not_called()
    with database() as db:
        deliveries = db.scalars(select(journal.BlacklistSyncDelivery)).all()
        assert all(row.status == expected for row in deliveries)
        if case in {"queued_edit", "newer"}:
            assert all(row.reason == "Newer game ban preserved" for row in deliveries)
        elif expected == "review":
            assert all(row.reason for row in deliveries)
    attempts = ctl.exchange_success.call_count
    assert process() == ("empty" if expected == "done" else "review")
    assert ctl.exchange_success.call_count == attempts


@pytest.mark.parametrize("present", ["remaining", "independent", "absent"])
def test_delete_preserves_or_applies_remaining_list(database, existing_blacklist, monkeypatch, present):
    from contextlib import nullcontext
    from types import SimpleNamespace
    from rcon.types import GameEnum

    record_id, _, second = existing_blacklist
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 1)
    with database.begin() as db:
        old = db.get(BlacklistRecord, record_id)
        db.get(Blacklist, second).servers = 1
        other = BlacklistRecord(blacklist_id=second, player_id_id=old.player_id_id, reason="Other",
                                admin_name="test", created_at=old.created_at - timedelta(days=1))
        db.add(other)
        db.flush()
        actor = blacklist._blacklist_ban_actor(other)
        stamp = (old.created_at - timedelta(minutes=2)).isoformat()
        independent = (old.created_at + timedelta(hours=1)).isoformat()
    assert blacklist.remove_record_from_blacklist(record_id)
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    ctl = receiver.rcon = mock.Mock()
    ctl.game_profile = SimpleNamespace(game=GameEnum.HLL_WW2)
    ctl.get_temp_bans.return_value = []
    ctl.get_perma_bans.return_value = [] if present == "absent" else [
        {"player_id": "synthetic-player", "ban_time": stamp if present == "remaining" else independent,
         "by": actor if present == "remaining" else "Moderator"}]
    ctl.get_detailed_player_info.return_value = {"name": "Test"}
    ctl.without_retries.side_effect = nullcontext
    ctl.perma_ban.return_value = True
    monkeypatch.setattr(blacklist, "send_to_discord_audit", mock.Mock())
    assert journal.process_one(1, receiver.dispatch) == "done"
    assert ctl.perma_ban.call_count == int(present == "absent")
    if present == "absent":
        assert ctl.perma_ban.call_args.kwargs["by"] == actor
    ctl.remove_perma_ban.assert_not_called()


@pytest.mark.parametrize("temporary", [False, True])
def test_manual_ban_waiting_during_conditional_removal_survives(
        database, existing_blacklist, monkeypatch, temporary):
    from types import SimpleNamespace
    from rcon import rcon as api
    from rcon.leadership_vote import storage
    from rcon.types import GameEnum

    record_id, _, _ = existing_blacklist
    pid = "abcdef0123456789abcdef0123456789"
    monkeypatch.setenv("SERVER_NUMBER", "1")
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 1)
    monkeypatch.setattr(storage, "before_manual_action", lambda *_: None)
    monkeypatch.setattr(api, "safe_save_player_action", lambda **_: None)
    with database.begin() as db:
        record = db.get(BlacklistRecord, record_id)
        record.player.player_id = pid
        record.created_at = datetime.now(timezone.utc) - timedelta(minutes=5)
        if temporary:
            record.expires_at = datetime.now(timezone.utc) + timedelta(hours=4)
        actor = blacklist._blacklist_ban_actor(record)
    assert blacklist.remove_record_from_blacklist(record_id)
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    ctl = receiver.rcon = api.Rcon.__new__(api.Rcon)
    ctl.game_profile = SimpleNamespace(game=GameEnum.HLL_VIETNAM)
    kind = "Temporary" if temporary else "Permanent"
    read_started, manual_attempt, release_read = Event(), Event(), Event()
    writes = []
    def read(command, version):
        assert command == f"Get{kind}Bans"
        read_started.set()
        assert release_read.wait(10)
        return SimpleNamespace(content_dict={"banList": [{"userId": pid, "userName": "Test",
            "timeOfBanning": (datetime.now(timezone.utc) - timedelta(minutes=1)).isoformat(),
            "durationHours": 3, "banReason": "List", "adminName": actor}]})
    ctl.exchange = read
    def write(command, version, payload):
        writes.append(command)
        return True
    ctl.exchange_success = write
    def manual_ban():
        manual_attempt.set()
        ban = ctl.temp_ban if temporary else ctl.perma_ban
        return ban(player_id=pid.upper(), reason="Independent decision", by="Moderator")
    with ThreadPoolExecutor(max_workers=2) as pool:
        deleting = pool.submit(journal.process_one, 1, receiver.dispatch)
        try:
            assert read_started.wait(10)
            manual = pool.submit(manual_ban)
            assert manual_attempt.wait(10)
            with pytest.raises(TimeoutError):
                manual.result(timeout=0.15)
        finally:
            release_read.set()
        assert deleting.result(timeout=10) == "done"
        assert manual.result(timeout=10) is True
    assert writes == [f"Remove{kind}Ban", f"{kind}BanPlayer"]


def test_create_edit_list_and_expire_each_create_durable_events(database, existing_blacklist, monkeypatch):
    _record_id, first, _second = existing_blacklist
    monkeypatch.setattr(blacklist, "_get_set_player", lambda session, player_id: session.scalar(
        select(PlayerID).where(PlayerID.player_id == player_id)))
    blacklist.add_record_to_blacklist("synthetic-player", first, "new", admin_name="test")
    blacklist.edit_blacklist(first, name="changed")
    blacklist.expire_all_player_blacklists("synthetic-player")
    with database() as session:
        rows = session.scalars(select(journal.BlacklistSyncDelivery)
                               .where(journal.BlacklistSyncDelivery.server_number == 1)
                               .order_by(journal.BlacklistSyncDelivery.id)).all()
        assert [blacklist.BlacklistCommand.decode(row.command).command for row in rows] == [
            blacklist.BlacklistCommandType.CREATE_RECORD,
            blacklist.BlacklistCommandType.EDIT_LIST,
            blacklist.BlacklistCommandType.EXPIRE_ALL,
        ]
        assert session.get(Blacklist, first).name == "changed"


def test_legacy_naive_expiration_is_utc_before_flush_and_serialization(database, existing_blacklist, monkeypatch):
    _record_id, first, _second = existing_blacklist
    monkeypatch.setattr(blacklist, "_get_set_player", lambda session, player_id: session.scalar(
        select(PlayerID).where(PlayerID.player_id == player_id)))
    naive = datetime(2035, 1, 2, 3, 4)
    result = blacklist.add_record_to_blacklist("synthetic-player", first, "temporary", expires_at=naive)
    assert result["expires_at"] == naive.replace(tzinfo=timezone.utc)
    assert result["is_active"] is True


def test_deleted_list_delivery_keeps_snapshot_after_source_is_gone(database, existing_blacklist):
    _record_id, first, _second = existing_blacklist
    assert blacklist.delete_blacklist(first)
    with database() as session:
        assert session.get(Blacklist, first) is None
        row = session.scalar(select(journal.BlacklistSyncDelivery))
        command = blacklist.BlacklistCommand.decode(row.command)
        assert command.command == blacklist.BlacklistCommandType.DELETE_LIST
        assert "synthetic-player" in command.payload["banned_players"]


def test_deleted_kick_only_steam_list_completes_without_game_action(database, existing_blacklist, monkeypatch):
    from rcon.types import GameEnum

    record_id, first, _ = existing_blacklist
    with database() as session, session.begin():
        record = session.get(BlacklistRecord, record_id)
        record.player.player_id = '76561198036685843'
        record.blacklist.sync = BlacklistSyncMethod.KICK_ONLY
    monkeypatch.setattr(blacklist, 'SERVER_NUMBER', 1)
    monkeypatch.setattr(blacklist, 'get_server_number_mask', lambda: 1)
    assert blacklist.delete_blacklist(first)
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = mock.Mock()
    receiver.rcon.game_profile.game = GameEnum.HLL_VIETNAM
    assert journal.process_one(1, receiver.dispatch) == 'done'
    with database() as session:
        row = session.scalar(select(journal.BlacklistSyncDelivery))
        assert row.status == 'done'
    receiver.rcon.get_detailed_player_info.assert_not_called()
    receiver.rcon.remove_temp_ban.assert_not_called()
    receiver.rcon.remove_perma_ban.assert_not_called()


@pytest.mark.parametrize("operation", ["create", "remove", "edit_list", "delete_list", "expire"])
def test_failed_journal_insert_rolls_back_all_mutations(database, existing_blacklist, monkeypatch, operation):
    record_id, first, _second = existing_blacklist
    def fail(*_args):
        raise RuntimeError("synthetic journal failure")
    monkeypatch.setattr(journal, "enqueue", fail)
    monkeypatch.setattr(blacklist, "_get_set_player", lambda session, player_id: session.scalar(
        select(PlayerID).where(PlayerID.player_id == player_id)))
    actions = {
        "create": lambda: blacklist.add_record_to_blacklist("synthetic-player", first, "new", admin_name="test"),
        "remove": lambda: blacklist.remove_record_from_blacklist(record_id),
        "edit_list": lambda: blacklist.edit_blacklist(first, name="changed"),
        "delete_list": lambda: blacklist.delete_blacklist(first),
        "expire": lambda: blacklist.expire_all_player_blacklists("synthetic-player"),
    }
    with pytest.raises(RuntimeError, match="synthetic journal failure"):
        actions[operation]()
    with database() as session:
        record = session.get(BlacklistRecord, record_id)
        assert record is not None and record.expires_at is None
        assert session.get(Blacklist, first).name == "first"
        assert len(session.scalars(select(BlacklistRecord)).all()) == 1
        assert session.scalars(select(journal.BlacklistSyncDelivery)).all() == []


def test_receiver_catches_up_after_being_offline_without_duplicate_action(database, existing_blacklist, monkeypatch):
    from unittest.mock import Mock

    record_id, first, _second = existing_blacklist
    with database() as session, session.begin():
        session.delete(session.get(BlacklistRecord, record_id))
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 1)
    monkeypatch.setattr(blacklist, "_get_set_player", lambda session, player_id: session.scalar(
        select(PlayerID).where(PlayerID.player_id == player_id)))
    monkeypatch.setattr(blacklist, "send_to_discord_audit", lambda **_: None)
    # Create the change while there is no subscriber or running receiver.
    blacklist.add_record_to_blacklist("synthetic-player", first, "reason", admin_name="tester")
    server = Mock()
    server.get_detailed_player_info.side_effect = blacklist.HLLCommandFailedError("offline")
    server.perma_ban.return_value = True
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = server
    assert journal.process_one(1, receiver.dispatch, is_ready=lambda: False) == "deferred"
    server.perma_ban.assert_not_called()
    assert journal.process_one(1, receiver.dispatch, is_ready=lambda: True) == "done"
    server.perma_ban.assert_called_once()
    # A restarted receiver sees the acknowledged event and does not repeat it.
    assert journal.process_one(1, receiver.dispatch) == "empty"
    server.perma_ban.assert_called_once()


def test_expired_queued_create_is_not_banned_after_reconnect(database, existing_blacklist, monkeypatch):
    record_id, _first, _second = existing_blacklist
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 1)
    with database() as session:
        record = session.get(BlacklistRecord, record_id)
        command = blacklist.BlacklistCommand(
            command=blacklist.BlacklistCommandType.CREATE_RECORD,
            server_mask=1,
            payload={"record_id": record_id, "player_id": record.player.player_id},
        )
        journal.enqueue(session, command.encode(), 1)
        session.commit()
    server = mock.Mock()
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = server
    assert journal.process_one(1, receiver.dispatch, is_ready=lambda: False) == "deferred"
    with database() as session, session.begin():
        session.get(BlacklistRecord, record_id).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    assert journal.process_one(1, receiver.dispatch, is_ready=lambda: True) == "done"
    server.perma_ban.assert_not_called()
    server.temp_ban.assert_not_called()


def test_offline_fourth_server_keeps_active_kick_only_record_until_ready(database, existing_blacklist, monkeypatch):
    record_id, first, _second = existing_blacklist
    with database() as session, session.begin():
        session.delete(session.get(BlacklistRecord, record_id))
        target = session.get(Blacklist, first)
        target.servers = 1 << 3
        target.sync = BlacklistSyncMethod.KICK_ONLY
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 4)
    monkeypatch.setattr(blacklist, "_get_set_player", lambda session, player_id: session.scalar(
        select(PlayerID).where(PlayerID.player_id == player_id)))
    blacklist.add_record_to_blacklist("synthetic-player", first, "reason", admin_name="tester")
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = mock.Mock()
    assert journal.process_one(4, receiver.dispatch, is_ready=lambda: False) == "deferred"
    receiver.rcon.kick.assert_not_called()
    with database() as session:
        row = session.scalar(select(journal.BlacklistSyncDelivery))
        assert row.server_number == 4 and row.status == "queued"
        assert session.scalar(select(BlacklistRecord)).is_expired() is None


def test_rejected_game_server_action_is_not_acknowledged(database, existing_blacklist, monkeypatch):
    from unittest.mock import Mock

    record_id, first, _second = existing_blacklist
    with database() as session, session.begin():
        session.delete(session.get(BlacklistRecord, record_id))
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 1)
    monkeypatch.setattr(blacklist, "_get_set_player", lambda session, player_id: session.scalar(
        select(PlayerID).where(PlayerID.player_id == player_id)))
    monkeypatch.setattr(blacklist, "send_to_discord_audit", lambda **_: None)
    blacklist.add_record_to_blacklist("synthetic-player", first, "reason", admin_name="tester")
    server = Mock()
    server.get_detailed_player_info.side_effect = blacklist.HLLCommandFailedError("offline")
    server.perma_ban.return_value = False
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = server
    assert journal.process_one(1, receiver.dispatch) == "review"
    assert journal.process_one(1, receiver.dispatch) == "review"
    server.perma_ban.assert_called_once()


def test_create_then_delete_while_receiver_offline_does_not_remove_unrelated_ban(database, existing_blacklist, monkeypatch):
    from unittest.mock import Mock

    record_id, first, _second = existing_blacklist
    with database() as session, session.begin():
        session.delete(session.get(BlacklistRecord, record_id))
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 1)
    monkeypatch.setattr(blacklist, "_get_set_player", lambda session, player_id: session.scalar(
        select(PlayerID).where(PlayerID.player_id == player_id)))
    monkeypatch.setattr(blacklist, "send_to_discord_audit", lambda **_: None)
    created = blacklist.add_record_to_blacklist("synthetic-player", first, "reason", admin_name="tester")
    blacklist.remove_record_from_blacklist(created["id"])
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = Mock()
    journal.process_one(1, receiver.dispatch)
    journal.process_one(1, receiver.dispatch)
    receiver.rcon.remove_perma_ban.assert_not_called()
    receiver.rcon.perma_ban.assert_not_called()


def test_create_edit_delete_while_offline_does_not_touch_unrelated_ban(database, existing_blacklist, monkeypatch):
    from unittest.mock import Mock

    record_id, first, _second = existing_blacklist
    with database() as session, session.begin():
        session.delete(session.get(BlacklistRecord, record_id))
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 1)
    monkeypatch.setattr(blacklist, "_get_set_player", lambda session, player_id: session.scalar(
        select(PlayerID).where(PlayerID.player_id == player_id)))
    monkeypatch.setattr(blacklist, "send_to_discord_audit", lambda **_: None)
    created = blacklist.add_record_to_blacklist("synthetic-player", first, "reason", admin_name="tester")
    blacklist.edit_record_from_blacklist(created["id"], reason="changed")
    blacklist.remove_record_from_blacklist(created["id"])
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = Mock()
    for _ in range(3):
        journal.process_one(1, receiver.dispatch)
    receiver.rcon.remove_perma_ban.assert_not_called()
    receiver.rcon.perma_ban.assert_not_called()


def test_interleaved_player_changes_do_not_remove_unrelated_ban(database, existing_blacklist, monkeypatch):
    from unittest.mock import Mock

    record_id, first, _second = existing_blacklist
    with database() as session, session.begin():
        session.delete(session.get(BlacklistRecord, record_id))
        session.add(PlayerID(player_id="second-synthetic-player"))
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 1)
    monkeypatch.setattr(blacklist, "_get_set_player", lambda session, player_id: session.scalar(
        select(PlayerID).where(PlayerID.player_id == player_id)))
    monkeypatch.setattr(blacklist, "send_to_discord_audit", lambda **_: None)
    created = blacklist.add_record_to_blacklist("synthetic-player", first, "reason", admin_name="tester")
    blacklist.add_record_to_blacklist("second-synthetic-player", first, "reason", admin_name="tester")
    blacklist.remove_record_from_blacklist(created["id"])
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = Mock()
    receiver.rcon.get_detailed_player_info.side_effect = blacklist.HLLCommandFailedError("offline")
    receiver.rcon.perma_ban.return_value = True
    for _ in range(3):
        journal.process_one(1, receiver.dispatch)
    receiver.rcon.remove_perma_ban.assert_not_called()
    assert receiver.rcon.perma_ban.call_count == 1
    assert receiver.rcon.perma_ban.call_args.kwargs["player_id"] == "second-synthetic-player"


def test_multiple_records_for_one_player_require_review_instead_of_stale_changes(database, existing_blacklist, monkeypatch):
    from unittest.mock import Mock

    record_id, first, second = existing_blacklist
    with database() as session, session.begin():
        session.delete(session.get(BlacklistRecord, record_id))
        session.get(Blacklist, second).servers = 1
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 1)
    monkeypatch.setattr(blacklist, "_get_set_player", lambda session, player_id: session.scalar(
        select(PlayerID).where(PlayerID.player_id == player_id)))
    monkeypatch.setattr(blacklist, "send_to_discord_audit", lambda **_: None)
    permanent = blacklist.add_record_to_blacklist("synthetic-player", first, "permanent", admin_name="tester")
    blacklist.add_record_to_blacklist("synthetic-player", second, "temporary",
        expires_at=datetime.now(timezone.utc) + timedelta(hours=3), admin_name="tester")
    blacklist.remove_record_from_blacklist(permanent["id"])
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = Mock()
    receiver.rcon.get_detailed_player_info.side_effect = blacklist.HLLCommandFailedError("offline")
    receiver.rcon.temp_ban.return_value = True
    receiver.rcon.remove_perma_ban.return_value = True
    assert journal.process_one(1, receiver.dispatch) == "review"
    receiver.rcon.remove_perma_ban.assert_not_called()
    receiver.rcon.temp_ban.assert_not_called()
    assert journal.list_reviews(1)["total"] == 3


def test_list_wide_change_interleaved_with_record_change_requires_review(database, existing_blacklist, monkeypatch):
    record_id, first, _second = existing_blacklist
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 1)
    blacklist.edit_record_from_blacklist(record_id, reason="changed")
    blacklist.edit_blacklist(first, name="new name")
    assert journal.process_one(1, lambda _: pytest.fail("must not execute stale changes")) == "review"
    result = journal.list_reviews(1)
    assert result["total"] == 2
