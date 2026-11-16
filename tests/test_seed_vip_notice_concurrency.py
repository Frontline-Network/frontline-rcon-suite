import threading
from contextlib import nullcontext
from unittest.mock import Mock

import fakeredis

from rcon.seed_vip import notifications


def test_concurrent_consumers_send_a_notice_at_most_once(monkeypatch):
    monkeypatch.setattr(notifications.time, "sleep", lambda _: None)
    redis = fakeredis.FakeStrictRedis()
    api = Mock()
    api.without_retries.side_effect = nullcontext
    api.message_player.return_value = True

    for index in range(20):
        redis.flushdb()
        api.message_player.reset_mock()
        queue = notifications.NotificationOutbox(redis, "test")
        queue.enqueue({f"fake-player-{index}": "fake notice"}, api)
        barrier = threading.Barrier(3)
        errors = []

        def consumer():
            try:
                barrier.wait()
                notifications.NotificationOutbox(redis, "test").flush(api)
            except BaseException as exc:
                errors.append(exc)

        threads = [threading.Thread(target=consumer) for _ in range(2)]
        for thread in threads:
            thread.start()
        barrier.wait()
        for thread in threads:
            thread.join()

        assert not errors
        api.message_player.assert_called_once_with(
            player_id=f"fake-player-{index}", message="fake notice"
        )
