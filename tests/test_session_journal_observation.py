import os
from types import SimpleNamespace
from uuid import uuid4

import pytest
import redis

from rcon import session_journal_observation as observation


def valid(**changes):
    return {'version': 1, 'server_number': 3, 'started_at': 990, 'finished_at': 992,
            'pending': 0, 'unpublished_anonymous': 0, **changes}


@pytest.mark.parametrize('change', [
    {'version': True}, {'server_number': 4}, {'started_at': 960}, {'started_at': float('nan')},
    {'finished_at': 1001}, {'started_at': 993}, {'pending': -1}, {'pending': True},
    {'unpublished_anonymous': -1}, {'unpublished_anonymous': None},
])
def test_invalid_observation_is_not_accepted(change):
    assert observation.validate(valid(**change), server_number=3, now=1000) is None


def test_counts_are_observations_not_boolean_completeness():
    value = observation.validate(valid(pending=2, unpublished_anonymous=1), server_number=3, now=1000)
    assert value == observation.JournalObservation(990, 992, 2, 1)


@pytest.mark.skipif(not os.environ.get('TEST_REDIS_URL'), reason='requires isolated Redis')
def test_real_redis_isolates_servers_and_retains_only_newer_observations():
    client = redis.Redis.from_url(os.environ['TEST_REDIS_URL'], decode_responses=True)
    scope = uuid4().hex * 2
    key3, key4 = [observation.observation_key(scope, server) for server in (3, 4)]
    try:
        journal = SimpleNamespace(pending_counts=lambda server: (2, 1) if server == 3 else (0, 0))
        assert observation.publish(client, journal, scope=scope, server_number=3)
        first = observation.read(client, scope=scope, server_number=3)
        assert (first.pending, first.unpublished_anonymous) == (2, 1)
        assert observation.read(client, scope=scope, server_number=4) is None
        assert client.ttl(key3) > 0
        class OlderClock:
            def time(self):
                return (int(first.started_at) - 5, 0)
            def eval(self, *args):
                return client.eval(*args)
        assert not observation.publish(OlderClock(), journal, scope=scope, server_number=3)
        assert observation.read(client, scope=scope, server_number=3) == first
        client.set(key4, '{invalid')
        assert observation.read(client, scope=scope, server_number=4) is None
    finally:
        client.delete(key3, key4)
        client.close()
