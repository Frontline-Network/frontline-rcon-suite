from types import SimpleNamespace
from unittest.mock import Mock
from datetime import datetime, timedelta, timezone
from contextlib import contextmanager
from contextlib import nullcontext

import pytest
from rcon import blacklist
from rcon.models import Blacklist, BlacklistRecord, PlayerID, PlayerName
from rcon.types import BlacklistSyncMethod
from sqlalchemy import create_engine
from sqlalchemy.orm import Session


@pytest.fixture(autouse=True)
def fake_blacklist_guard(monkeypatch):
    pending = {}

    def reserve(server, player, rules, action):
        if player in pending or '*' in pending:
            return None
        pending[player] = 'synthetic-token'
        return 'synthetic-token'

    def finish(server, player, token, result, *, expected):
        assert pending[player] == token
        del pending[player]
        return 1

    monkeypatch.setattr(blacklist, 'lock', lambda _key: nullcontext())
    monkeypatch.setattr(blacklist.action_guard, 'reserve', reserve)
    monkeypatch.setattr(blacklist.action_guard, 'finish', finish)
    monkeypatch.setattr(blacklist.action_guard, 'pending_players', lambda *_args: set(pending))
    return pending


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
    monkeypatch.setattr(blacklist, "_blacklist_remaining_hours", lambda _: 1)
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


@pytest.mark.parametrize("state", [blacklist.BanState.NONE, blacklist.BanState.TEMP])
@pytest.mark.parametrize("naive", [False, True])
def test_expired_record_never_creates_kick_or_ban(monkeypatch, fake_blacklist_guard, state, naive):
    expires = datetime.now(timezone.utc) - timedelta(seconds=1)
    if naive:
        expires = expires.replace(tzinfo=None)
    record = SimpleNamespace(expires_at=expires)
    server = Mock()
    monkeypatch.setattr(blacklist, "get_ban_state_from_record", lambda _: state)
    assert blacklist.apply_blacklist_punishment(server, record, player_id="synthetic") is blacklist._BLACKLIST_ACTION_EXPIRED
    server.kick.assert_not_called()
    server.temp_ban.assert_not_called()
    server.perma_ban.assert_not_called()
    assert fake_blacklist_guard == {}


def test_record_expiring_during_reservation_does_not_send(monkeypatch, fake_blacklist_guard):
    record = SimpleNamespace(expires_at=datetime.now(timezone.utc) + timedelta(hours=1))
    server = Mock()
    monkeypatch.setattr(blacklist, "get_ban_state_from_record", lambda _: blacklist.BanState.TEMP)
    original_reserve = blacklist.action_guard.reserve

    def expire_during_reservation(*args, **kwargs):
        token = original_reserve(*args, **kwargs)
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        return token

    monkeypatch.setattr(blacklist.action_guard, "reserve", expire_during_reservation)
    assert blacklist.apply_blacklist_punishment(server, record, player_id="synthetic") is blacklist._BLACKLIST_ACTION_EXPIRED
    server.kick.assert_not_called()
    server.temp_ban.assert_not_called()
    server.perma_ban.assert_not_called()
    assert fake_blacklist_guard == {}


@pytest.mark.parametrize("naive", [False, True])
def test_live_temporary_blacklist_record_accepts_legacy_utc_expiry(monkeypatch, naive):
    expires = datetime.now(timezone.utc) + timedelta(hours=2)
    if naive:
        expires = expires.replace(tzinfo=None)
    record = SimpleNamespace(admin_name="tester", expires_at=expires,
                             get_formatted_reason=lambda: "reason")
    server = Mock()
    server.temp_ban.return_value = True
    monkeypatch.setattr(blacklist, "get_ban_state_from_record", lambda _: blacklist.BanState.TEMP)
    monkeypatch.setattr(blacklist, "send_to_discord_audit", Mock())
    assert blacklist.apply_blacklist_punishment(server, record, player_id="synthetic", player_name="test") is True
    assert server.temp_ban.call_args.kwargs["duration_hours"] == 1


@pytest.mark.parametrize('sync', list(BlacklistSyncMethod))
def test_short_temporary_record_kicks_online_in_every_sync_mode(monkeypatch, sync):
    record = BlacklistRecord(admin_name='test', expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
                             blacklist=Blacklist(name='test', sync=sync))
    monkeypatch.setattr(record, 'get_formatted_reason', lambda: 'reason')
    server = Mock()
    server.kick.return_value = True
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', Mock())
    assert blacklist.apply_blacklist_punishment(server, record, player_id='id', player_name='name') is True
    server.kick.assert_called_once()
    server.temp_ban.assert_not_called()


@pytest.mark.parametrize('sync', [BlacklistSyncMethod.BAN_IMMEDIATELY, BlacklistSyncMethod.BAN_ON_CONNECT])
def test_short_ban_offline_is_deferred_and_never_removes_unrelated_ban(monkeypatch, sync):
    record = BlacklistRecord(admin_name='test', expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
                             blacklist=Blacklist(name='test', sync=sync))
    server = Mock()
    server.get_temp_bans.return_value = []
    server.get_perma_bans.return_value = []
    server.get_detailed_player_info.side_effect = blacklist.HLLCommandFailedError('offline')
    blacklist.synchronize_ban(server, 'id', record, blacklist.BanState.TEMP)
    server.kick.assert_not_called()
    server.temp_ban.assert_not_called()
    server.remove_temp_ban.assert_not_called()


@pytest.mark.parametrize('existing', ['temporary', 'permanent'])
@pytest.mark.parametrize('minutes', [30, 90])
def test_temporary_restriction_does_not_remove_or_overwrite_unattributed_ban(existing, minutes):
    record = BlacklistRecord(admin_name='test', expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
                             blacklist=Blacklist(name='test', sync=BlacklistSyncMethod.BAN_IMMEDIATELY))
    server = Mock()
    server.get_temp_bans.return_value = [{'player_id': 'id'}] if existing == 'temporary' else []
    server.get_perma_bans.return_value = [{'player_id': 'id'}] if existing == 'permanent' else []
    with pytest.raises(blacklist.BlacklistBanOwnershipUnverified):
        blacklist.synchronize_ban(server, 'id', record, blacklist.BanState.PERMA)
    server.remove_temp_ban.assert_not_called()
    server.remove_perma_ban.assert_not_called()
    server.temp_ban.assert_not_called()
    server.kick.assert_not_called()


def test_stale_previous_ban_status_does_not_prevent_new_temporary_sanction(monkeypatch):
    record = BlacklistRecord(admin_name='test', expires_at=datetime.now(timezone.utc) + timedelta(minutes=90),
                             blacklist=Blacklist(name='test', sync=BlacklistSyncMethod.BAN_IMMEDIATELY))
    monkeypatch.setattr(record, 'get_formatted_reason', lambda: 'reason')
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', Mock())
    server = Mock()
    server.get_temp_bans.return_value = []
    server.get_perma_bans.return_value = []
    server.get_detailed_player_info.return_value = {'name': 'test'}
    server.temp_ban.return_value = True
    blacklist.synchronize_ban(server, 'id', record, blacklist.BanState.PERMA)
    server.remove_perma_ban.assert_not_called()
    server.temp_ban.assert_called_once()


def test_expired_new_temporary_restriction_does_not_query_or_remove_bans():
    record = BlacklistRecord(admin_name='test', expires_at=datetime.now(timezone.utc) - timedelta(minutes=1),
                             blacklist=Blacklist(name='test', sync=BlacklistSyncMethod.BAN_ON_CONNECT))
    server = Mock()
    blacklist.synchronize_ban(server, 'id', record, blacklist.BanState.PERMA)
    server.assert_not_called()
    server.get_temp_bans.assert_not_called()
    server.remove_perma_ban.assert_not_called()


def test_expiry_during_fresh_ban_lookup_skips_review_and_all_actions():
    record = BlacklistRecord(admin_name='test', expires_at=datetime.now(timezone.utc) + timedelta(minutes=20),
                             blacklist=Blacklist(name='test', sync=BlacklistSyncMethod.BAN_IMMEDIATELY))
    server = Mock()
    def expires_while_reading():
        record.expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
        return [{'player_id': 'id'}]
    server.get_temp_bans.side_effect = expires_while_reading
    blacklist.synchronize_ban(server, 'id', record, blacklist.BanState.PERMA)
    server.get_perma_bans.assert_not_called()
    server.remove_perma_ban.assert_not_called()
    server.kick.assert_not_called()


def test_existing_eos_ban_matches_case_insensitively():
    record = BlacklistRecord(admin_name='test', expires_at=datetime.now(timezone.utc) + timedelta(minutes=30),
                             blacklist=Blacklist(name='test', sync=BlacklistSyncMethod.BAN_IMMEDIATELY))
    server = Mock()
    server.get_temp_bans.return_value = [{'player_id': 'a' * 32}]
    with pytest.raises(blacklist.BlacklistBanOwnershipUnverified):
        blacklist.synchronize_ban(server, 'A' * 32, record, blacklist.BanState.NONE)
    server.kick.assert_not_called()


@pytest.mark.parametrize('minutes, expected', [(61, 1), (119, 1), (121, 2), (179, 2)])
def test_temporary_list_ban_rounds_down(monkeypatch, minutes, expected):
    record = BlacklistRecord(admin_name='test', expires_at=datetime.now(timezone.utc) + timedelta(minutes=minutes),
                             blacklist=Blacklist(name='test', sync=BlacklistSyncMethod.BAN_IMMEDIATELY))
    monkeypatch.setattr(record, 'get_formatted_reason', lambda: 'reason')
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', Mock())
    server = Mock()
    server.temp_ban.return_value = True
    assert blacklist.apply_blacklist_punishment(server, record, player_id='id', player_name='name') is True
    assert server.temp_ban.call_args.kwargs['duration_hours'] == expected
    server.kick.assert_not_called()


def test_crossing_hour_boundary_reserves_kick_instead_of_ban(monkeypatch):
    record = BlacklistRecord(admin_name='test', expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
                             blacklist=Blacklist(name='test', sync=BlacklistSyncMethod.BAN_IMMEDIATELY))
    monkeypatch.setattr(record, 'get_formatted_reason', lambda: 'reason')
    server = Mock()
    server.kick.return_value = True
    actions = []
    reserve = blacklist.action_guard.reserve
    def crosses_boundary(*args):
        actions.append(args[-1])
        token = reserve(*args)
        if args[-1] == 'ban':
            record.expires_at = datetime.now(timezone.utc) + timedelta(minutes=30)
        return token
    monkeypatch.setattr(blacklist.action_guard, 'reserve', crosses_boundary)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', Mock())
    assert blacklist.apply_blacklist_punishment(server, record, player_id='id', player_name='name') is True
    assert actions == ['ban', 'kick']
    server.kick.assert_called_once()
    server.temp_ban.assert_not_called()


@pytest.mark.parametrize('remaining_hours', [[-1], [1, -1]])
def test_negative_remaining_time_never_becomes_kick(monkeypatch, remaining_hours):
    record = BlacklistRecord(admin_name='test', expires_at=datetime.now(timezone.utc) + timedelta(hours=2),
                             blacklist=Blacklist(name='test', sync=BlacklistSyncMethod.BAN_IMMEDIATELY))
    monkeypatch.setattr(record, 'get_formatted_reason', lambda: 'reason')
    monkeypatch.setattr(blacklist, '_blacklist_remaining_hours', Mock(side_effect=remaining_hours))
    server = Mock()
    assert blacklist.apply_blacklist_punishment(server, record, player_id='id', player_name='name') is blacklist._BLACKLIST_ACTION_EXPIRED
    server.kick.assert_not_called()
    server.temp_ban.assert_not_called()


@pytest.mark.parametrize('result', [None, TimeoutError('synthetic lost response')])
def test_uncertain_blacklist_action_blocks_later_attempts(monkeypatch, fake_blacklist_guard, result):
    record = SimpleNamespace(admin_name='tester', expires_at=None, get_formatted_reason=lambda: 'reason')
    server = Mock()
    if isinstance(result, Exception):
        server.perma_ban.side_effect = result
    else:
        server.perma_ban.return_value = result
    monkeypatch.setattr(blacklist, 'get_ban_state_from_record', lambda _: blacklist.BanState.PERMA)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', Mock())
    assert blacklist.apply_blacklist_punishment(server, record, player_id='synthetic', player_name='name') is False
    assert blacklist.apply_blacklist_punishment(server, record, player_id='synthetic', player_name='name') is False
    server.perma_ban.assert_called_once()
    assert fake_blacklist_guard == {'synthetic': 'synthetic-token'}


def test_rejected_blacklist_action_can_be_retried(monkeypatch, fake_blacklist_guard):
    record = SimpleNamespace(admin_name='tester', expires_at=None, get_formatted_reason=lambda: 'reason')
    server = Mock()
    server.perma_ban.return_value = False
    monkeypatch.setattr(blacklist, 'get_ban_state_from_record', lambda _: blacklist.BanState.PERMA)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', Mock())
    assert blacklist.apply_blacklist_punishment(server, record, player_id='synthetic', player_name='name') is False
    assert blacklist.apply_blacklist_punishment(server, record, player_id='synthetic', player_name='name') is False
    assert server.perma_ban.call_count == 2 and fake_blacklist_guard == {}


def test_pending_blacklist_action_blocks_synchronization_removal(fake_blacklist_guard):
    fake_blacklist_guard['synthetic'] = 'synthetic-token'
    server = Mock()
    with pytest.raises(RuntimeError, match='awaits review'):
        blacklist.synchronize_ban(server, 'synthetic', None, blacklist.BanState.PERMA)
    server.remove_perma_ban.assert_not_called()


@pytest.mark.parametrize('pending_player', ['synthetic', '*'])
def test_expire_all_does_not_remove_bans_while_review_is_pending(fake_blacklist_guard, pending_player):
    fake_blacklist_guard[pending_player] = 'synthetic-token'
    server = Mock()
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = server
    with pytest.raises(RuntimeError, match='awaits review'):
        handler.handle_expire_all(SimpleNamespace(player_id='synthetic'))
    server.get_temp_bans.assert_not_called()
    server.get_perma_bans.assert_not_called()
    server.remove_temp_ban.assert_not_called()
    server.remove_perma_ban.assert_not_called()


def test_expire_all_fails_closed_if_guard_database_is_unavailable(monkeypatch):
    monkeypatch.setattr(blacklist.action_guard, 'pending_players', Mock(side_effect=RuntimeError('database offline')))
    server = Mock()
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = server
    with pytest.raises(RuntimeError, match='database offline'):
        handler.handle_expire_all(SimpleNamespace(player_id='synthetic'))
    server.assert_not_called()


def test_expire_all_proceeds_for_an_unrelated_player(fake_blacklist_guard):
    fake_blacklist_guard['other-player'] = 'synthetic-token'
    server = Mock()
    server.get_temp_bans.return_value = [{'player_id': 'synthetic'}]
    server.get_perma_bans.return_value = [{'player_id': 'synthetic'}]
    server.remove_temp_ban.return_value = True
    server.remove_perma_ban.return_value = True
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = server
    handler.handle_expire_all(SimpleNamespace(player_id='synthetic'))
    server.remove_temp_ban.assert_called_once_with('synthetic')
    server.remove_perma_ban.assert_called_once_with('synthetic')


@pytest.mark.parametrize('result', [None, '', 1, False])
def test_expire_all_stops_after_unconfirmed_temporary_unban(result):
    server = Mock()
    server.get_temp_bans.return_value = [{'player_id': 'synthetic'}]
    server.get_perma_bans.return_value = [{'player_id': 'synthetic'}]
    server.remove_temp_ban.return_value = result
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = server
    with pytest.raises(RuntimeError):
        handler.handle_expire_all(SimpleNamespace(player_id='synthetic'))
    server.remove_temp_ban.assert_called_once_with('synthetic')
    server.get_perma_bans.assert_not_called()
    server.remove_perma_ban.assert_not_called()


@pytest.mark.parametrize('result', [None, '', 1, False])
def test_expire_all_does_not_confirm_unconfirmed_permanent_unban(result):
    server = Mock()
    server.get_temp_bans.return_value = []
    server.get_perma_bans.return_value = [{'player_id': 'synthetic'}]
    server.remove_perma_ban.return_value = result
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = server
    with pytest.raises(RuntimeError):
        handler.handle_expire_all(SimpleNamespace(player_id='synthetic'))
    server.remove_perma_ban.assert_called_once_with('synthetic')


@pytest.mark.parametrize('old_state,method', [
    (blacklist.BanState.TEMP, 'remove_temp_ban'),
    (blacklist.BanState.PERMA, 'remove_perma_ban'),
])
@pytest.mark.parametrize('result', [None, '', 1, False])
def test_sync_does_not_continue_after_unconfirmed_unban(monkeypatch, old_state, method, result):
    server = Mock()
    getattr(server, method).return_value = result
    record = SimpleNamespace(blacklist=SimpleNamespace(sync=BlacklistSyncMethod.BAN_IMMEDIATELY))
    monkeypatch.setattr(blacklist, 'get_ban_state_from_record', lambda _: blacklist.BanState.NONE)
    with pytest.raises(RuntimeError):
        blacklist.synchronize_ban(server, 'synthetic', record, old_state)
    getattr(server, method).assert_called_once_with('synthetic')
    server.get_detailed_player_info.assert_not_called()
    server.kick.assert_not_called()
    server.temp_ban.assert_not_called()
    server.perma_ban.assert_not_called()


def test_confirmed_action_with_failed_finalization_is_not_resent(monkeypatch, fake_blacklist_guard):
    record = SimpleNamespace(admin_name='tester', expires_at=None, get_formatted_reason=lambda: 'reason')
    server = Mock()
    server.perma_ban.return_value = True
    monkeypatch.setattr(blacklist, 'get_ban_state_from_record', lambda _: blacklist.BanState.PERMA)
    monkeypatch.setattr(blacklist, 'send_to_discord_audit', Mock())
    monkeypatch.setattr(blacklist.action_guard, 'finish', Mock(side_effect=RuntimeError('database unavailable')))
    assert blacklist.apply_blacklist_punishment(server, record, player_id='synthetic', player_name='name') is True
    assert blacklist.apply_blacklist_punishment(server, record, player_id='synthetic', player_name='name') is False
    server.perma_ban.assert_called_once()
    assert fake_blacklist_guard == {'synthetic': 'synthetic-token'}


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
    monkeypatch.setattr(blacklist, "blacklist_change_session", session)
    monkeypatch.setattr(blacklist, "is_player_blacklisted", lambda *_args, **_kwargs: None)
    blacklist.BlacklistCommandHandler.handle_edit_record(SimpleNamespace(rcon=server), SimpleNamespace(old_record=old))
    server.remove_perma_ban.assert_not_called()


def test_synchronize_no_ban_and_no_record_is_noop():
    server = Mock()
    blacklist.synchronize_ban(server, "id", None, blacklist.BanState.NONE)
    server.assert_not_called()


def test_uncertain_blacklist_commit_does_not_trigger_fallback_ban(monkeypatch):
    server = Mock()
    monkeypatch.setattr(blacklist, "add_record_to_blacklist", Mock(side_effect=TimeoutError("lost commit reply")))
    with pytest.raises(TimeoutError):
        blacklist.blacklist_or_ban(server, 1, "fake-id", "reason")
    server.perma_ban.assert_not_called()
    server.temp_ban.assert_not_called()


def test_blacklist_expiration_normalizes_legacy_naive_utc():
    naive = datetime(2026, 1, 2, 3, 4, 5)
    assert blacklist.normalize_blacklist_expiry(naive) == naive.replace(tzinfo=timezone.utc)
    local = datetime(2026, 1, 2, 4, 4, 5, tzinfo=timezone(timedelta(hours=1)))
    assert blacklist.normalize_blacklist_expiry(local) == naive.replace(tzinfo=timezone.utc)


def test_moved_record_does_not_assume_old_ban_on_new_server(monkeypatch):
    @contextmanager
    def session():
        yield object()
    old = {"id": 5, "player_id": "id", "blacklist": {"servers": [1], "sync": BlacklistSyncMethod.BAN_IMMEDIATELY}, "expires_at": None}
    new = SimpleNamespace(id=5)
    sync = Mock()
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 2)
    monkeypatch.setattr(blacklist, "blacklist_change_session", session)
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
    monkeypatch.setattr(blacklist, "blacklist_change_session", session)
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
    monkeypatch.setattr(blacklist, "blacklist_change_session", session)
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
    monkeypatch.setattr(blacklist, "blacklist_change_session", session)
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
    monkeypatch.setattr(blacklist, "blacklist_change_session", session)
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
    monkeypatch.setattr(blacklist, "blacklist_change_session", session)
    def commit(session, command):
        send(command)
        session.commit()
    monkeypatch.setattr(blacklist, "commit_blacklist_change", commit)
    blacklist.edit_record_from_blacklist(record_id, blacklist_id=second_id)
    assert send.call_args.args[0].server_mask == 3

def test_blacklist_receiver_probes_game_server_without_taking_actions():
    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = Mock()
    receiver.rcon.get_gamestate.side_effect = [ConnectionRefusedError(), None, {}, {"current_map": {}}]
    assert receiver._game_server_ready() is False
    assert receiver._game_server_ready() is False
    assert receiver._game_server_ready() is False
    assert receiver._game_server_ready() is True
    receiver.rcon.kick.assert_not_called()
    receiver.rcon.temp_ban.assert_not_called()
    receiver.rcon.perma_ban.assert_not_called()


def test_blacklist_receiver_passes_readiness_probe_to_durable_journal(monkeypatch):
    from threading import Event
    from rcon import blacklist_sync_journal

    receiver = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    receiver.rcon = Mock()
    receiver.pubsub = Mock()
    stop = Event()
    receiver.pubsub.get_message.side_effect = lambda **_: stop.set()
    process = Mock()
    monkeypatch.setattr(blacklist_sync_journal, 'process_one', process)
    receiver.run(stop)
    process.assert_called_once_with(blacklist.SERVER_NUMBER, receiver.dispatch,
                                    is_ready=receiver._game_server_ready,
                                    prepare=receiver._prepare_delivery)
    receiver.pubsub.close.assert_called_once()
