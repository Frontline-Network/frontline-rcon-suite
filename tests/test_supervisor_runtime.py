import threading
import time
import unittest

from rcon.supervisor_runtime import ServiceSpec, _service_loop


class SharedSupervisorRuntimeTests(unittest.TestCase):
    def test_shared_service_restarts_after_failure_and_clean_return(self):
        calls = 0
        stop_event = threading.Event()

        def target():
            nonlocal calls
            calls += 1
            if calls == 1:
                raise RuntimeError("expected test failure")
            stop_event.set()

        _service_loop(ServiceSpec("test", target), stop_event, restart_delay=0)

        self.assertEqual(calls, 2)

    def test_shared_service_stops_during_restart_backoff(self):
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

        self.assertFalse(thread.is_alive())
        self.assertEqual(calls, 1)


if __name__ == "__main__":
    unittest.main()
