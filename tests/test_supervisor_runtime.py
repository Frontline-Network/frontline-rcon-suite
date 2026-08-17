import threading
import time

from rcon.supervisor_runtime import ServiceSpec, _service_loop


def test_shared_service_restarts_after_failure_and_clean_return():
    calls = 0
    stop_event = threading.Event()

    def target():
        nonlocal calls
        calls += 1
        if calls == 1:
            raise RuntimeError("expected test failure")
        stop_event.set()

    _service_loop(ServiceSpec("test", target), stop_event, restart_delay=0)

    assert calls == 2


def test_shared_service_stops_during_restart_backoff():
    calls = 0
    stop_event = threading.Event()

    def target():
        nonlocal calls
        calls += 1

    thread = threading.Thread(
        target=_service_loop,
        args=(ServiceSpec("test", target), stop_event, 60),
    )
    thread.start()
    while calls == 0:
        time.sleep(0.001)
    stop_event.set()
    thread.join(timeout=1)

    assert not thread.is_alive()
    assert calls == 1
