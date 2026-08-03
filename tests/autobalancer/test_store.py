import os

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.autobalancer.store import AutobalancerStore


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.lists = {}
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
            self.lists.pop(key, None)

    def lpush(self, key, value):
        self.lists.setdefault(key, []).insert(0, value)

    def ltrim(self, key, start, end):
        self.lists[key] = self.lists.get(key, [])[start : end + 1]

    def lrange(self, key, start, end):
        return self.lists.get(key, [])[start : end + 1]

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


class ByteStreamRedis(FakeRedis):
    def get(self, key):
        value = super().get(key)
        return value.encode("utf-8") if isinstance(value, str) else value

    def xread(self, streams, count=100, block=1):
        streams = {
            key: value.decode("utf-8") if isinstance(value, bytes) else value
            for key, value in streams.items()
        }
        result = super().xread(streams, count=count, block=block)
        return [
            (
                stream.encode("utf-8"),
                [
                    (
                        stream_id.encode("utf-8"),
                        {
                            key.encode("utf-8"): value.encode("utf-8")
                            for key, value in fields.items()
                        },
                    )
                    for stream_id, fields in entries
                ],
            )
            for stream, entries in result
        ]


def test_duplicate_events_are_idempotent():
    store = AutobalancerStore(FakeRedis(), server_number=1)
    payload = {"event_id": "same-log-line", "player_id": "victim"}
    assert store.publish_event("death", payload) is not None
    assert store.publish_event("death", payload) is None
    events = store.read_events()
    assert len(events) == 1
    store.acknowledge_events(events)
    assert store.read_events() == []


def test_byte_mode_redis_streams_and_armed_player_are_supported():
    store = AutobalancerStore(ByteStreamRedis(), server_number=1)
    store.arm_player("victim")
    assert store.is_armed_player("victim") is True

    payload = {"event_id": "byte-event", "player_id": "victim"}
    assert store.publish_event("death", payload) is not None
    events = store.read_events()

    assert events == [
        {
            "event_id": "byte-event",
            "player_id": "victim",
            "type": "death",
            "stream_id": "1-0",
        }
    ]
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


def test_status_history_is_sampled_and_returned_in_chronological_order():
    redis = FakeRedis()
    store = AutobalancerStore(redis, server_number=1)
    first = {
        "updated_at": "2026-08-03T20:00:00+00:00",
        "mode": "shadow",
        "phase": "idle",
        "team_counts": {"allies": 48, "axis": 47},
        "team_difference": 1,
        "required_switches": 0,
    }
    store.save_status(first)
    store.save_status({**first, "team_difference": 4})

    assert store.load_status_history() == [
        {
            **first,
            "round_id": None,
            "block_reasons": [],
        }
    ]

    redis.values.pop(store.key("status_history_gate"))
    second = {
        **first,
        "updated_at": "2026-08-03T20:00:30+00:00",
        "team_difference": -3,
    }
    store.save_status(second)
    assert [sample["team_difference"] for sample in store.load_status_history()] == [
        1,
        -3,
    ]


def test_only_one_live_snapshot_is_claimed_per_sampling_window():
    store = AutobalancerStore(FakeRedis(), server_number=1)

    assert store.claim_snapshot_slot() is True
    assert store.claim_snapshot_slot() is False
    assert store.claim_snapshot_prune() is True
    assert store.claim_snapshot_prune() is False
