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
    record = object()

    def lookup(_session, identifier):
        return record if identifier == STEAM else None

    with patch('rcon.hooks.lock', return_value=nullcontext()), \
         patch('rcon.hooks.get_server_number', return_value=3), \
         patch('rcon.hooks.enter_session'), \
         patch('rcon.hooks.is_player_blacklisted', side_effect=lookup) as lookup_mock, \
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
    event = {'timestamp_ms': 1700000000000, 'player_id_1': EOS, 'player_name_1': 'synthetic'}
    with patch('rcon.hooks.save_player'), patch('rcon.hooks.PlayerSoldier.update'), \
         patch('rcon.hooks.save_start_player_session'), patch('rcon.hooks.ban_if_has_vac_bans'), \
         patch('rcon.hooks.ban_if_blacklisted', return_value=(False, False)) as check:
        hooks.handle_on_connect.__wrapped__(api, event, 'synthetic', EOS)
    check.assert_called_once_with(api, EOS, 'synthetic', verified_steam_id=expected)
