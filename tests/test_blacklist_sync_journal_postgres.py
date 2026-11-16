"""Exercise durable delivery with a disposable PostgreSQL schema and fake RCON."""
import os
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
from threading import Event
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
    assert journal.process_one(1, receiver.dispatch) == "done"
    server.perma_ban.assert_called_once()
    # A restarted receiver sees the acknowledged event and does not repeat it.
    assert journal.process_one(1, receiver.dispatch) == "empty"
    server.perma_ban.assert_called_once()


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
