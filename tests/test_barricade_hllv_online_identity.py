from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest
from rcon import blacklist
from rcon.barricade_hllv_identity import prepare_online_steam_identity
from rcon.types import BlacklistSyncMethod, GameEnum

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


def test_duplicate_online_eos_links_fail_without_guessing():
    api = api_with_players([row(), row('fedcba9876543210fedcba9876543210')])
    with pytest.raises(ValueError, match='Multiple online EOS'):
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
