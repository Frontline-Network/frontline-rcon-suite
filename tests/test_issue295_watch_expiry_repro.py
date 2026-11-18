"""Reproduce a lost warning reply followed by expiry of the squad watch."""
from unittest.mock import Mock

import fakeredis
import pytest

from rcon.automods import automod
from rcon.automods.models import ActionMethod, PunishDetails, PunishPlayer, PunishStepState
from rcon.automods.no_leader import NoLeaderAutomod
from rcon.user_config.auto_mod_no_leader import AutoModNoLeaderUserConfig
from tests.test_automod_action_guard_postgres import database


@pytest.mark.xfail(strict=True, reason='Uncertain warning can be repeated after watch expiry')
def test_same_unresolved_warning_is_not_repeated_after_squad_watch_expires(database, monkeypatch):
    monkeypatch.setattr(automod, 'get_server_number', lambda: '3')
    redis = fakeredis.FakeStrictRedis()
    config = AutoModNoLeaderUserConfig(number_of_warnings=1, warning_interval_seconds=1)
    mod = NoLeaderAutomod(config, redis)
    player = PunishPlayer(player_id='synthetic-eos', name='Synthetic', squad='Able', team='allies',
                          role='rifleman', lvl=100,
                          details=PunishDetails(author=mod.action_author, message='synthetic warning'))
    api = Mock()
    api.message_player.side_effect = TimeoutError('synthetic reply loss after possible delivery')

    with mod.watch_state('allies', 'Able') as state:
        assert mod.should_warn_player(state, 'Able', player) == PunishStepState.APPLY
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [mod])
    assert api.message_player.call_count == 1

    # Equivalent to the documented expiry of the Redis watch during downtime.
    redis.delete('no_leader_watch_id_v2alliesable')
    restarted = NoLeaderAutomod(config, redis)
    with restarted.watch_state('allies', 'Able') as state:
        assert restarted.should_warn_player(state, 'Able', player) == PunishStepState.APPLY
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [restarted])
    assert api.message_player.call_count == 1
