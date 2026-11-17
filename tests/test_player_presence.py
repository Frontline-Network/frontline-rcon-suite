from contextlib import nullcontext
import json
import logging
import os
from types import SimpleNamespace
from unittest.mock import Mock
from uuid import uuid4

import pytest
import redis

from rcon.player_presence import (PresenceWindow, capture_observation, database_scope,
                                  merge_observations, read_observations, run_loop, snapshot_key,
                                  validated_observation)


def payload(**overrides):
    return {'version': 1, 'server_number': 4, 'started_at': 990.0,
            'finished_at': 992.0, 'players': ['steam-id', 'console-id'], **overrides}


def test_fresh_roster_keeps_observation_interval_and_empty_roster_is_valid():
    assert validated_observation(payload(), server_number=4, now=1000, max_age=30) == (
        PresenceWindow(990, 992), ('steam-id', 'console-id'))
    assert validated_observation(payload(players=[]), server_number=4, now=1000, max_age=30) == (
        PresenceWindow(990, 992), ())


@pytest.mark.parametrize('change', [
    {'server_number': 3}, {'started_at': 960}, {'started_at': 993},
    {'finished_at': 1001}, {'started_at': 970, 'finished_at': 992},
    {'players': ['same', 'same']}, {'players': ['']}, {'players': [' x']},
    {'players': ['x' * 101]}, {'players': ['x'] * 251}, {'version': True},
    {'started_at': float('nan')},
])
def test_unreliable_roster_is_never_used_as_presence(change):
    assert validated_observation(payload(**change), server_number=4, now=1000, max_age=30) is None


def test_latest_sighting_bounds_merge_without_assuming_instant_or_continuous_presence():
    observations = [
        (PresenceWindow(990, 995), ['shared', 'console']),
        (PresenceWindow(992, 994), ['shared', 'steam']),
    ]
    assert merge_observations(observations) == {
        'shared': PresenceWindow(992, 995),
        'console': PresenceWindow(990, 995),
        'steam': PresenceWindow(992, 994),
    }


def test_database_scope_separates_databases_without_exposing_password():
    first = database_scope('postgresql://reader:secret@db:5432/one')
    assert first == database_scope('postgresql://reader:different@db:5432/one')
    assert first != database_scope('postgresql://reader:secret@db:5432/two')
    assert 'secret' not in first
    with pytest.raises(ValueError):
        database_scope('sqlite:///local.db')


@pytest.fixture
def isolated_redis():
    url = os.getenv('TEST_REDIS_URL')
    if not url:
        pytest.skip('requires disposable Redis')
    client = redis.Redis.from_url(url, decode_responses=True)
    scope = uuid4().hex * 2
    yield client, scope
    client.delete(*(snapshot_key(scope, server) for server in (3, 4)))
    client.close()


def test_real_redis_complete_roster_and_failed_refresh_preserve_only_known_sample(isolated_redis):
    red, scope = isolated_redis
    api = Mock()
    api.without_retries.return_value = nullcontext()
    api.get_player_ids.return_value = [('name-a', 'console-id'), ('name-b', 'steam-id')]
    assert capture_observation(red, api, scope=scope, server_number=3)
    seen, available = read_observations(red, scope=scope, server_numbers=[3, 4])
    assert set(seen) == {'console-id', 'steam-id'} and available == {3}
    assert red.ttl(snapshot_key(scope, 3)) > 0
    api.get_player_ids.return_value = [('valid', 'same'), ('invalid', 'same')]
    with pytest.raises(ValueError):
        capture_observation(red, api, scope=scope, server_number=3)
    assert read_observations(red, scope=scope, server_numbers=[3, 4])[0] == seen
    assert 'name-a' not in red.get(snapshot_key(scope, 3))
    other_scope = database_scope('postgresql://reader:secret@db/other-database')
    assert read_observations(red, scope=other_scope, server_numbers=[3, 4]) == ({}, set())


def test_real_redis_stale_corrupt_or_wrong_server_values_are_unknown(isolated_redis):
    red, scope = isolated_redis
    seconds, microseconds = red.time()
    now = seconds + microseconds / 1_000_000
    red.set(snapshot_key(scope, 3), json.dumps(payload(server_number=3, started_at=now-100,
                                                       finished_at=now-99)))
    red.set(snapshot_key(scope, 4), 'not-json')
    assert read_observations(red, scope=scope, server_numbers=[3, 4]) == ({}, set())
    red.set(snapshot_key(scope, 3), json.dumps(payload(server_number=4, started_at=now-1,
                                                       finished_at=now)))
    assert read_observations(red, scope=scope, server_numbers=[3, 4]) == ({}, set())


def test_late_old_capture_cannot_replace_a_newer_roster(isolated_redis):
    red, scope = isolated_redis
    seconds, _ = red.time()

    class ClockedRedis:
        def __init__(self, *times):
            self.times = iter(times)

        def time(self):
            return next(self.times), 0

        def eval(self, *args):
            return red.eval(*args)

    api = Mock()
    api.without_retries.return_value = nullcontext()
    api.get_player_ids.return_value = [('name', 'new-player')]
    assert capture_observation(ClockedRedis(seconds-3, seconds-2), api, scope=scope, server_number=3)
    api.get_player_ids.return_value = [('name', 'older-player')]
    assert not capture_observation(ClockedRedis(seconds-5, seconds-4), api, scope=scope, server_number=3)
    sightings, available = read_observations(red, scope=scope, server_numbers=[3])
    assert set(sightings) == {'new-player'} and available == {3}


def test_failed_poll_does_not_refresh_prior_observation(isolated_redis, caplog):
    red, scope = isolated_redis
    api = Mock()
    api.without_retries.return_value = nullcontext()
    api.get_player_ids.return_value = [('name', 'synthetic-player')]
    capture_observation(red, api, scope=scope, server_number=3)
    key = snapshot_key(scope, 3)
    before = red.get(key)
    api.get_player_ids.side_effect = OSError('sensitive synthetic detail')
    stop = Mock()
    stop.is_set.return_value = False
    stop.wait.return_value = True
    run_loop(red, api, scope=scope, server_number=3, stop_event=stop)
    assert red.get(key) == before
    assert 'sensitive synthetic detail' not in caplog.text
    stop.wait.assert_called_once()


def test_repeated_failures_are_rate_limited_and_recovery_is_reported(monkeypatch, caplog):
    from rcon import player_presence

    capture = Mock(side_effect=[OSError('private'), OSError('private'), OSError('private'),
                                ValueError('private'), True])
    monkeypatch.setattr(player_presence, 'capture_observation', capture)
    monotonic = iter([0, 15, 300, 315])
    monkeypatch.setattr(player_presence, 'time', SimpleNamespace(monotonic=lambda: next(monotonic)))
    stop = Mock()
    stop.is_set.return_value = False
    stop.wait.side_effect = [False, False, False, False, True]
    with caplog.at_level(logging.INFO, logger=player_presence.__name__):
        run_loop(None, None, scope='synthetic', server_number=4, stop_event=stop)
    assert capture.call_count == 5
    assert [record.getMessage() for record in caplog.records] == [
        'Player presence observation unavailable (OSError)',
        'Player presence observation unavailable (OSError)',
        'Player presence observation unavailable (ValueError)',
        'Player presence observation recovered',
    ]
    assert 'private' not in caplog.text


def test_missing_shared_database_does_not_restart_service_in_a_tight_loop(monkeypatch, caplog):
    from rcon import player_presence

    monkeypatch.delenv('HLL_DB_URL', raising=False)
    stop = Mock()
    stop.is_set.return_value = False
    stop.wait.return_value = True
    player_presence.run(stop)
    stop.wait.assert_called_once_with(player_presence.FAILURE_LOG_INTERVAL_SECONDS)
    assert 'initialization unavailable (KeyError)' in caplog.text


def test_remote_observations_reject_unaligned_clocks(monkeypatch):
    from rcon import cache_utils, player_presence

    monkeypatch.setenv('HLL_DB_URL', 'postgresql://reader@db/shared')
    red = Mock()
    red.time.return_value = (1000, 0)
    monkeypatch.setattr(cache_utils, 'get_redis_client', lambda **kwargs: red)
    monkeypatch.setattr(player_presence, 'time', SimpleNamespace(time=lambda: 1002.01))
    with pytest.raises(ValueError, match='clock'):
        player_presence.read_other_servers(3)
    red.mget.assert_not_called()
