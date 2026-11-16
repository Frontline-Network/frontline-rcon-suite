"""A failed blacklist action must not trigger a second automatic ban path."""
from unittest.mock import Mock, patch
from contextlib import nullcontext
import pytest
from rcon import hooks


@pytest.mark.parametrize('record,action_result,expect_session,expect_vac', [
    (None, None, True, True),
    (object(), False, True, False),
    (object(), None, True, False),
    (object(), True, False, False),
])
def test_connect_separates_existing_restriction_from_action_result(record, action_result, expect_session, expect_vac):
    api = Mock()
    api.get_detailed_player_info.return_value = None
    event = {'timestamp_ms': 1700000000000, 'player_id_1': 'synthetic-player', 'player_name_1': 'synthetic'}
    with patch('rcon.hooks.lock', return_value=nullcontext()), patch('rcon.hooks.get_server_number', return_value=3), \
         patch('rcon.hooks.enter_session'), patch('rcon.hooks.is_player_blacklisted', return_value=record), \
         patch('rcon.hooks.apply_blacklist_punishment', return_value=action_result) as enforcement, \
         patch('rcon.hooks.save_player'), patch('rcon.hooks.save_start_player_session') as session, \
         patch('rcon.hooks.ban_if_has_vac_bans') as vac:
        hooks.handle_on_connect.__wrapped__(api, event, 'synthetic', 'synthetic-player')
    assert session.called is expect_session
    assert vac.called is expect_vac
    assert enforcement.called is (record is not None)


def test_blacklist_is_rechecked_after_serialization_before_action():
    api = Mock()
    with patch('rcon.hooks.lock', return_value=nullcontext()), patch('rcon.hooks.get_server_number', return_value=3), \
         patch('rcon.hooks.enter_session'), \
         patch('rcon.hooks.is_player_blacklisted', side_effect=[object(), None]), \
         patch('rcon.hooks.apply_blacklist_punishment') as enforcement:
        assert hooks.ban_if_blacklisted(api, 'synthetic-player', 'synthetic') == (False, False)
    enforcement.assert_not_called()


def test_serialization_failure_preserves_existing_restriction_and_skips_vac():
    api = Mock()
    api.get_detailed_player_info.return_value = None
    event = {'timestamp_ms': 1700000000000, 'player_id_1': 'synthetic-player', 'player_name_1': 'synthetic'}
    with patch('rcon.hooks.lock', side_effect=TimeoutError('synthetic lock timeout')), \
         patch('rcon.hooks.get_server_number', return_value=3), patch('rcon.hooks.enter_session'), \
         patch('rcon.hooks.is_player_blacklisted', return_value=object()), \
         patch('rcon.hooks.apply_blacklist_punishment') as enforcement, \
         patch('rcon.hooks.save_player'), patch('rcon.hooks.save_start_player_session') as session, \
         patch('rcon.hooks.ban_if_has_vac_bans') as vac:
        hooks.handle_on_connect.__wrapped__(api, event, 'synthetic', 'synthetic-player')
    enforcement.assert_not_called()
    vac.assert_not_called()
    session.assert_called_once()
