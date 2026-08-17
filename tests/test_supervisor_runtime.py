import importlib.util
from pathlib import Path
import sys
import threading
import time
import unittest


_MODULE_SPEC = importlib.util.spec_from_file_location(
    "frontline_supervisor_runtime",
    Path(__file__).parents[1] / "rcon" / "supervisor_runtime.py",
)
assert _MODULE_SPEC and _MODULE_SPEC.loader
_RUNTIME = importlib.util.module_from_spec(_MODULE_SPEC)
sys.modules[_MODULE_SPEC.name] = _RUNTIME
_MODULE_SPEC.loader.exec_module(_RUNTIME)
ServiceSpec = _RUNTIME.ServiceSpec
DEFAULT_SERVICES = _RUNTIME.DEFAULT_SERVICES
_service_loop = _RUNTIME._service_loop
decode_service_state = _RUNTIME.decode_service_state


class SharedSupervisorRuntimeTests(unittest.TestCase):
    def test_default_services_keep_automod_isolated(self):
        names = {service.name for service in DEFAULT_SERVICES}

        self.assertIn("auto_settings", names)
        self.assertIn("broadcasts", names)
        self.assertNotIn("automod", names)

    def test_redis_state_decodes_bytes_from_shared_pool(self):
        self.assertEqual(
            decode_service_state(
                {
                    b"live_stats_refresh:desired": b"STOPPED",
                    "routines:state": "RUNNING",
                }
            ),
            {
                "live_stats_refresh:desired": "STOPPED",
                "routines:state": "RUNNING",
            },
        )

    def test_shared_service_restarts_after_failure_and_clean_return(self):
        calls = 0
        stop_event = threading.Event()

        def target(_stop_event):
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

        def target(_stop_event):
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
