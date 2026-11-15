from types import SimpleNamespace
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager

import pytest
from rcon import blacklist
from rcon.models import Blacklist, BlacklistRecord, PlayerID, PlayerName
from rcon.types import BlacklistSyncMethod
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.mark.parametrize("state,method", [
    (blacklist.BanState.NONE, "kick"),
    (blacklist.BanState.TEMP, "temp_ban"),
    (blacklist.BanState.PERMA, "perma_ban"),
])
@pytest.mark.parametrize("accepted", [False, True])
def test_blacklist_reports_server_result(monkeypatch, state, method, accepted):
    record = SimpleNamespace(admin_name="tester", expires_at=None, get_formatted_reason=lambda: "reason")
    server = Mock()
    getattr(server, method).return_value = accepted
    audit = Mock()
    monkeypatch.setattr(blacklist, "get_ban_state_from_record", lambda _: state)
    monkeypatch.setattr(blacklist, "round_timedelta_to_hours", lambda _: 1)
    monkeypatch.setattr(blacklist, "send_to_discord_audit", audit)
    result = blacklist.apply_blacklist_punishment(server, record, player_id="id", player_name="name")
    assert result is accepted
    assert audit.call_args.kwargs["by"] == ("BLACKLIST" if accepted else "ERROR")


def test_offline_ban_without_saved_name_uses_player_id(monkeypatch):
    record = SimpleNamespace(
        admin_name="tester", player=SimpleNamespace(player_id="id", names=[]),
        get_formatted_reason=lambda: "reason",
    )
    server = Mock()
    server.perma_ban.return_value = True
    monkeypatch.setattr(blacklist, "get_ban_state_from_record", lambda _: blacklist.BanState.PERMA)
    monkeypatch.setattr(blacklist, "send_to_discord_audit", Mock())
    assert blacklist.apply_blacklist_punishment(server, record) is True
    assert server.perma_ban.call_args.kwargs["player_id"] == "id"


@pytest.mark.parametrize("reason", ["Evidence {", "Evidence }", "{player_id.no_such_attribute}"])
def test_invalid_stored_reason_does_not_prevent_enforcement_or_listing(monkeypatch, reason):
    player = PlayerID(player_id="id")
    record = BlacklistRecord(
        id=1, player=player, blacklist=Blacklist(name="test", sync=BlacklistSyncMethod.BAN_IMMEDIATELY),
        reason=reason, admin_name="tester", created_at=datetime.now(timezone.utc),
    )
    server = Mock()
    server.perma_ban.return_value = True
    monkeypatch.setattr(blacklist, "send_to_discord_audit", Mock())
    assert blacklist.apply_blacklist_punishment(server, record, player_name="name") is True
    assert server.perma_ban.call_args.kwargs["reason"] == reason
    assert record.to_dict(with_blacklist=False, with_player=True)["formatted_reason"] == reason


def test_edit_does_not_remove_ban_on_server_outside_old_list(monkeypatch):
    @contextmanager
    def session():
        yield object()
    server = Mock()
    old = {"player_id": "id", "blacklist": {"servers": [1], "sync": BlacklistSyncMethod.BAN_IMMEDIATELY}, "expires_at": None}
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 2)
    monkeypatch.setattr(blacklist, "enter_session", session)
    monkeypatch.setattr(blacklist, "is_player_blacklisted", lambda *_args, **_kwargs: None)
    blacklist.BlacklistCommandHandler.handle_edit_record(SimpleNamespace(rcon=server), SimpleNamespace(old_record=old))
    server.remove_perma_ban.assert_not_called()


def test_synchronize_no_ban_and_no_record_is_noop():
    server = Mock()
    blacklist.synchronize_ban(server, "id", None, blacklist.BanState.NONE)
    server.assert_not_called()


def test_moved_record_does_not_assume_old_ban_on_new_server(monkeypatch):
    @contextmanager
    def session():
        yield object()
    old = {"id": 5, "player_id": "id", "blacklist": {"servers": [1], "sync": BlacklistSyncMethod.BAN_IMMEDIATELY}, "expires_at": None}
    new = SimpleNamespace(id=5)
    sync = Mock()
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 2)
    monkeypatch.setattr(blacklist, "enter_session", session)
    monkeypatch.setattr(blacklist, "is_player_blacklisted", lambda *_args, **_kwargs: new)
    monkeypatch.setattr(blacklist, "synchronize_ban", sync)
    blacklist.BlacklistCommandHandler.handle_edit_record(SimpleNamespace(rcon=Mock()), SimpleNamespace(old_record=old))
    assert sync.call_args.kwargs["old_state"] == blacklist.BanState.NONE


def test_editing_one_list_keeps_higher_priority_ban_on_another(monkeypatch):
    @contextmanager
    def session():
        yield object()
    now = datetime.now(timezone.utc)
    player = SimpleNamespace(player_id="id")
    edited = SimpleNamespace(id=1, blacklist_id=10, player=player, created_at=now - timedelta(minutes=1), expires_at=None)
    other = SimpleNamespace(id=2, blacklist_id=20, player=player, created_at=now, expires_at=None, blacklist=SimpleNamespace(sync=BlacklistSyncMethod.BAN_IMMEDIATELY))
    old = {"id": 10, "servers": None, "sync": BlacklistSyncMethod.BAN_IMMEDIATELY}
    new = {"id": 10, "servers": None, "sync": BlacklistSyncMethod.KICK_ONLY}
    sync = Mock()
    monkeypatch.setattr(blacklist, "enter_session", session)
    monkeypatch.setattr(blacklist, "get_active_blacklist_records", lambda *_: [edited])
    monkeypatch.setattr(blacklist, "get_player_blacklist_records", lambda *_args, **_kwargs: [other])
    monkeypatch.setattr(blacklist, "synchronize_ban", sync)
    blacklist.BlacklistCommandHandler.handle_edit_list(SimpleNamespace(rcon=Mock()), SimpleNamespace(old_blacklist=old, new_blacklist=new))
    sync.assert_not_called()


@pytest.mark.parametrize("current_id, should_sync", [(1, True), (2, False)])
def test_enabling_immediate_bans_syncs_only_current_priority(monkeypatch, current_id, should_sync):
    @contextmanager
    def session():
        yield object()
    record = SimpleNamespace(id=1, player=SimpleNamespace(player_id="id"))
    old = {"id": 10, "servers": None, "sync": BlacklistSyncMethod.BAN_ON_CONNECT}
    new = {"id": 10, "servers": None, "sync": BlacklistSyncMethod.BAN_IMMEDIATELY}
    sync = Mock()
    monkeypatch.setattr(blacklist, "enter_session", session)
    monkeypatch.setattr(blacklist, "get_active_blacklist_records", lambda *_: [record])
    monkeypatch.setattr(blacklist, "is_player_blacklisted", lambda *_args: SimpleNamespace(id=current_id))
    monkeypatch.setattr(blacklist, "get_ban_state_from_record", lambda _: blacklist.BanState.PERMA)
    monkeypatch.setattr(blacklist, "synchronize_ban", sync)
    blacklist.BlacklistCommandHandler.handle_edit_list(SimpleNamespace(rcon=Mock()), SimpleNamespace(old_blacklist=old, new_blacklist=new))
    assert sync.call_count == int(should_sync)


def test_editing_higher_priority_list_reconciles_remaining_ban(monkeypatch):
    @contextmanager
    def session():
        yield object()
    now = datetime.now(timezone.utc)
    player = SimpleNamespace(player_id="id")
    edited = SimpleNamespace(id=1, blacklist_id=10, player=player, created_at=now, expires_at=None)
    other = SimpleNamespace(id=2, blacklist_id=20, player=player, created_at=now, expires_at=now + timedelta(days=1), blacklist=SimpleNamespace(sync=BlacklistSyncMethod.BAN_IMMEDIATELY))
    old = {"id": 10, "servers": None, "sync": BlacklistSyncMethod.BAN_IMMEDIATELY}
    new = {"id": 10, "servers": None, "sync": BlacklistSyncMethod.KICK_ONLY}
    sync = Mock()
    monkeypatch.setattr(blacklist, "enter_session", session)
    monkeypatch.setattr(blacklist, "get_active_blacklist_records", lambda *_: [edited])
    monkeypatch.setattr(blacklist, "get_player_blacklist_records", lambda *_args, **_kwargs: [other])
    monkeypatch.setattr(blacklist, "synchronize_ban", sync)
    blacklist.BlacklistCommandHandler.handle_edit_list(SimpleNamespace(rcon=Mock()), SimpleNamespace(old_blacklist=old, new_blacklist=new))
    assert sync.call_args.kwargs["new_record"] is other
    assert sync.call_args.kwargs["old_state"] == blacklist.BanState.PERMA


def test_edit_overlapping_lists_uses_current_database_state(monkeypatch):
    engine = create_engine("sqlite://")
    for model in (PlayerID, Blacklist, BlacklistRecord):
        model.__table__.create(engine)
    now = datetime.now(timezone.utc)
    with Session(engine) as sess:
        player = PlayerID(player_id="id", created=now)
        edited = Blacklist(name="edited", sync=BlacklistSyncMethod.KICK_ONLY)
        other = Blacklist(name="other", sync=BlacklistSyncMethod.BAN_IMMEDIATELY)
        sess.add_all([player, edited, other])
        sess.flush()
        edited_id = edited.id
        sess.add_all([
            BlacklistRecord(player_id_id=player.id, blacklist_id=edited.id, reason="test", admin_name="test", created_at=now-timedelta(minutes=1)),
            BlacklistRecord(player_id_id=player.id, blacklist_id=other.id, reason="test", admin_name="test", created_at=now),
        ])
        sess.commit()
    @contextmanager
    def session():
        with Session(engine) as sess:
            yield sess
    monkeypatch.setattr(blacklist, "enter_session", session)
    server = Mock()
    old = {"id": edited_id, "servers": None, "sync": BlacklistSyncMethod.BAN_IMMEDIATELY}
    new = {"id": edited_id, "servers": None, "sync": BlacklistSyncMethod.KICK_ONLY}
    blacklist.BlacklistCommandHandler.handle_edit_list(SimpleNamespace(rcon=server), SimpleNamespace(old_blacklist=old, new_blacklist=new))
    server.remove_perma_ban.assert_not_called()


def test_moving_record_notifies_both_server_masks(monkeypatch):
    engine = create_engine("sqlite://")
    for model in (PlayerID, PlayerName, Blacklist, BlacklistRecord):
        model.__table__.create(engine)
    with Session(engine) as sess:
        player = PlayerID(player_id="id", created=datetime.now())
        first = Blacklist(name="first", sync=BlacklistSyncMethod.BAN_IMMEDIATELY, servers=1)
        second = Blacklist(name="second", sync=BlacklistSyncMethod.BAN_IMMEDIATELY, servers=2)
        sess.add_all([player, first, second])
        sess.flush()
        record = BlacklistRecord(player_id_id=player.id, blacklist_id=first.id, reason="test", admin_name="test", created_at=datetime.now(timezone.utc))
        sess.add(record)
        sess.commit()
        record_id, second_id = record.id, second.id
    @contextmanager
    def session():
        with Session(engine) as sess:
            yield sess
    send = Mock()
    monkeypatch.setattr(blacklist, "enter_session", session)
    monkeypatch.setattr(blacklist.BlacklistCommandHandler, "send", send)
    blacklist.edit_record_from_blacklist(record_id, blacklist_id=second_id)
    assert send.call_args.args[0].server_mask == 3
