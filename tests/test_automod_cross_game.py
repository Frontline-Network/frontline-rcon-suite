"""Cross-game audit of role thresholds and the configured punishment limit."""

from contextlib import contextmanager
from datetime import timedelta
from unittest.mock import Mock

import pytest

from rcon.automods.level_thresholds import LevelThresholdsAutomod
from rcon.automods.models import WatchStatus
from rcon.user_config.auto_mod_level import AutoModLevelUserConfig


@pytest.mark.parametrize("role", ["officer", "squadleader"])
@pytest.mark.parametrize("team", ["allies", "axis"])
@pytest.mark.parametrize("punishment_limit", [0, 1, 2, -1])
@pytest.mark.parametrize("kick_enabled", [False, True])
def test_hll_and_vietnam_role_limits_and_punishment_cap(
    role, team, punishment_limit, kick_enabled
):
    config = AutoModLevelUserConfig(
        enabled=True,
        number_of_warnings=0,
        number_of_punishments=punishment_limit,
        punish_interval_seconds=60,
        kick_after_max_punish=kick_enabled,
        kick_grace_period_seconds=120,
        level_thresholds={
            "officer": {"label": "Leader", "min_level": 50, "min_players": 0}
        },
    )
    mod = LevelThresholdsAutomod(config, Mock())
    watch = WatchStatus()

    @contextmanager
    def watch_state(*_):
        yield watch

    mod.watch_state = watch_state
    player = {
        "player_id": "test-player", "name": "Test Player", "level": 7,
        "role": role, "team": team, "unit_name": "able", "profile": None,
    }
    squad = {"players": [player]}
    view = {team: {"commander": None, "squads": {"able": squad}}}
    for attempt in range(5):
        result = mod.punitions_to_apply(view, "able", team, squad, {})
        should_punish = punishment_limit != 0 and (
            punishment_limit == -1 or attempt < punishment_limit or not kick_enabled
        )
        assert len(result.punish) == int(should_punish)
        if not kick_enabled:
            assert not result.kick
        if result.punish:
            waiting = mod.punitions_to_apply(view, "able", team, squad, {})
            assert not waiting.punish and not waiting.kick
            if punishment_limit > 0:
                assert len(watch.punished[player["name"]]) <= punishment_limit
            watch.punished[player["name"]][-1] -= timedelta(seconds=61)

    player["level"] = 50
    result = mod.punitions_to_apply(view, "able", team, squad, {})
    assert not result.warning and not result.punish and not result.kick


@pytest.mark.parametrize("role", ["officer", "squadleader"])
def test_level_one_exception_also_applies_to_both_games(role):
    config = AutoModLevelUserConfig(
        enabled=True, levelbug_enabled=True, number_of_warnings=2,
        level_thresholds={
            "officer": {"label": "Leader", "min_level": 50, "min_players": 0}
        },
    )
    mod = LevelThresholdsAutomod(config, Mock())

    @contextmanager
    def watch_state(*_):
        yield WatchStatus()

    mod.watch_state = watch_state
    player = {"player_id": "test-player", "name": "Test", "level": 1, "role": role, "profile": None}
    squad = {"players": [player]}
    view = {"allies": {"commander": None, "squads": {"able": squad}}}
    result = mod.punitions_to_apply(view, "able", "allies", squad, {})
    assert not result.warning and not result.punish and not result.kick
