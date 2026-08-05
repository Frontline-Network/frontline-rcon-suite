from unittest.mock import Mock

from rcon.automods.automod import _do_punitions
from rcon.automods.models import ActionMethod, PunishDetails, PunishPlayer
from rcon.connection import HLLCommandError


def test_punish_rcon_error_is_logged_and_retried_without_stopping_automod():
    player = PunishPlayer(
        player_id="player-id",
        name="Player",
        squad="Able",
        team="allies",
        details=PunishDetails(author="AutoMod_SeedingRules", message="Follow seeding rules"),
    )
    rcon = Mock()
    rcon.punish.side_effect = HLLCommandError(500, "Unable to perform request")
    moderator = Mock()

    _do_punitions(rcon, ActionMethod.PUNISH, [player], [moderator])

    moderator.player_punish_failed.assert_called_once_with(player)
