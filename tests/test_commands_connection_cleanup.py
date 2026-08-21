import threading
from unittest.mock import Mock, patch

from rcon.commands import HLLServerCtl
from rcon.types import ServerInfo


class FakeConnection:
    def __init__(self, identifier: str):
        self.id = identifier
        self.connected = False
        self.closed = False

    def connect(self, *_args) -> None:
        self.connected = True

    def close(self) -> None:
        self.closed = True


def test_terminated_thread_connection_is_closed_and_removed_on_next_access():
    perf_stats = Mock()
    controller = HLLServerCtl(ServerInfo(), perf_stats)
    connections = [FakeConnection("worker"), FakeConnection("main")]

    with patch("rcon.commands.HLLConnection", side_effect=connections):
        def worker() -> None:
            with controller.with_connection():
                pass

        thread = threading.Thread(target=worker)
        thread.start()
        thread.join(timeout=1)
        assert not thread.is_alive()
        assert len(controller.conns) == 1

        with controller.with_connection() as current_connection:
            assert current_connection is connections[1]

    assert connections[0].closed is True
    assert connections[1].closed is False
    assert len(controller.conns) == 1
    perf_stats.increment.assert_any_call("connection_closed_dead_thread")
    perf_stats.set.assert_any_call("connection_pool_size", 0)


def test_live_thread_connection_is_not_cleaned_up():
    perf_stats = Mock()
    controller = HLLServerCtl(ServerInfo(), perf_stats)
    connections = [FakeConnection("worker"), FakeConnection("main")]
    worker_started = threading.Event()
    release_worker = threading.Event()

    with patch("rcon.commands.HLLConnection", side_effect=connections):
        def worker() -> None:
            with controller.with_connection():
                worker_started.set()
                release_worker.wait(timeout=1)

        thread = threading.Thread(target=worker)
        thread.start()
        assert worker_started.wait(timeout=1)

        with controller.with_connection() as current_connection:
            assert current_connection is connections[1]
            assert connections[0].closed is False

        release_worker.set()
        thread.join(timeout=1)

    assert connections[0].closed is False

