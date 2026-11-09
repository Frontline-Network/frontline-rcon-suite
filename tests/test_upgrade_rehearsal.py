"""Reject unsafe rehearsal targets before any Docker mutation or DB connection."""

import importlib.util
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "upgrade_rehearsal", ROOT / "scripts/rehearse_upgrade.py"
)
rehearsal = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(rehearsal)


class UpgradeRehearsalSafetyTests(unittest.TestCase):
    def test_existing_directory_is_never_used_as_a_new_rehearsal(self):
        with tempfile.TemporaryDirectory() as folder:
            runner = rehearsal.Rehearsal(Path(folder))
            runner.command = Mock()
            with self.assertRaisesRegex(RuntimeError, "new, empty"):
                runner.prepare(None)
            runner.command.assert_not_called()

    def runner(self, folder, **changes):
        runner = rehearsal.Rehearsal(Path(folder))
        runner.state = {
            "token": "test-owner",
            "containers": {"postgres": {"id": "test-id"}},
        }
        current = {
            "Id": "test-id",
            "Config": {"Labels": {rehearsal.LABEL: "test-owner"}},
            "HostConfig": {"NetworkMode": "none", "PortBindings": {}},
        }
        for section, values in changes.items():
            current[section].update(values)
        runner.inspect = Mock(return_value=current)
        runner.command = Mock()
        return runner

    def test_cleanup_refuses_a_container_with_another_owner(self):
        with tempfile.TemporaryDirectory() as folder:
            runner = self.runner(
                folder, Config={"Labels": {rehearsal.LABEL: "customer"}}
            )
            with self.assertRaisesRegex(RuntimeError, "ownership"):
                runner.cleanup()
            runner.command.assert_not_called()

    def test_cleanup_refuses_published_ports_and_live_networks(self):
        for unsafe in ({"NetworkMode": "bridge"}, {"PortBindings": {"5432/tcp": [{}]}}):
            with self.subTest(unsafe=unsafe), tempfile.TemporaryDirectory() as folder:
                runner = self.runner(folder, HostConfig=unsafe)
                with self.assertRaises(RuntimeError):
                    runner.cleanup()
                runner.command.assert_not_called()

    def test_probe_rejects_live_database_before_importing_django(self):
        for flag, host in (("", "127.0.0.1"), ("isolated", "production-db")):
            with self.subTest(flag=flag, host=host):
                process = subprocess.run(
                    [sys.executable, str(ROOT / "scripts/upgrade_probe.py"), "seed"],
                    env={
                        **os.environ,
                        "CRCON_UPGRADE_REHEARSAL": flag,
                        "HLL_DB_HOST": host,
                    },
                    capture_output=True,
                    text=True,
                    timeout=10,
                )
                self.assertNotEqual(process.returncode, 0)
                self.assertIn("RuntimeError", process.stderr)
                self.assertNotIn("ModuleNotFoundError", process.stderr)


if __name__ == "__main__":
    unittest.main()
