from types import SimpleNamespace
from unittest import mock

from rcon.hllv_admin_refresh import refresh_hllv_admin_role_on_connect
from rcon.types import GameEnum

EOS_ID = "a" * 32


def _rcon(game=GameEnum.HLL_VIETNAM):
    rcon = mock.Mock()
    rcon.config = SimpleNamespace(game=game)
    return rcon


def test_hll_does_not_refresh_spectator_role():
    rcon = _rcon(GameEnum.HLL_WW2)

    assert refresh_hllv_admin_role_on_connect(rcon, "7" * 17, "Player") is False

    rcon.get_admin_ids.assert_not_called()
    rcon.add_admin.assert_not_called()


def test_hllv_ignores_non_eos_admin_id():
    rcon = _rcon()

    assert refresh_hllv_admin_role_on_connect(rcon, "7" * 17, "Player") is False

    rcon.get_admin_ids.assert_not_called()
    rcon.add_admin.assert_not_called()


def test_hllv_refreshes_confirmed_spectator_role_and_preserves_comment():
    rcon = _rcon()
    spectator = {
        "player_id": EOS_ID,
        "role": "Spectator",
        "name": "Camera account",
    }
    rcon.get_admin_ids.side_effect = [[spectator], [spectator]]
    rcon.add_admin.return_value = True

    assert refresh_hllv_admin_role_on_connect(rcon, EOS_ID, "Player") is True

    assert rcon.get_admin_ids.call_count == 2
    rcon.get_admin_ids.cache_clear.assert_called_once_with()
    rcon.add_admin.assert_called_once_with(
        player_id=EOS_ID,
        role="spectator",
        description="Camera account",
    )


def test_hllv_does_not_restore_role_removed_after_cached_read():
    rcon = _rcon()
    cached_spectator = {
        "player_id": EOS_ID,
        "role": "spectator",
        "name": "Old assignment",
    }
    rcon.get_admin_ids.side_effect = [[cached_spectator], []]

    assert refresh_hllv_admin_role_on_connect(rcon, EOS_ID, "Player") is False

    rcon.get_admin_ids.cache_clear.assert_called_once_with()
    rcon.add_admin.assert_not_called()


def test_hllv_does_not_refresh_other_admin_roles():
    rcon = _rcon()
    owner = {"player_id": EOS_ID, "role": "owner", "name": "Owner"}
    rcon.get_admin_ids.return_value = [owner]

    assert refresh_hllv_admin_role_on_connect(rcon, EOS_ID, "Player") is False

    rcon.add_admin.assert_not_called()


def test_hllv_reports_rejected_refresh_without_removing_role():
    rcon = _rcon()
    spectator = {"player_id": EOS_ID, "role": "spectator", "name": "Player"}
    rcon.get_admin_ids.side_effect = [[spectator], [spectator]]
    rcon.add_admin.return_value = False

    assert refresh_hllv_admin_role_on_connect(rcon, EOS_ID, "Player") is False

    rcon.add_admin.assert_called_once()
    rcon.remove_admin.assert_not_called()
