from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock, patch

import pytest

from rcon import hooks
from rcon.types import GameEnum

EOS = '0123456789abcdef0123456789abcdef'
STEAM = '76561198036685843'


def player(**changes):
    info = {'player_id': EOS, 'eos_id': EOS, 'steam_id': STEAM,
            'platform': 'EPlatformFamily::Steam'}
    info.update(changes)
    return info


def server(game=GameEnum.HLL_VIETNAM):
    return SimpleNamespace(game_profile=SimpleNamespace(game=game))


def test_only_current_self_consistent_vietnam_steam_identity_is_used():
    assert hooks._verified_hllv_steam_id(server(), EOS, player()) == STEAM
    assert hooks._verified_hllv_steam_id(server(GameEnum.HLL_WW2), EOS, player()) is None
    for changes in (
        {'player_id': 'other'}, {'eos_id': 'other'}, {'steam_id': None},
        {'steam_id': 'invalid'}, {'platform': 'EPlatformFamily::Xbox'},
        {'platform': 'EPlatformFamily::WinGDK'}, {'platform': 'EPlatformFamily::PS5'},
    ):
        assert hooks._verified_hllv_steam_id(server(), EOS, player(**changes)) is None
    assert hooks._verified_hllv_steam_id(server(), 'not-eos', player(player_id='not-eos', eos_id='not-eos')) is None
    assert hooks._verified_hllv_steam_id(server(), EOS, None) is None


def test_restriction_on_verified_steam_id_is_applied_to_eos_id():
    api = server()
    record = SimpleNamespace(id=1, player=SimpleNamespace(player_id=STEAM))

    def lookup(_session, identifier):
        return record if identifier == STEAM else None

    with patch('rcon.hooks.lock', return_value=nullcontext()), \
         patch('rcon.hooks.get_server_number', return_value=3), \
         patch('rcon.hooks.enter_session'), \
         patch('rcon.hooks.is_player_blacklisted', side_effect=lookup) as lookup_mock, \
         patch('rcon.hooks.prepare_online_steam_identity', return_value={'steam_id': STEAM, 'eos_id': EOS}), \
         patch('rcon.hooks.apply_blacklist_punishment', return_value=True) as apply:
        assert hooks.ban_if_blacklisted(api, EOS, 'synthetic', verified_steam_id=STEAM) == (True, True)
    assert lookup_mock.call_count == 4  # Repeat both lookups under the synchronization lock.
    apply.assert_called_once_with(api, record, player_id=EOS, player_name='synthetic')


def test_multiple_applicable_records_keep_highest_existing_priority():
    now = datetime.now(timezone.utc)
    temporary = SimpleNamespace(created_at=now, expires_at=now + timedelta(hours=1))
    permanent = SimpleNamespace(created_at=now - timedelta(days=1), expires_at=None)
    with patch('rcon.hooks.is_player_blacklisted', side_effect=[temporary, permanent]):
        assert hooks._connect_blacklist_record(object(), EOS, STEAM) is permanent


def test_unverified_identity_never_looks_up_a_steam_alias():
    with patch('rcon.hooks.is_player_blacklisted', return_value=None) as lookup:
        assert hooks._connect_blacklist_record(object(), EOS, None) is None
    lookup.assert_called_once()


@pytest.mark.parametrize('game,info,expected', [
    (GameEnum.HLL_VIETNAM, player(), STEAM),
    (GameEnum.HLL_VIETNAM, player(platform='EPlatformFamily::Xbox'), None),
    (GameEnum.HLL_WW2, player(), None),
])
def test_connect_passes_only_server_verified_alias(game, info, expected):
    api = Mock()
    api.game_profile.game = game
    api.get_detailed_player_info.return_value = info
    api.get_uncached_detailed_player_info.return_value = info
    event = {'timestamp_ms': 1700000000000, 'player_id_1': EOS, 'player_name_1': 'synthetic'}
    with patch('rcon.hooks.save_player'), patch('rcon.hooks.PlayerSoldier.update'), \
         patch('rcon.hooks.save_start_player_session'), patch('rcon.hooks.ban_if_has_vac_bans'), \
         patch('rcon.hooks.ban_if_blacklisted', return_value=(False, False)) as check:
        hooks.handle_on_connect.__wrapped__(api, event, 'synthetic', EOS)
    check.assert_called_once_with(api, EOS, 'synthetic', verified_steam_id=expected)
    if game == GameEnum.HLL_VIETNAM:
        api.get_uncached_detailed_player_info.assert_called_once_with(EOS)
        api.get_detailed_player_info.assert_not_called()


def test_connect_uses_fresh_roster_when_player_response_lacks_steam_id():
    api = Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [{'iD': EOS, 'eosId': EOS, 'steamId': STEAM,
                                             'platform': 'EPlatformFamily::Steam'}]
    assert hooks._connect_verified_steam_id(api, EOS, player(steam_id=None)) == STEAM
    api.get_all_player_info.assert_called_once_with(strict=True, fresh=True)


def test_connect_does_not_guess_when_roster_is_incomplete():
    api = Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    api.without_retries.return_value = nullcontext()
    api.get_all_player_info.return_value = [{'iD': EOS, 'eosId': EOS, 'steamId': None,
                                             'platform': 'EPlatformFamily::Steam'}]
    assert hooks._connect_verified_steam_id(api, EOS, player(steam_id=None)) is None


def test_console_identity_does_not_trigger_steam_roster_lookup():
    api = Mock()
    api.game_profile.game = GameEnum.HLL_VIETNAM
    assert hooks._connect_verified_steam_id(api, EOS, player(platform='EPlatformFamily::PS5', steam_id=None)) is None
    api.get_all_player_info.assert_not_called()


@pytest.mark.parametrize('identity,clock', [
    ({'steam_id': STEAM, 'eos_id': None}, [10.0]),
    ({'steam_id': STEAM, 'eos_id': EOS}, [10.0, 16.0]),
])
def test_connect_does_not_sanction_changed_or_stale_alias(identity, clock):
    entry = SimpleNamespace(id=1, player=SimpleNamespace(player_id=STEAM))
    def lookup(_session, identifier):
        return entry if identifier == STEAM else None
    with patch('rcon.hooks.lock', return_value=nullcontext()), \
         patch('rcon.hooks.get_server_number', return_value=3), \
         patch('rcon.hooks.enter_session'), \
         patch('rcon.hooks.is_player_blacklisted', side_effect=lookup), \
         patch('rcon.hooks.prepare_online_steam_identity', return_value=identity), \
         patch('rcon.blacklist_sync_journal.enqueue_connect_reconciliation') as defer, \
         patch('rcon.hooks.monotonic', side_effect=clock), \
         patch('rcon.hooks.apply_blacklist_punishment') as apply:
        assert hooks.ban_if_blacklisted(server(), EOS, 'synthetic', verified_steam_id=STEAM) == (True, False)
    apply.assert_not_called()
    defer.assert_called_once()
