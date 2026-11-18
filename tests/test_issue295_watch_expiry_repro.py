"""Reproduce a lost warning reply followed by expiry of the squad watch."""
from unittest.mock import Mock
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import fakeredis
import pytest

from rcon.automods import action_guard, automod, event_guard
from sqlalchemy import select
from rcon.automods.models import ActionMethod, PunishDetails, PunishPlayer, PunishStepState, PunitionsToApply
from rcon.automods.no_leader import NoLeaderAutomod
from rcon.user_config.auto_mod_no_leader import AutoModNoLeaderUserConfig
from tests.test_automod_action_guard_postgres import database


def test_same_unresolved_warning_is_not_repeated_after_squad_watch_expires(database, monkeypatch):
    monkeypatch.setattr(automod, 'get_server_number', lambda: '3')
    monkeypatch.setattr(automod, '_periodic_warning_identity', lambda *_: (1000, 'a' * 64), raising=False)
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


def test_periodic_attempt_deduplicates_only_its_exact_identity(database):
    first = (1000, 'a' * 64)
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=first)
    assert token
    assert action_guard.review(3, 'synthetic', token, 'Automod', 'reply lost') == 1
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=first) is None
    for player, rule, identity in [('other', 'rule', first), ('synthetic', 'other', first),
                                    ('synthetic', 'rule', (1001, 'b' * 64))]:
        token = action_guard.reserve(3, player, [rule], 'message', periodic_event=identity)
        assert token
        assert action_guard.finish(3, player, token, 'confirmed', expected=1) == 1
        # A confirmed send is not retained as an uncertain attempt.
        token = action_guard.reserve(3, player, [rule], 'message', periodic_event=identity)
        assert token
        assert action_guard.finish(3, player, token, 'confirmed', expected=1) == 1


def test_parallel_periodic_reservations_send_at_most_once(database):
    from threading import Barrier
    barrier = Barrier(6)
    def reserve(_):
        barrier.wait(timeout=5)
        return action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=(1000, 'a' * 64, 'c' * 64))
    with ThreadPoolExecutor(max_workers=6) as executor:
        results = list(executor.map(reserve, range(6)))
    assert sum(bool(token) for token in results) == 1


def test_periodic_scope_can_be_released_after_positive_rule_reset(database):
    scope = 'c' * 64
    event = (1000, 'a' * 64, scope)
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=event)
    assert action_guard.review(3, 'synthetic', token, 'Automod', 'reply lost') == 1
    assert action_guard.release_periodic_scope(3, 'synthetic', 'other-rule', scope) == 0
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=event) is None
    assert action_guard.release_periodic_scope(3, 'synthetic', 'rule', scope) == 1
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=event)


def test_positive_rule_reset_during_send_is_applied_after_outcome(database):
    scope = 'c' * 64
    event = (1000, 'a' * 64, scope)
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=event)
    assert action_guard.release_periodic_scope(3, 'synthetic', 'rule', scope) == 0
    # The action is still in flight; the reset must not allow a parallel send.
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=event) is None
    assert action_guard.review(3, 'synthetic', token, 'Automod', 'reply lost') == 1
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=event)


def test_observed_leader_releases_only_matching_player_and_squad(database, monkeypatch):
    scope = 'c' * 64
    event = (1000, 'a' * 64, scope)
    mod = NoLeaderAutomod(AutoModNoLeaderUserConfig(), Mock())
    mod.punitions_to_apply = Mock(return_value=PunitionsToApply())
    token = action_guard.reserve(3, 'synthetic', [mod.action_author], 'message', periodic_event=event)
    assert action_guard.review(3, 'synthetic', token, 'Automod', 'reply lost') == 1
    api = Mock()
    api.get_team_view.return_value = {'allies': {'commander': None, 'squads': {
        'Able': {'has_leader': True, 'players': [{'player_id': 'synthetic'}]}}}, 'axis': None}
    api.get_gamestate.return_value = {}
    monkeypatch.setattr(automod, 'get_server_number', lambda: '3')
    monkeypatch.setattr(automod, '_periodic_warning_scope', lambda *_: scope)
    automod.get_punitions_to_apply(api, [mod])
    assert action_guard.reserve(3, 'synthetic', [mod.action_author], 'message', periodic_event=event)


def test_periodic_scope_remains_manually_reviewable(database):
    event = (1000, 'b' * 64, 'c' * 64)
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=event)
    assert action_guard.review(3, 'synthetic', token, 'Automod', 'reply lost') == 1
    assert any(row['token'] == token for row in action_guard.list_pending(3)['results'])
    assert action_guard.review(3, 'synthetic', token, 'operator', 'verified') == 1
    assert all(row['token'] != token for row in action_guard.list_pending(3)['results'])
    assert action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=event)


def test_warning_scope_changes_only_with_verified_context(monkeypatch):
    import rcon.active_session_selection as sessions
    import rcon.autobalancer.snapshot as snapshot
    import rcon.models as models

    current = {'session': 10, 'round': 'round-one', 'stable': True}
    monkeypatch.setattr(automod, 'get_server_number', lambda: '3')
    monkeypatch.setattr(models, 'get_session_maker', lambda: lambda: nullcontext(object()))
    monkeypatch.setattr(sessions, 'latest_open_sessions',
                        lambda *args: [(object(), SimpleNamespace(id=current['session']))] if current['session'] else [])
    monkeypatch.setattr(snapshot, '_map_name', lambda state: 'map')
    monkeypatch.setattr(snapshot, '_current_round', lambda *_: (current['round'], 0, current['stable']))
    def scope(squad='Able'):
        return automod._periodic_warning_scope('synthetic', 'allies', squad, {})
    initial = scope()
    assert initial and scope() == initial
    assert scope('Baker') != initial
    current['session'] = 11
    assert scope() != initial
    current['session'] = 10
    current['round'] = 'round-two'
    assert scope() != initial
    current['stable'] = False
    assert scope() is None
    current['stable'] = True
    current['session'] = None
    assert scope() is None


def test_log_event_cleanup_does_not_remove_periodic_warning(database):
    token = action_guard.reserve(3, 'synthetic', ['rule'], 'message', periodic_event=(1000, 'a' * 64, 'c' * 64))
    assert action_guard.review(3, 'synthetic', token, 'Automod', 'reply lost') == 1
    with database.begin() as session:
        session.execute(event_guard.cutover.insert().values(server_number=3, boundary_ms=0, cleanup_ms=0))
    event_guard.allow_after_cutover(3, int(__import__('time').time() * 1000), action_guard._lock)
    with database() as session:
        assert session.execute(select(event_guard.events).where(event_guard.events.c.token == token)).one()


def test_real_session_and_round_change_produce_new_scope(database, monkeypatch):
    import rcon.autobalancer.snapshot as snapshot
    import rcon.models as models

    engine = database.kw['bind']
    models.PlayerID.__table__.create(engine)
    models.PlayerSession.__table__.create(engine)
    monkeypatch.setattr(models, 'get_session_maker', lambda: database)
    monkeypatch.setattr(automod, 'get_server_number', lambda: '3')
    now = datetime.now(timezone.utc)
    round_data = {'name': 'synthetic-map', 'start': int(now.timestamp()) - 60}
    monkeypatch.setattr(snapshot, 'MapsHistory', lambda **kwargs: [dict(round_data)])
    state = {'current_map': {'id': 'synthetic-map'}}
    with database.begin() as session:
        player = models.PlayerID(player_id='synthetic-eos')
        session.add(player)
        session.flush()
        first = models.PlayerSession(player_id_id=player.id, server_number=3,
                                     start=now.replace(tzinfo=None) - timedelta(seconds=30),
                                     created=now.replace(tzinfo=None) - timedelta(seconds=30))
        session.add(first)
        session.flush()
        first_id = first.id
        player_db_id = player.id
    original = automod._periodic_warning_scope('synthetic-eos', 'allies', 'Able', state)
    assert original
    original_event = (1000, original, original)
    token = action_guard.reserve(3, 'synthetic-eos', ['rule'], 'message', periodic_event=original_event)
    assert action_guard.review(3, 'synthetic-eos', token, 'Automod', 'reply lost') == 1
    assert action_guard.reserve(3, 'synthetic-eos', ['rule'], 'message', periodic_event=original_event) is None
    assert automod._periodic_warning_scope('synthetic-eos', 'allies', 'Baker', state) != original
    with database.begin() as session:
        session.get(models.PlayerSession, first_id).end = now.replace(tzinfo=None)
        session.add(models.PlayerSession(player_id_id=player_db_id, server_number=3,
                                         start=now.replace(tzinfo=None), created=now.replace(tzinfo=None)))
    new_session = automod._periodic_warning_scope('synthetic-eos', 'allies', 'Able', state)
    assert new_session and new_session != original
    token = action_guard.reserve(3, 'synthetic-eos', ['rule'], 'message', periodic_event=(1000, new_session, new_session))
    assert token
    assert action_guard.finish(3, 'synthetic-eos', token, 'confirmed', expected=1) == 1
    round_data['start'] += 30
    new_round = automod._periodic_warning_scope('synthetic-eos', 'allies', 'Able', state)
    assert new_round and new_round != new_session
    assert action_guard.reserve(3, 'synthetic-eos', ['rule'], 'message', periodic_event=(1000, new_round, new_round))
