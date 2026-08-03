import os

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.autobalancer.store import AutobalancerStore


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.stream = []
        self.sequence = 0

    def set(self, key, value, nx=False, ex=None):
        if nx and key in self.values:
            return False
        self.values[key] = value
        return True

    def get(self, key):
        return self.values.get(key)

    def exists(self, key):
        return key in self.values

    def expire(self, key, ttl):
        return key in self.values

    def delete(self, *keys):
        for key in keys:
            self.values.pop(key, None)

    def eval(self, script, key_count, key, token, *args):
        if self.values.get(key) != token:
            return 0
        if "expire" in script:
            return 1
        self.values.pop(key, None)
        return 1

    def xadd(self, key, fields, maxlen=None, approximate=True):
        self.sequence += 1
        stream_id = f"{self.sequence}-0"
        self.stream.append((stream_id, fields))
        return stream_id

    def xread(self, streams, count=100, block=1):
        key, cursor = next(iter(streams.items()))
        sequence = int(cursor.split("-", 1)[0])
        entries = [
            entry for entry in self.stream if int(entry[0].split("-")[0]) > sequence
        ]
        return [(key, entries[:count])] if entries else []


def test_duplicate_events_are_idempotent():
    store = AutobalancerStore(FakeRedis(), server_number=1)
    payload = {"event_id": "same-log-line", "player_id": "victim"}
    assert store.publish_event("death", payload) is not None
    assert store.publish_event("death", payload) is None
    events = store.read_events()
    assert len(events) == 1
    store.acknowledge_events(events)
    assert store.read_events() == []


def test_only_one_instance_wins_leader_lock():
    redis = FakeRedis()
    first = AutobalancerStore(redis, server_number=1)
    second = AutobalancerStore(redis, server_number=1)
    assert first.acquire_leader("first") is True
    assert second.acquire_leader("second") is False
    assert first.renew_leader("first") is True
    first.release_leader("first")
    assert second.acquire_leader("second") is True


def test_stale_leader_cannot_renew_or_release_new_owner_lock():
    redis = FakeRedis()
    store = AutobalancerStore(redis, server_number=1)
    redis.values[store.key("leader")] = "new-owner"
    assert store.renew_leader("stale-owner") is False
    store.release_leader("stale-owner")
    assert redis.values[store.key("leader")] == "new-owner"


def test_only_one_switch_execution_can_be_active_per_server():
    redis = FakeRedis()
    first = AutobalancerStore(redis, server_number=1)
    second = AutobalancerStore(redis, server_number=1)
    assert first.acquire_execution("first") is True
    assert second.acquire_execution("second") is False
    second.release_execution("second")
    assert redis.values[first.key("execution")] == "first"
    first.release_execution("first")
    assert second.acquire_execution("second") is True
