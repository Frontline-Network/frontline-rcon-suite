"""Synthetic probes of remaining squad-warning retry paths."""
from unittest.mock import Mock
import fakeredis
import pytest
from rcon.automods import automod
from rcon.automods.models import ActionMethod, PunishDetails, PunishPlayer, PunishStepState
from rcon.automods.no_solotank import NoSoloTankAutomod
from rcon.automods.level_thresholds import LevelThresholdsAutomod
from rcon.automods.seeding_rules import SeedingRulesAutomod
from rcon.user_config.auto_mod_solo_tank import AutoModNoSoloTankUserConfig
from rcon.user_config.auto_mod_level import AutoModLevelUserConfig
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig
from rcon.maps import GameMode
from tests.test_automod_action_guard_postgres import database


@pytest.mark.parametrize('mod_type,config_type,key', [
    (NoSoloTankAutomod, AutoModNoSoloTankUserConfig, 'no_solo_tank_id_v2alliesable'),
    (LevelThresholdsAutomod, AutoModLevelUserConfig, 'level_thresholds_automod_id_v2alliesable'),
    (SeedingRulesAutomod, AutoModSeedingUserConfig, 'seeding_rules_automod_id_v2alliesable'),
])
def test_other_rules_do_not_repeat_same_uncertain_warning_after_watch_expiry(database, monkeypatch, mod_type, config_type, key):
    monkeypatch.setattr(automod, 'get_server_number', lambda: '3')
    monkeypatch.setattr(automod, '_periodic_warning_identity', lambda *_: (1000, 'a' * 64, 'b' * 64))
    redis = fakeredis.FakeStrictRedis()
    config = config_type(number_of_warnings=1, warning_interval_seconds=1)
    mod = mod_type(config, redis)
    player = PunishPlayer(player_id='synthetic-eos', name='Synthetic', squad='Able', team='allies', role='rifleman', lvl=100,
                          details=PunishDetails(author=mod.action_author, message='synthetic warning'))
    api = Mock()
    api.message_player.side_effect = TimeoutError('synthetic reply loss')
    with mod.watch_state('allies', 'Able') as state:
        assert mod.should_warn_player(state, 'Able', player) == PunishStepState.APPLY
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [mod])
    redis.delete(key)
    restarted = mod_type(config, redis)
    with restarted.watch_state('allies', 'Able') as state:
        assert restarted.should_warn_player(state, 'Able', player) == PunishStepState.APPLY
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [restarted])
    assert api.message_player.call_count == 1


def test_observed_solo_tank_reset_releases_matching_scope(database, monkeypatch):
    scope = 'c' * 64
    event = (1000, 'a' * 64, scope)
    mod = NoSoloTankAutomod(AutoModNoSoloTankUserConfig(), Mock())
    mod.punitions_to_apply = Mock(return_value=automod.PunitionsToApply())
    token = automod.action_guard.reserve(3, 'synthetic-eos', [mod.action_author], 'message', periodic_event=event)
    assert automod.action_guard.review(3, 'synthetic-eos', token, 'Automod', 'reply lost') == 1
    api = Mock()
    api.get_team_view.return_value = {'allies': {'commander': None, 'squads': {'Able': {
        'type': 'armor', 'players': [{'player_id': 'synthetic-eos'}, {'player_id': 'second'}]}}}, 'axis': None}
    api.get_gamestate.return_value = {}
    monkeypatch.setattr(automod, 'get_server_number', lambda: '3')
    monkeypatch.setattr(automod, '_periodic_warning_scope', lambda *_: scope)
    automod.get_punitions_to_apply(api, [mod])
    assert automod.action_guard.reserve(3, 'synthetic-eos', [mod.action_author], 'message', periodic_event=event)


def test_combined_rule_warning_is_not_repeated_after_watch_loss(database, monkeypatch):
    from rcon.automods.no_leader import NoLeaderAutomod
    from rcon.user_config.auto_mod_no_leader import AutoModNoLeaderUserConfig
    monkeypatch.setattr(automod, 'get_server_number', lambda: '3')
    monkeypatch.setattr(automod, '_periodic_warning_identity', lambda *_: (1000, 'a' * 64, 'c' * 64))
    leader = NoLeaderAutomod(AutoModNoLeaderUserConfig(), fakeredis.FakeStrictRedis())
    solo = NoSoloTankAutomod(AutoModNoSoloTankUserConfig(), fakeredis.FakeStrictRedis())
    player = PunishPlayer(player_id='synthetic-eos', name='Synthetic', squad='Able', team='allies',
                          details=PunishDetails(author=leader.action_author, message='synthetic'),
                          related_authors=[solo.action_author])
    api = Mock()
    api.message_player.side_effect = TimeoutError('synthetic reply loss')
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [leader, solo])
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [leader, solo])
    api.message_player.assert_called_once()


@pytest.mark.parametrize('mod_type,config_type', [
    (LevelThresholdsAutomod, AutoModLevelUserConfig),
    (SeedingRulesAutomod, AutoModSeedingUserConfig),
])
def test_observed_no_violation_releases_player_scope(monkeypatch, mod_type, config_type):
    mod = mod_type(config_type(), fakeredis.FakeStrictRedis())
    mod._periodic_warning_candidates = {'synthetic-eos'}
    seen = Mock()
    monkeypatch.setattr(automod, 'release_observed_periodic_warning', seen)
    if isinstance(mod, SeedingRulesAutomod):
        mod._is_seeding_rule_disabled = Mock(return_value=True)
        mod._disable_for_round = Mock()
        mod._enable_for_round = Mock()
        mod._update_combat_area_excursion = Mock()
    squad = {'type': 'infantry', 'players': [{'player_id': 'synthetic-eos', 'name': 'Synthetic',
                                                'role': 'rifleman', 'level': 100, 'offense': 0}]}
    view = {'allies': {'commander': None, 'squads': {'Able': squad}},
            'axis': {'commander': None, 'squads': {}}}
    game_state = {'game_mode': GameMode.WARFARE, 'axis_score': 0, 'allied_score': 0}
    mod.punitions_to_apply(view, 'Able', 'allies', squad, game_state)
    seen.assert_called_once_with(mod, 'synthetic-eos', 'allies', 'Able', game_state)
