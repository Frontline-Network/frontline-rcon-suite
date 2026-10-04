import json
import os
import subprocess
import sys
import unittest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
SUPERVISOR_COMMANDS = {
    "auto_settings",
    "autobalancer",
    "automod",
    "blacklists",
    "broadcast_loop",
    "combined_runtime",
    "campaign_message_loop",
    "expiring_vips",
    "live_stats_loop",
    "population_history",
    "log_loop",
    "log_recorder",
    "log_stream",
    "routines",
    "seed_vip",
    "supervisor_runtime_mode",
    "watch_killrate",
}


class SupervisorCliTests(unittest.TestCase):
    def _run_python(self, code, *args):
        env = os.environ.copy()
        env["HLL_SUPERVISOR_PROCESS"] = "1"
        env["PYTHONPATH"] = str(REPO_ROOT)
        env.setdefault("SERVER_NUMBER", "1")
        env.setdefault("DEBUG", "1")
        return subprocess.run(
            [sys.executable, "-c", code, *args],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

    @staticmethod
    def _result_payload(result):
        line = next(
            line for line in result.stdout.splitlines() if line.startswith("RESULT:")
        )
        return json.loads(line.removeprefix("RESULT:"))

    def test_import_exposes_only_supervisor_commands_and_keeps_services_lazy(self):
        result = self._run_python("""
import json
import sys
from rcon.supervisor_cli import cli

heavy_modules = (
    "rcon.hooks",
    "rcon.autobalancer.service",
    "rcon.automods.automod",
    "rcon.logs.recorder",
    "rcon.logs.stream",
    "rcon.player_stats",
    "rcon.user_config.log_stream",
    "rcon.user_config.scoreboard",
    "rcon.user_config.webhooks",
    "rcon.watch_killrate",
)
print("RESULT:" + json.dumps({
    "commands": sorted(cli.commands),
    "loaded_heavy_modules": [name for name in heavy_modules if name in sys.modules],
}))
""")

        self.assertEqual(0, result.returncode, result.stderr)
        payload = self._result_payload(result)
        self.assertEqual(SUPERVISOR_COMMANDS, set(payload["commands"]))
        self.assertEqual([], payload["loaded_heavy_modules"])

    def test_log_hooks_are_explicit_and_idempotent(self):
        result = self._run_python("""
import json
from rcon.log_hooks import register_log_hooks
from rcon.logs.loop import HOOKS

before = sum(len(callbacks) for callbacks in HOOKS.values())
register_log_hooks()
after_first = sum(len(callbacks) for callbacks in HOOKS.values())
register_log_hooks()
after_second = sum(len(callbacks) for callbacks in HOOKS.values())
print("RESULT:" + json.dumps({
    "before": before,
    "after_first": after_first,
    "after_second": after_second,
}))
""")

        self.assertEqual(0, result.returncode, result.stderr)
        payload = self._result_payload(result)
        self.assertEqual(0, payload["before"])
        self.assertGreater(payload["after_first"], 0)
        self.assertEqual(payload["after_first"], payload["after_second"])

    def test_manage_help_uses_minimal_cli(self):
        env = os.environ.copy()
        env["HLL_SUPERVISOR_PROCESS"] = "1"
        env["PYTHONPATH"] = str(REPO_ROOT)
        env.setdefault("SERVER_NUMBER", "1")
        env.setdefault("DEBUG", "1")
        result = subprocess.run(
            [sys.executable, str(REPO_ROOT / "manage.py"), "--help"],
            cwd=REPO_ROOT,
            env=env,
            capture_output=True,
            text=True,
            timeout=30,
            check=False,
        )

        self.assertEqual(0, result.returncode, result.stderr)
        self.assertIn("log_loop", result.stdout)
        self.assertIn("automod", result.stdout)
        self.assertNotIn("clear_cache", result.stdout)
        self.assertNotIn("set_map_rotation", result.stdout)

    def test_supervisor_processes_use_minimal_import_mode_but_cron_does_not(self):
        config = (REPO_ROOT / "config" / "supervisord.conf").read_text(encoding="utf-8")
        sections = {
            chunk.split("]", 1)[0]: chunk for chunk in config.split("[program:")[1:]
        }

        expected_minimal = {
            "auto_settings",
            "autobalancer",
            "automod",
            "blacklists",
            "broadcasts",
            "campaign_messages",
            "expiring_vips",
            "live_stats_refresh",
            "population_history",
            "log_event_loop",
            "log_recorder",
            "log_stream",
            "routines",
            "scoreboard",
            "seed_vip",
            "watch_killrate",
            "workers",
        }
        for program in expected_minimal:
            self.assertIn("HLL_SUPERVISOR_PROCESS=1", sections[program], program)

        self.assertNotIn("scheduler", sections)

        # Cron must retain the full CLI for enrich_db_users and custom RCON
        # commands configured by administrators.
        self.assertNotIn("HLL_SUPERVISOR_PROCESS", sections["cron"])

    def test_combined_config_replaces_only_compatible_services(self):
        config = (REPO_ROOT / "config" / "supervisord_combined.conf").read_text(
            encoding="utf-8"
        )
        sections = {
            chunk.split("]", 1)[0]: chunk for chunk in config.split("[program:")[1:]
        }

        self.assertIn("frontline_runtime", sections)
        for service in {
            "autobalancer",
            "blacklists",
            "expiring_vips",
            "live_stats_refresh",
            "population_history",
            "log_recorder",
            "routines",
            "auto_settings",
            "broadcasts",
        }:
            self.assertNotIn(service, sections)
        for isolated_service in {
            "automod",
            "campaign_messages",
            "log_event_loop",
            "scoreboard",
            "workers",
        }:
            self.assertIn(isolated_service, sections)


if __name__ == "__main__":
    unittest.main()
