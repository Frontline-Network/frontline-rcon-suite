from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon import hooks
from rcon.types import GameEnum, WindowsStoreIdActionType


@pytest.mark.parametrize("action", list(WindowsStoreIdActionType))
@pytest.mark.parametrize("player_id", ["0" * 32, "f" * 32])
def test_hllv_eos_ids_do_not_trigger_windows_store_actions(monkeypatch, action, player_id):
    config = SimpleNamespace(enabled=True, action=action, player_message="reason",
                             audit_message="{name}", audit_message_author="admin",
                             temp_ban_length_hours=1)
    monkeypatch.setattr(hooks.RconServerSettingsUserConfig, "load_from_db",
                        lambda: SimpleNamespace(windows_store_players=config))
    audit = Mock()
    monkeypatch.setattr(hooks, "send_to_discord_audit", audit)
    rcon = Mock()
    rcon.config.game = GameEnum.HLL_VIETNAM
    hooks.windows_store_player_check.__wrapped__(rcon, {}, "player", player_id)
    rcon.kick.assert_not_called()
    rcon.temp_ban.assert_not_called()
    rcon.perma_ban.assert_not_called()
    audit.assert_not_called()
