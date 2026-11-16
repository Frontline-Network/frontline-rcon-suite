"""Durable team-switch reservations use only disposable PostgreSQL data."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timezone
from threading import Barrier

from rcon.automods import action_guard
from rcon.autobalancer.models import Phase
from rcon.user_config.autobalancer import AutobalancerUserConfig
from tests.autobalancer.test_service import make_snapshot, service
from tests.test_automod_action_guard_postgres import database


def test_concurrent_switch_reservation_survives_reconnect_and_review(database):
    barrier = Barrier(8)

    def worker(_):
        barrier.wait(timeout=10)
        return action_guard.reserve(3, 'synthetic', ['AutobalancerSwitch'], 'switch')

    with ThreadPoolExecutor(max_workers=8) as pool:
        tokens = list(pool.map(worker, range(8)))
    assert sum(token is not None for token in tokens) == 1
    token = next(token for token in tokens if token)
    database.kw['bind'].dispose()
    assert action_guard.pending_players(3, 'AutobalancerSwitch') == {'synthetic'}
    assert action_guard.reserve(3, 'synthetic', ['AutobalancerSwitch'], 'switch') is None
    assert action_guard.pending_players(4, 'AutobalancerSwitch') == set()
    assert action_guard.review(3, 'synthetic', token, 'operator', 'checked server logs') == 1
    assert action_guard.reserve(3, 'synthetic', ['AutobalancerSwitch'], 'switch') is not None


def test_uncertain_service_outcome_retains_real_reservation(database, monkeypatch):
    instance = service()
    instance.server_number = 3
    instance.action_guard = action_guard
    monkeypatch.setattr('rcon.autobalancer.service.read_seeding_active', lambda *args: False)
    calls = []

    def lost_reply(player_id):
        calls.append(player_id)
        raise TimeoutError('synthetic lost reply')

    instance.rcon.switch_player_now = lost_reply
    now = datetime.fromtimestamp(3000, timezone.utc)
    state = {'phase': Phase.ARMED, 'decision_id': 'first', 'source_team': 'allies',
             'target_team': 'axis', 'candidate': {'player_id': 'a0', 'base_tier': 0}}
    instance._execute_after_death(state, make_snapshot(now), AutobalancerUserConfig(mode='auto'),
                                  {'timestamp_ms': 2999000, 'player_id': 'a0'}, now)
    assert calls == ['a0']
    assert action_guard.pending_players(3, 'AutobalancerSwitch') == {'a0'}
    assert action_guard.reserve(3, 'a0', ['AutobalancerSwitch'], 'switch') is None


def test_transition_hold_blocks_all_players_only_on_its_server(database):
    token = action_guard.reserve(3, '*', ['AutobalancerSwitch'], 'switch', legacy_global=True)
    assert action_guard.pending_players(3, 'AutobalancerSwitch') == {'*'}
    assert action_guard.reserve(3, 'synthetic', ['AutobalancerSwitch'], 'switch') is None
    assert action_guard.reserve(4, 'synthetic', ['AutobalancerSwitch'], 'switch')
    assert action_guard.review(3, '*', token, 'operator', 'transition checked') == 1
    assert action_guard.pending_players(3, 'AutobalancerSwitch') == set()
    assert action_guard.reserve(3, 'synthetic', ['AutobalancerSwitch'], 'switch')
