"""Reject unsafe rehearsal targets before any Docker mutation or DB connection."""

import importlib.util
from copy import deepcopy
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
    def preservation(self):
        return {
            "hashes": {"auth_user": "users", "user_config": "old-config", "alembic_version": "old-schema"},
            "counts": {"player_stats": 50},
            "configuration": {"3_CampaignsUserConfig": "customer-value"},
            "safe_new_configs": [],
            "schema_heads": ["old"],
        }

    def test_additive_upgrade_preserves_existing_data_and_safe_defaults(self):
        before = self.preservation()
        after = deepcopy(before)
        after["schema_heads"] = ["new"]
        after["hashes"].update(user_config="new-config", alembic_version="new-schema")
        after["configuration"]["3_VipRewardsUserConfig"] = "disabled-preview"
        after["safe_new_configs"] = ["3_VipRewardsUserConfig"]
        rehearsal.verify_preservation(before, after, ["new"])
        # Old application code can run on the additive schema, without downgrade.
        rehearsal.verify_preservation(before, after, ["new"])

    def test_preservation_rejects_customer_changes_and_unexpected_defaults(self):
        before = self.preservation()
        cases = []
        changed = deepcopy(before)
        changed["hashes"]["auth_user"] = "changed"
        cases.append(changed)
        changed = deepcopy(before)
        changed["counts"]["player_stats"] = 49
        cases.append(changed)
        for mutation in ("changed", None):
            changed = deepcopy(before)
            if mutation is None:
                del changed["configuration"]["3_CampaignsUserConfig"]
            else:
                changed["configuration"]["3_CampaignsUserConfig"] = mutation
            cases.append(changed)
        for key in ("3_VipRewardsUserConfig", "3_UnknownConfig"):
            changed = deepcopy(before)
            changed["configuration"][key] = "unsafe"
            cases.append(changed)
        changed = deepcopy(before)
        changed["schema_heads"] = ["wrong"]
        cases.append(changed)
        for after in cases:
            with self.subTest(after=after), self.assertRaises(RuntimeError):
                rehearsal.verify_preservation(before, after, ["old"])

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
