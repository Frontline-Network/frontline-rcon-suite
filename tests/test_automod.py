from unittest.mock import Mock

from rcon.automods import automod
from rcon.automods.automod import _do_punitions
from rcon.automods.models import (
    ActionMethod,
    PunishDetails,
    PunishPlayer,
    PunitionsToApply,
)
from rcon.connection import HLLCommandError


def test_punish_rcon_error_is_logged_and_retried_without_stopping_automod():
    player = PunishPlayer(
        player_id="player-id",
        name="Player",
        squad="Able",
        team="allies",
        details=PunishDetails(
            author="AutoMod_SeedingRules", message="Follow seeding rules"
        ),
    )
    rcon = Mock()
    rcon.punish.side_effect = HLLCommandError(500, "Unable to perform request")
    moderator = Mock()

    _do_punitions(rcon, ActionMethod.PUNISH, [player], [moderator])

    moderator.player_punish_failed.assert_called_once_with(player)


def test_do_punitions_reuses_one_moderator_snapshot(monkeypatch):
    moderators = [Mock()]
    enabled_moderators = Mock(return_value=moderators)
    apply_punitions = Mock()
    monkeypatch.setattr(automod, "enabled_moderators", enabled_moderators)
    monkeypatch.setattr(automod, "_do_punitions", apply_punitions)

    automod.do_punitions(Mock(), PunitionsToApply())

    enabled_moderators.assert_called_once_with()
    assert apply_punitions.call_count == 3
    assert all(call.args[3] is moderators for call in apply_punitions.call_args_list)


def test_pending_timer_cleanup_does_not_remove_newer_timer():
    player_id = "player-id"
    older = Mock()
    newer = Mock()
    automod.pendingTimers[player_id] = newer

    automod._remove_pending_timer(player_id, older)
    assert automod.pendingTimers[player_id] is newer

    automod._remove_pending_timer(player_id, newer)
    assert player_id not in automod.pendingTimers
