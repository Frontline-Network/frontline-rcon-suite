from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from rcon import blacklist
from rcon.barricade_hllv_identity import prepare_online_steam_identity
from rcon.types import BlacklistSyncMethod, GameEnum
from rcon.game.hllv.player_adapter import HLLVPlayerInfoAdapter
from rcon.game.player_adapter import PlayerResponseAdapterError
from rcon.rcon import Rcon

STEAM = '76561198036685843'
EOS = '0123456789abcdef0123456789abcdef'


def api_with_players(players):
    api = Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = players
    api.get_detailed_player_info.return_value = {
        'player_id': EOS, 'eos_id': EOS, 'steam_id': STEAM,
        'platform': 'EPlatformFamily::Steam', 'name': 'synthetic',
    }
    return api


def row(eos=EOS, platform='EPlatformFamily::Steam', steam=STEAM):
    return {'iD': eos, 'eosId': eos, 'steamId': steam, 'platform': platform}


def record(sync=BlacklistSyncMethod.KICK_ONLY, expires=None, created=None, record_id=1):
    return SimpleNamespace(id=record_id, blacklist=SimpleNamespace(sync=sync),
                           expires_at=expires, created_at=created or datetime.now(timezone.utc))


def test_preparation_uses_fresh_verified_steam_eos_and_ignores_console():
    api = api_with_players([row(platform='EPlatformFamily::Xbox', steam=None), row()])
    assert prepare_online_steam_identity(api, STEAM) == {'steam_id': STEAM, 'eos_id': EOS}
    api.get_raw_player_snapshot.clear_for.assert_called_once_with()
    api.get_all_player_info.assert_called_once_with(strict=True)


def test_malformed_online_roster_is_not_treated_as_offline():
    api = api_with_players([])
    api.game_profile.player_adapter = HLLVPlayerInfoAdapter()
    api.get_raw_player_snapshot.return_value = {
        'players': [{'iD': EOS, 'eosId': EOS, 'steamId': STEAM,
                     'platform': 'EPlatformFamily::Steam'}],  # Missing name.
    }
    api.get_all_player_info.side_effect = lambda **kwargs: Rcon.get_all_player_info(api, **kwargs)
    with pytest.raises(PlayerResponseAdapterError):
        prepare_online_steam_identity(api, STEAM)


def test_regular_roster_consumers_keep_skipping_invalid_rows():
    api = api_with_players([])
    api.game_profile.player_adapter = HLLVPlayerInfoAdapter()
    api.get_raw_player_snapshot.return_value = {'players': [{'iD': EOS}]}
    assert Rcon.get_all_player_info(api) == []


def test_duplicate_online_eos_links_fail_without_guessing():
    api = api_with_players([row(), row('fedcba9876543210fedcba9876543210')])
    with pytest.raises(ValueError, match='Multiple online EOS'):
        prepare_online_steam_identity(api, STEAM)


@pytest.mark.parametrize('incomplete', [
    row(steam=None), row(steam='invalid'), row(platform=''),
    row(platform='EPlatformFamily::Unknown', steam=None),
    {**row(), 'eosId': ''},
])
def test_incomplete_metadata_never_proves_steam_player_absent(incomplete):
    api = api_with_players([incomplete])
    with pytest.raises(ValueError):
        prepare_online_steam_identity(api, STEAM)


def test_unknown_second_row_does_not_hide_ambiguous_steam_identity():
    api = api_with_players([row(), row(platform='', steam=None)])
    with pytest.raises(ValueError, match='Unknown online platform'):
        prepare_online_steam_identity(api, STEAM)


def test_inconsistent_platform_for_same_steam_id_fails_closed():
    api = api_with_players([row(platform='EPlatformFamily::Xbox'), row()])
    with pytest.raises(ValueError, match='Inconsistent online Steam identity'):
        prepare_online_steam_identity(api, STEAM)


def test_malformed_delivery_is_left_to_normal_review_handling():
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api_with_players([])
    assert handler._prepare_delivery(b'bad') is None


@pytest.mark.parametrize('sync', [BlacklistSyncMethod.KICK_ONLY, BlacklistSyncMethod.BAN_ON_CONNECT,
                                  BlacklistSyncMethod.BAN_IMMEDIATELY])
def test_new_online_restriction_uses_eos_for_every_sync_mode(sync):
    api, entry = api_with_players([row()]), record(sync)
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    payload = blacklist.BlacklistCreateRecordCommand(player_id=STEAM, record_id=1)
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', side_effect=[entry, None]), \
         patch.object(blacklist, 'apply_blacklist_punishment', return_value=True) as apply:
        handler.handle_create_record(payload, {'steam_id': STEAM, 'eos_id': EOS})
    assert apply.call_args.kwargs['player_id'] == EOS
    api.get_detailed_player_info.assert_called_once_with(player_id=EOS)


def test_changed_identity_never_causes_a_sanction():
    api, entry = api_with_players([row()]), record()
    api.get_detailed_player_info.return_value['steam_id'] = '76561198036685844'
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    payload = blacklist.BlacklistCreateRecordCommand(player_id=STEAM, record_id=1)
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', side_effect=[entry, None]), \
         patch.object(blacklist, 'apply_blacklist_punishment') as apply:
        with pytest.raises(RuntimeError, match='association changed'):
            handler.handle_create_record(payload, {'steam_id': STEAM, 'eos_id': EOS})
    apply.assert_not_called()


@pytest.mark.parametrize('sync,raises', [(BlacklistSyncMethod.KICK_ONLY, False),
                                         (BlacklistSyncMethod.BAN_ON_CONNECT, False),
                                         (BlacklistSyncMethod.BAN_IMMEDIATELY, True)])
def test_offline_unknown_eos_never_sends_steam_id_as_a_game_command(sync, raises):
    api, entry = api_with_players([]), record(sync)
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    payload = blacklist.BlacklistCreateRecordCommand(player_id=STEAM, record_id=1)
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', return_value=entry), \
         patch.object(blacklist, 'apply_blacklist_punishment') as apply:
        if raises:
            with pytest.raises(RuntimeError, match='No verified online EOS'):
                handler.handle_create_record(payload, {'steam_id': STEAM, 'eos_id': None})
        else:
            handler.handle_create_record(payload, {'steam_id': STEAM, 'eos_id': None})
    apply.assert_not_called()


def test_higher_priority_eos_restriction_is_not_overwritten():
    api, entry = api_with_players([row()]), record(expires=datetime.now(timezone.utc) + timedelta(hours=1))
    prior = record(record_id=2, created=datetime.now(timezone.utc) - timedelta(days=1))
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    payload = blacklist.BlacklistCreateRecordCommand(player_id=STEAM, record_id=1)
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', side_effect=[entry, prior]), \
         patch.object(blacklist, 'apply_blacklist_punishment') as apply:
        handler.handle_create_record(payload, {'steam_id': STEAM, 'eos_id': EOS})
    apply.assert_not_called()


@pytest.mark.parametrize('method', ['handle_edit_record', 'handle_delete_record'])
def test_removed_kick_only_record_never_removes_an_independent_ban(method):
    api = api_with_players([])
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    old = {'player_id': STEAM, 'blacklist': {'sync': BlacklistSyncMethod.KICK_ONLY, 'servers': None}}
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', return_value=None), \
         patch.object(blacklist, 'synchronize_ban') as sync:
        getattr(handler, method)(SimpleNamespace(old_record=old), {'steam_id': STEAM, 'eos_id': None})
    sync.assert_not_called()
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


@pytest.mark.parametrize('method', ['handle_edit_record', 'handle_delete_record'])
def test_existing_game_ban_with_unknown_ownership_is_not_removed(method):
    api = api_with_players([row()])
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    old = {'player_id': STEAM, 'blacklist': {'sync': BlacklistSyncMethod.BAN_IMMEDIATELY, 'servers': None}}
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', return_value=None), \
         patch.object(blacklist, 'synchronize_ban') as sync:
        with pytest.raises(blacklist.HLLVSteamBanOwnershipUnverified):
            getattr(handler, method)(SimpleNamespace(old_record=old), {'steam_id': STEAM, 'eos_id': EOS})
    sync.assert_not_called()
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


def test_edit_from_kick_only_to_ban_targets_live_verified_eos():
    api = api_with_players([row()])
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    old = {'player_id': STEAM, 'blacklist': {'sync': BlacklistSyncMethod.KICK_ONLY, 'servers': None}}
    updated = record(BlacklistSyncMethod.BAN_IMMEDIATELY)
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', side_effect=[updated, None]), \
         patch.object(blacklist, 'apply_blacklist_punishment', return_value=True) as apply:
        handler.handle_edit_record(SimpleNamespace(old_record=old), {'steam_id': STEAM, 'eos_id': EOS})
    assert apply.call_args.kwargs['player_id'] == EOS
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


@pytest.mark.parametrize('old_servers,old_id,new_id,old_hours,new_hours,expected', [
    ([4], 1, 1, 2, 2, True),   # Newly applicable on this server.
    ([4], 1, 2, 2, 3, False),  # An unrelated, existing top record.
    (None, 1, 1, 2, 2, False), # The same effective kick-only record.
    (None, 1, 2, 3, 2, True),  # Removing the formerly higher restriction.
    (None, 1, 2, 2, 3, False), # The old restriction was lower priority.
])
def test_kick_only_changes_only_act_on_newly_effective_restrictions(
        old_servers, old_id, new_id, old_hours, new_hours, expected):
    api = api_with_players([row()])
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    now = datetime.now(timezone.utc)
    old = {'id': old_id, 'player_id': STEAM, 'created_at': now,
           'expires_at': now + timedelta(hours=old_hours),
           'blacklist': {'sync': BlacklistSyncMethod.KICK_ONLY, 'servers': old_servers}}
    updated = record(expires=now + timedelta(hours=new_hours), created=now, record_id=new_id)
    with patch.object(blacklist, 'SERVER_NUMBER', 3), \
         patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', side_effect=[updated, None]), \
         patch.object(blacklist, 'apply_blacklist_punishment', return_value=True) as apply:
        handler.handle_edit_record(SimpleNamespace(old_record=old), {'steam_id': STEAM, 'eos_id': EOS})
    assert apply.call_count == int(expected)
    if expected:
        assert apply.call_args.kwargs['player_id'] == EOS
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


def test_list_edit_checks_all_identities_before_any_game_action():
    api = api_with_players([row()])
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    records = [SimpleNamespace(player=SimpleNamespace(player_id=EOS)),
               SimpleNamespace(player=SimpleNamespace(player_id=STEAM))]
    payload = SimpleNamespace(
        old_blacklist={'id': 1, 'servers': None, 'sync': BlacklistSyncMethod.BAN_IMMEDIATELY},
        new_blacklist={'id': 1, 'servers': None, 'sync': BlacklistSyncMethod.KICK_ONLY},
    )
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'get_active_blacklist_records', return_value=iter(records)), \
         patch.object(blacklist, 'synchronize_ban') as sync:
        with pytest.raises(blacklist.HLLVSteamBanOwnershipUnverified):
            handler.handle_edit_list(payload)
    sync.assert_not_called()


def test_list_delete_and_expire_do_not_guess_steam_ban_ownership():
    api = api_with_players([row()])
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    payload = SimpleNamespace(blacklist={'sync': BlacklistSyncMethod.BAN_IMMEDIATELY},
                              banned_players={EOS: (None, None), STEAM: (None, None)})
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'synchronize_ban') as sync:
        with pytest.raises(blacklist.HLLVSteamBanOwnershipUnverified):
            handler.handle_delete_list(payload)
        with pytest.raises(blacklist.HLLVSteamBanOwnershipUnverified):
            handler.handle_expire_all(SimpleNamespace(player_id=STEAM))
    sync.assert_not_called()
    api.get_temp_bans.assert_not_called()
    api.get_perma_bans.assert_not_called()
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


def test_deleting_kick_only_steam_list_without_remaining_record_never_unbans():
    api = api_with_players([])
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    payload = SimpleNamespace(blacklist={'sync': BlacklistSyncMethod.KICK_ONLY},
                              banned_players={STEAM: (None, None)})
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', return_value=None), \
         patch.object(blacklist, 'synchronize_ban') as sync:
        handler.handle_delete_list(payload)
    sync.assert_not_called()
    api.remove_temp_ban.assert_not_called()
    api.remove_perma_ban.assert_not_called()


def test_kick_only_list_delete_preflights_steam_before_any_other_player_action():
    api = api_with_players([])
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    payload = SimpleNamespace(blacklist={'sync': BlacklistSyncMethod.KICK_ONLY},
                              banned_players={EOS: (None, None), STEAM: (None, None)})
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', return_value=record()), \
         patch.object(blacklist, 'synchronize_ban') as sync:
        with pytest.raises(blacklist.HLLVSteamIdentityUnverified):
            handler.handle_delete_list(payload)
    sync.assert_not_called()


def test_kick_only_list_delete_keeps_other_eos_processing():
    api = api_with_players([])
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    payload = SimpleNamespace(blacklist={'sync': BlacklistSyncMethod.KICK_ONLY},
                              banned_players={EOS: (None, None), STEAM: (None, None)})
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', return_value=None), \
         patch.object(blacklist, 'synchronize_ban') as sync:
        handler.handle_delete_list(payload)
    sync.assert_called_once_with(api, EOS, None, blacklist.BanState.NONE)


def test_classic_hll_steam_list_delete_keeps_existing_behavior():
    api = api_with_players([])
    api.game_profile.game = GameEnum.HLL_WW2
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = api
    payload = SimpleNamespace(blacklist={'sync': BlacklistSyncMethod.KICK_ONLY},
                              banned_players={STEAM: (None, None)})
    with patch.object(blacklist, 'blacklist_change_session', return_value=nullcontext(object())), \
         patch.object(blacklist, 'is_player_blacklisted', return_value=None), \
         patch.object(blacklist, 'synchronize_ban') as sync:
        handler.handle_delete_list(payload)
    sync.assert_called_once_with(api, STEAM, None, blacklist.BanState.NONE)
