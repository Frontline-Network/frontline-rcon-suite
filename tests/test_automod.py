from unittest.mock import Mock
from datetime import datetime
import pickle
import pytest

from rcon.automods import automod
from rcon.automods.automod import _do_punitions
from rcon.automods.models import (
    ActionMethod,
    PunishDetails,
    PunishPlayer,
    PunitionsToApply,
)
from rcon.connection import HLLCommandError


def test_automod_uses_compact_live_roster_snapshot():
    rcon = Mock()
    rcon.get_team_view.return_value = {"allies": {}, "axis": {}}

    automod.get_punitions_to_apply(rcon, [])

    rcon.get_team_view.assert_called_once_with(compact=True)


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
    moderator.action_author = "AutoMod_SeedingRules"

    _do_punitions(rcon, ActionMethod.PUNISH, [player], [moderator])

    moderator.player_punish_failed.assert_called_once_with(player)


@pytest.mark.parametrize("result", [False, OSError("response lost")])
def test_failed_warning_rolls_back_only_originating_rule(result):
    from rcon.automods.models import WatchStatus
    from rcon.automods.no_leader import NoLeaderAutomod
    player = PunishPlayer(player_id="id", name="Player", squad="Able", team="allies",
                          details=PunishDetails(author="AutoMod_NoLeaderWatch", message="warning"))
    red = Mock()
    red.get.return_value = pickle.dumps(WatchStatus(warned={"Player": [datetime.now()]}))
    origin = NoLeaderAutomod(Mock(), red)
    other = Mock()
    other.action_author = "AutoMod_SeedingRules"
    server = Mock()
    if isinstance(result, Exception):
        server.message_player.side_effect = result
    else:
        server.message_player.return_value = result
    _do_punitions(server, ActionMethod.MESSAGE, [player], [origin, other])
    saved = pickle.loads(red.setex.call_args.args[2])
    assert saved.warned["Player"] == []
    other.player_warning_failed.assert_not_called()


def test_failed_punishment_does_not_reset_other_rule():
    player = PunishPlayer(player_id="id", name="Player", squad="Able", team="allies",
                          details=PunishDetails(author="AutoMod_NoLeaderWatch", message="reason"))
    origin, other = Mock(), Mock()
    origin.action_author = "AutoMod_NoLeaderWatch"
    other.action_author = "AutoMod_SeedingRules"
    server = Mock()
    server.punish.return_value = False
    _do_punitions(server, ActionMethod.PUNISH, [player], [origin, other])
    origin.player_punish_failed.assert_called_once_with(player)
    other.player_punish_failed.assert_not_called()


@pytest.mark.parametrize("method", ["punish", "kick"])
@pytest.mark.parametrize("dry_first", [True, False])
def test_dry_run_never_suppresses_live_action(method, dry_first):
    def player(dry):
        return PunishPlayer(player_id="id", name="Player", squad="Able", team="allies",
                            details=PunishDetails(author="test", message="reason", dry_run=dry))
    merged = PunitionsToApply()
    for dry in (dry_first, not dry_first):
        merged.merge(PunitionsToApply(**{method: [player(dry)]}))
    actions = getattr(merged, method)
    assert len(actions) == 1
    assert actions[0].details.dry_run is False


@pytest.mark.parametrize("dry_run", [True, False])
def test_connect_dry_run_and_reconnect_timer(monkeypatch, dry_run):
    from rcon.automods.level_thresholds import LevelThresholdsAutomod
    from rcon.user_config.auto_mod_level import AutoModLevelUserConfig
    timers = []
    class FakeTimer:
        def __init__(self, delay, callback):
            self.callback, self.cancelled = callback, False
            timers.append(self)
        def start(self): pass
        def cancel(self): self.cancelled = True
    server = Mock()
    server.get_detailed_player_info.return_value = {"level": 1}
    cfg = AutoModLevelUserConfig(enabled=True, dry_run=dry_run, announcement_enabled=True, min_level=20)
    monkeypatch.setattr(automod, "Timer", FakeTimer)
    monkeypatch.setattr(automod, "get_redis_client", lambda: None)
    monkeypatch.setattr(automod, "is_first_run_done", lambda _: True)
    monkeypatch.setattr(automod, "enabled_moderators", lambda: [LevelThresholdsAutomod(cfg, None)])
    try:
        log = {"player_name_1": "Player", "player_id_1": "id"}
        automod.on_connected(server, log)
        automod.on_connected(server, log)
        assert timers[0].cancelled is True
        timers[0].callback()
        timers[1].callback()
        assert server.message_player.call_count == (0 if dry_run else 1)
    finally:
        automod.pendingTimers.pop("id", None)


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
