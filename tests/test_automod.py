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


@pytest.fixture(autouse=True)
def isolate_watch_tests_from_durable_guard(monkeypatch):
    """These tests cover Redis watches; PostgreSQL guard behavior is tested separately."""
    monkeypatch.setattr(automod, "get_server_number", lambda: "3")
    monkeypatch.setattr(automod.action_guard, "reserve", lambda *args: "synthetic-token")
    monkeypatch.setattr(automod.action_guard, "finish", lambda *args, **kwargs: kwargs["expected"])


def test_automod_uses_compact_live_roster_snapshot():
    rcon = Mock()
    rcon.get_team_view.return_value = {"allies": {}, "axis": {}}

    automod.get_punitions_to_apply(rcon, [])

    rcon.get_team_view.assert_called_once_with(compact=True)


def test_punish_rcon_error_is_treated_as_uncertain_without_stopping_automod():
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

    moderator.player_punish_started.assert_called_once_with(player)
    moderator.player_punish_succeeded.assert_not_called()
    moderator.player_punish_failed.assert_not_called()


@pytest.mark.parametrize("result", [False, OSError("response lost")])
def test_failed_warning_rolls_back_only_originating_rule(result):
    from rcon.automods.models import PENDING_WARNING, WatchStatus
    from rcon.automods.no_leader import NoLeaderAutomod
    player = PunishPlayer(player_id="id", name="Player", squad="Able", team="allies",
                          details=PunishDetails(author="AutoMod_NoLeaderWatch", message="warning"))
    red = Mock()
    red.get.return_value = pickle.dumps(WatchStatus(warned={"id": [PENDING_WARNING]}))
    origin = NoLeaderAutomod(Mock(), red)
    other = Mock()
    other.action_author = "AutoMod_SeedingRules"
    server = Mock()
    if isinstance(result, Exception):
        server.message_player.side_effect = result
    else:
        server.message_player.return_value = result
    _do_punitions(server, ActionMethod.MESSAGE, [player], [origin, other])
    if result is False:
        saved = pickle.loads(red.setex.call_args.args[2])
        assert saved.warned["id"] == []
    else:
        red.setex.assert_not_called()
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


@pytest.mark.parametrize("result", [True, False, None, OSError("response lost")])
def test_warning_progress_requires_confirmation(monkeypatch, result):
    from contextlib import contextmanager
    from rcon.automods.models import PENDING_WARNING, PunishStepState, WatchStatus
    from rcon.automods.no_leader import NoLeaderAutomod
    from rcon.user_config.auto_mod_no_leader import AutoModNoLeaderUserConfig

    state = WatchStatus()
    mod = NoLeaderAutomod(AutoModNoLeaderUserConfig(number_of_warnings=1, warning_interval_seconds=0), Mock())
    @contextmanager
    def watch_state(_team, _squad):
        yield state
    mod.watch_state = watch_state
    player = PunishPlayer(player_id="fake-id", name="Player", squad="Able", team="allies", lvl=100,
                          details=PunishDetails(author=mod.action_author, message="warning"))
    assert mod.should_warn_player(state, "Able", player) == PunishStepState.APPLY
    assert state.warned[player.player_id] == [PENDING_WARNING]
    server = Mock()
    if isinstance(result, Exception):
        server.message_player.side_effect = result
    else:
        server.message_player.return_value = result
    monkeypatch.setattr(automod, "audit", Mock())
    _do_punitions(server, ActionMethod.MESSAGE, [player], [mod])
    if result is True:
        assert mod.should_warn_player(state, "Able", player) == PunishStepState.GO_TO_NEXT_STEP
    elif result is False:
        assert mod.should_warn_player(state, "Able", player) == PunishStepState.APPLY
    else:
        assert state.warned[player.player_id] == [PENDING_WARNING]
        assert mod.should_warn_player(state, "Able", player) == PunishStepState.WAIT
    server.message_player.assert_called_once()


@pytest.mark.parametrize("method", [ActionMethod.PUNISH, ActionMethod.KICK])
@pytest.mark.parametrize("result", [True, False, None, OSError("response lost")])
def test_action_outcome_controls_repeat_and_escalation(monkeypatch, method, result):
    from contextlib import contextmanager
    from rcon.automods.is_time import is_time
    from rcon.automods.models import PENDING_WARNING, WatchStatus
    from rcon.automods.no_leader import NoLeaderAutomod

    initial = datetime.now()
    state = WatchStatus(punished={"fake-id": [initial]})
    mod = NoLeaderAutomod(Mock(), Mock())
    @contextmanager
    def watch_state(_team, _squad):
        yield state
    mod.watch_state = watch_state
    player = PunishPlayer(player_id="fake-id", name="Player", squad="Able", team="allies",
                          details=PunishDetails(author=mod.action_author, message="reason"))
    server = Mock()
    target = server.punish if method == ActionMethod.PUNISH else server.kick
    if isinstance(result, Exception):
        target.side_effect = result
    else:
        target.return_value = result
    monkeypatch.setattr(automod, "audit", Mock())
    _do_punitions(server, method, [player], [mod])
    if result is False:
        assert state.punished["fake-id"] == ([] if method == ActionMethod.PUNISH else [initial])
    elif result is True and method == ActionMethod.PUNISH:
        assert len(state.punished["fake-id"]) == 1
        assert state.punished["fake-id"][-1] != PENDING_WARNING
    else:
        assert state.punished["fake-id"][-1] == PENDING_WARNING
        assert not is_time(state.punished["fake-id"], 0)
    target.assert_called_once()


def test_audit_failure_after_confirmed_punishment_does_not_reset_state(monkeypatch):
    player = PunishPlayer(player_id="fake-id", name="Player", squad="Able", team="allies",
                          details=PunishDetails(author="rule", message="reason"))
    mod = Mock()
    mod.action_author = "rule"
    server = Mock()
    server.punish.return_value = True
    monkeypatch.setattr(automod, "audit", Mock(side_effect=OSError("audit unavailable")))
    _do_punitions(server, ActionMethod.PUNISH, [player], [mod])
    mod.player_punish_failed.assert_not_called()
    mod.player_punish_started.assert_called_once_with(player)
    mod.player_punish_succeeded.assert_called_once_with(player)


@pytest.mark.parametrize("result", [True, False, OSError("response lost")])
def test_weapon_event_without_squad_does_not_create_shared_watch(monkeypatch, result):
    player = PunishPlayer(player_id="fake-id", name="Player", squad="", team="",
                          details=PunishDetails(author="rule", message="reason"))
    mod = Mock()
    mod.action_author = "rule"
    server = Mock()
    if isinstance(result, Exception):
        server.punish.side_effect = result
    else:
        server.punish.return_value = result
    monkeypatch.setattr(automod, "audit", Mock())
    _do_punitions(server, ActionMethod.PUNISH, [player], [mod])
    server.punish.assert_called_once()
    mod.player_punish_started.assert_not_called()
    mod.player_punish_succeeded.assert_not_called()
    mod.player_punish_failed.assert_not_called()


@pytest.mark.parametrize("method", [ActionMethod.PUNISH, ActionMethod.KICK])
def test_interrupted_action_keeps_pending_reservation(monkeypatch, method):
    from contextlib import contextmanager
    from rcon.automods.models import PENDING_WARNING, WatchStatus
    from rcon.automods.no_leader import NoLeaderAutomod

    state = WatchStatus(punished={"fake-id": [datetime.now()]})
    mod = NoLeaderAutomod(Mock(), Mock())
    @contextmanager
    def watch_state(_team, _squad):
        yield state
    mod.watch_state = watch_state
    player = PunishPlayer(player_id="fake-id", name="Player", squad="Able", team="allies",
                          details=PunishDetails(author=mod.action_author, message="reason"))
    server = Mock()
    target = server.punish if method == ActionMethod.PUNISH else server.kick
    target.side_effect = KeyboardInterrupt()
    monkeypatch.setattr(automod, "audit", Mock())
    with pytest.raises(KeyboardInterrupt):
        _do_punitions(server, method, [player], [mod])
    assert state.punished["fake-id"][-1] == PENDING_WARNING


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


@pytest.mark.parametrize("method", [ActionMethod.PUNISH, ActionMethod.KICK])
@pytest.mark.parametrize("result", [False, OSError("response lost")])
def test_merged_live_rules_receive_same_action_outcome(monkeypatch, method, result):
    def player(author):
        return PunishPlayer(player_id="fake-id", name="Player", squad="Able", team="allies",
                            details=PunishDetails(author=author, message="reason"))
    merged = PunitionsToApply()
    action_name = "punish" if method == ActionMethod.PUNISH else "kick"
    for author in ("rule-a", "rule-b"):
        merged.merge(PunitionsToApply(**{action_name: [player(author)]}))
    mods = [Mock(action_author="rule-a"), Mock(action_author="rule-b")]
    server = Mock()
    action = getattr(server, action_name)
    if isinstance(result, Exception):
        action.side_effect = result
    else:
        action.return_value = result
    monkeypatch.setattr(automod, "audit", Mock())
    _do_punitions(server, method, getattr(merged, action_name), mods)
    action.assert_called_once()
    for mod in mods:
        if method == ActionMethod.PUNISH:
            mod.player_punish_started.assert_called_once()
            assert mod.player_punish_failed.call_count == (1 if result is False else 0)
        else:
            mod.player_kick_attempted.assert_called_once()
            assert mod.player_kick_rejected.call_count == (1 if result is False else 0)


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
