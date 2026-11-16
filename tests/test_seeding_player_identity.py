import pickle
from datetime import datetime, timedelta

import fakeredis

from rcon.automods.models import PENDING_WARNING, PunishDetails, PunishPlayer, PunishStepState, WatchStatus
from rcon.automods.seeding_rules import SeedingRulesAutomod
from rcon.user_config.auto_mod_seeding import AutoModSeedingUserConfig


def player(pid, name):
    return PunishPlayer(player_id=pid, name=name, team='allies', squad='Able', lvl=100,
                        details=PunishDetails(author='AutoMod_SeedingRules'))


def test_duplicate_names_are_independent_and_rename_preserves_progress():
    mod = SeedingRulesAutomod(AutoModSeedingUserConfig(number_of_warnings=1, warning_interval_seconds=0), fakeredis.FakeStrictRedis())
    first, second = player('eos-one', 'Same'), player('eos-two', 'Same')
    with mod.watch_state('allies', 'Able') as state:
        assert mod.should_warn_player(state, 'Able', first) == PunishStepState.APPLY
        state.warned[first.player_id][-1] = datetime.now() - timedelta(seconds=10)
        assert mod.should_warn_player(state, 'Able', second) == PunishStepState.APPLY
        renamed = player('eos-one', 'Renamed')
        assert mod.should_warn_player(state, 'Able', renamed) == PunishStepState.GO_TO_NEXT_STEP
        assert state.warned[second.player_id] == [PENDING_WARNING]


def test_legacy_name_history_is_not_attributed_to_new_ids():
    red = fakeredis.FakeStrictRedis()
    old_key = 'seeding_rules_automodalliesable'
    red.setex(old_key, 120, pickle.dumps(WatchStatus(warned={'Same': [datetime.now() - timedelta(minutes=1)]})))
    mod = SeedingRulesAutomod(AutoModSeedingUserConfig(number_of_warnings=1, warning_interval_seconds=0), red)
    with mod.watch_state('allies', 'Able') as state:
        assert mod.should_warn_player(state, 'Able', player('eos-new', 'Same')) == PunishStepState.APPLY
    assert red.exists(old_key)


def test_warning_confirmation_and_reset_use_id():
    red = fakeredis.FakeStrictRedis()
    mod = SeedingRulesAutomod(AutoModSeedingUserConfig(number_of_warnings=1, warning_interval_seconds=0), red)
    first, second = player('eos-one', 'Same'), player('eos-two', 'Same')
    with mod.watch_state('allies', 'Able') as state:
        assert mod.should_warn_player(state, 'Able', first) == PunishStepState.APPLY
        assert mod.should_warn_player(state, 'Able', second) == PunishStepState.APPLY
    mod.player_warning_succeeded(first)
    with mod.watch_state('allies', 'Able') as state:
        assert state.warned[first.player_id][-1] != PENDING_WARNING
        assert state.warned[second.player_id][-1] == PENDING_WARNING
        mod._clear_player_progress(state, first.player_id)
        assert first.player_id not in state.warned
        assert second.player_id in state.warned


def test_missing_identity_is_ignored_on_connect_and_kill():
    red = fakeredis.FakeStrictRedis()
    mod = SeedingRulesAutomod(AutoModSeedingUserConfig(), red)
    result = mod.on_connected('Synthetic', '')
    assert not result.warning and not result.punish and not result.kick
    assert not red.keys('*')
    result = mod.on_kill({'player_id_1': None, 'weapon': 'synthetic'})
    assert not result.warning and not result.punish and not result.kick
