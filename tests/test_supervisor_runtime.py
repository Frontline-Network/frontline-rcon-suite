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
mark_runtime_mode = _RUNTIME.mark_runtime_mode
prepare_shared_state = _RUNTIME.prepare_shared_state
read_service_controls = _RUNTIME.read_service_controls
MODE_KEY = _RUNTIME.MODE_KEY
STATE_KEY = _RUNTIME.STATE_KEY


class SharedSupervisorRuntimeTests(unittest.TestCase):
    def test_default_services_include_all_compatible_python_loops(self):
        names = {service.name for service in DEFAULT_SERVICES}

        self.assertEqual(
            names,
            {
                "population_history",
                "live_map",
                "expiring_vips",
                "live_stats_refresh",
                "autobalancer",
                "blacklists",
                "log_recorder",
                "routines",
                "auto_settings",
                "broadcasts",
                "campaign_messages",
                "log_event_loop",
                "log_stream",
                "scoreboard",
                "automod",
                "watch_killrate",
                "seed_vip",
                "vip_rewards",
            },
        )

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

    def test_service_controls_are_read_in_one_batched_command(self):
        class FakeRedis:
            calls = []

            def hmget(self, key, fields):
                self.calls.append((key, fields))
                return [b"STOPPED", b"token-1", None, None]

        red = FakeRedis()

        self.assertEqual(
            read_service_controls(red, ["broadcasts", "routines"]),
            {
                "broadcasts": ("STOPPED", "token-1"),
                "routines": ("RUNNING", ""),
            },
        )
        self.assertEqual(len(red.calls), 1)
        self.assertEqual(
            red.calls[0],
            (
                STATE_KEY,
                [
                    "broadcasts:desired",
                    "broadcasts:restart",
                    "routines:desired",
                    "routines:restart",
                ],
            ),
        )

    def test_split_to_shared_transition_resets_stale_stop_requests(self):
        class FakeRedis:
            def __init__(self):
                self.values = {MODE_KEY: b"split"}
                self.hashes = {STATE_KEY: {"auto_settings:desired": "STOPPED"}}

            def get(self, key):
                return self.values.get(key)

            def set(self, key, value):
                self.values[key] = value

            def hset(self, key, mapping):
                self.hashes.setdefault(key, {}).update(mapping)

        red = FakeRedis()

        self.assertTrue(
            prepare_shared_state(red, ["auto_settings", "broadcasts"])
        )
        self.assertEqual(red.values[MODE_KEY], "shared")
        self.assertEqual(
            red.hashes[STATE_KEY]["auto_settings:desired"], "RUNNING"
        )
        self.assertEqual(red.hashes[STATE_KEY]["broadcasts:desired"], "RUNNING")

    def test_shared_restart_preserves_intentional_stop_requests(self):
        class FakeRedis:
            def __init__(self):
                self.values = {MODE_KEY: b"shared"}
                self.hashes = {STATE_KEY: {"auto_settings:desired": "STOPPED"}}

            def get(self, key):
                return self.values.get(key)

            def set(self, key, value):
                self.values[key] = value

            def hset(self, key, mapping):
                self.hashes.setdefault(key, {}).update(mapping)

        red = FakeRedis()

        self.assertFalse(prepare_shared_state(red, ["auto_settings"]))
        self.assertEqual(
            red.hashes[STATE_KEY]["auto_settings:desired"], "STOPPED"
        )

    def test_split_runtime_marker_is_persisted(self):
        class FakeRedis:
            values = {}

            def set(self, key, value):
                self.values[key] = value

        red = FakeRedis()
        mark_runtime_mode("split", red=red)

        self.assertEqual(red.values[MODE_KEY], "split")

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

    def test_restart_state_is_part_of_runtime_contract(self):
        source = (Path(__file__).parents[1] / "rcon" / "supervisor_runtime.py").read_text()

        self.assertIn('f"{name}:restart"', source)
        self.assertIn("Restarting requested shared service", source)


if __name__ == "__main__":
    unittest.main()
