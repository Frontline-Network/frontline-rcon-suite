import pickle
from datetime import datetime, timedelta
from unittest.mock import Mock

import fakeredis
import pytest

from rcon.automods import automod
from rcon.automods.level_thresholds import LevelThresholdsAutomod
from rcon.automods.models import ActionMethod, PENDING_WARNING, PunishDetails, PunishPlayer, PunishStepState, WatchStatus
from rcon.automods.no_leader import NoLeaderAutomod
from rcon.automods.no_solotank import NoSoloTankAutomod
from rcon.automods.seeding_rules import SeedingRulesAutomod
from rcon.user_config.auto_mod_level import AutoModLevelUserConfig
from rcon.user_config.auto_mod_no_leader import AutoModNoLeaderUserConfig
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig
from rcon.user_config.auto_mod_solo_tank import AutoModNoSoloTankUserConfig


@pytest.fixture(autouse=True)
def isolate_watch_tests_from_durable_guard(monkeypatch):
    monkeypatch.setattr(automod, "get_server_number", lambda: "3")
    monkeypatch.setattr(automod.action_guard, "reserve", lambda *args: "synthetic-token")
    monkeypatch.setattr(automod.action_guard, "finish", lambda *args, **kwargs: kwargs["expected"])


@pytest.mark.parametrize("mod_type,config_type", [
    (NoLeaderAutomod, AutoModNoLeaderUserConfig),
    (NoSoloTankAutomod, AutoModNoSoloTankUserConfig),
    (LevelThresholdsAutomod, AutoModLevelUserConfig),
    (SeedingRulesAutomod, AutoModSeedingUserConfig),
])
@pytest.mark.parametrize("outcome", ["confirmed", "rejected", "timeout", "interrupted"])
def test_warning_state_survives_worker_restart(monkeypatch, mod_type, config_type, outcome):
    redis = fakeredis.FakeStrictRedis()
    config = config_type(number_of_warnings=1, warning_interval_seconds=1)
    mod = mod_type(config, redis)
    player = PunishPlayer(player_id="fake-console-id", name="Player", squad="Able", team="allies",
                          role="rifleman", lvl=100, details=PunishDetails(author=mod.action_author, message="warning"))
    with mod.watch_state(player.team, player.squad) as state:
        assert mod.should_warn_player(state, player.squad, player) == PunishStepState.APPLY
        assert state.warned[mod.progress_key(player)] == [PENDING_WARNING]

    api = Mock()
    api.message_player.return_value = outcome == "confirmed"
    if outcome == "timeout":
        api.message_player.side_effect = TimeoutError("fake lost response")
    monkeypatch.setattr(automod, "audit", Mock())
    if outcome != "interrupted":
        automod._do_punitions(api, ActionMethod.MESSAGE, [player], [mod])

    restarted = mod_type(config, redis)
    with restarted.watch_state(player.team, player.squad) as state:
        if outcome == "confirmed":
            state.warned[mod.progress_key(player)][-1] -= timedelta(seconds=2)
        expected = {"confirmed": PunishStepState.GO_TO_NEXT_STEP,
                    "rejected": PunishStepState.APPLY,
                    "timeout": PunishStepState.WAIT,
                    "interrupted": PunishStepState.WAIT}[outcome]
        assert restarted.should_warn_player(state, player.squad, player) == expected
    assert api.message_player.call_count == (0 if outcome == "interrupted" else 1)


def test_dry_run_confirms_only_simulated_warning(monkeypatch):
    redis = fakeredis.FakeStrictRedis()
    config = AutoModNoLeaderUserConfig(number_of_warnings=1, warning_interval_seconds=0)
    mod = NoLeaderAutomod(config, redis)
    player = PunishPlayer(player_id="fake-id", name="Player", squad="Able", team="allies", lvl=100,
                          details=PunishDetails(author=mod.action_author + "-DryRun", message="warning", dry_run=True))
    with mod.watch_state(player.team, player.squad) as state:
        assert mod.should_warn_player(state, player.squad, player) == PunishStepState.APPLY
    api = Mock()
    monkeypatch.setattr(automod, "audit", Mock())
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [mod])
    api.message_player.assert_not_called()
    with mod.watch_state(player.team, player.squad) as state:
        assert mod.should_warn_player(state, player.squad, player) == PunishStepState.GO_TO_NEXT_STEP


@pytest.mark.parametrize("mod_type,config_type,key", [
    (NoLeaderAutomod, AutoModNoLeaderUserConfig, "no_leader_watchalliesable"),
    (NoSoloTankAutomod, AutoModNoSoloTankUserConfig, "no_solo_tankalliesable"),
    (LevelThresholdsAutomod, AutoModLevelUserConfig, "level_thresholds_automodalliesable"),
])
def test_legacy_name_warning_is_not_attributed_to_any_id(mod_type, config_type, key):
    redis = fakeredis.FakeStrictRedis()
    legacy = WatchStatus(warned={"Player": [datetime.now() - timedelta(seconds=60)]})
    del legacy.__dict__["warning_confirmation_version"]
    redis.set(key, pickle.dumps(legacy))
    mod = mod_type(config_type(number_of_warnings=1, warning_interval_seconds=1), redis)
    player = PunishPlayer(player_id="fake-id", name="Player", squad="Able", team="allies", lvl=100)
    with mod.watch_state("allies", "Able") as state:
        assert "Player" not in state.warned
        assert mod.should_warn_player(state, "Able", player) == PunishStepState.APPLY
    with mod.watch_state("allies", "Able") as state:
        assert state.warned[player.player_id][-1] == PENDING_WARNING
    assert redis.exists(key)


@pytest.mark.parametrize("mod_type,config_type", [
    (NoLeaderAutomod, AutoModNoLeaderUserConfig),
    (NoSoloTankAutomod, AutoModNoSoloTankUserConfig),
    (LevelThresholdsAutomod, AutoModLevelUserConfig),
    (SeedingRulesAutomod, AutoModSeedingUserConfig),
])
def test_duplicate_names_do_not_share_warnings_and_rename_keeps_identity(mod_type, config_type):
    redis = fakeredis.FakeStrictRedis()
    mod = mod_type(config_type(number_of_warnings=1, warning_interval_seconds=1), redis)
    first = PunishPlayer(player_id="eos-first", name="Same", squad="Able", team="allies", lvl=100)
    second = PunishPlayer(player_id="eos-second", name="Same", squad="Able", team="allies", lvl=100)
    with mod.watch_state("allies", "Able") as state:
        assert mod.should_warn_player(state, "Able", first) == PunishStepState.APPLY
        state.warned[first.player_id][-1] = datetime.now() - timedelta(seconds=5)
        assert mod.should_warn_player(state, "Able", second) == PunishStepState.APPLY
        first.name = "Renamed"
        assert mod.should_warn_player(state, "Able", first) == PunishStepState.GO_TO_NEXT_STEP
        assert state.warned[second.player_id] == [PENDING_WARNING]
