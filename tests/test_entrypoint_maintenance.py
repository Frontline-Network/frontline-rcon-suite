"""Run the real maintenance entrypoint against isolated command doubles."""

import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class MaintenanceEntrypointTests(unittest.TestCase):
    def run_maintenance(self, *, failure="", stale_marker=False):
        bash = os.environ.get("BASH") or shutil.which("bash")
        if bash is None:
            self.skipTest("bash is required for entrypoint behavior tests")
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            binary = root / "bin"
            web = root / "rconweb"
            binary.mkdir()
            web.mkdir()
            marker = web / "maintenance-container-healthy"
            if stale_marker:
                marker.touch()
            shutil.copy2(ROOT / "entrypoint.sh", root / "entrypoint.sh")
            commands = root / "commands.log"
            for name in ("alembic", "python", "sleep"):
                self.executable(
                    binary / name,
                    """#!/usr/bin/env bash
name="${0##*/}"
echo "$name $*" >> "$COMMAND_LOG"
if [[ "$name" == "$FAIL_STAGE" ]]; then exit 17; fi
# End the successful maintenance wait without reaching unrelated services.
if [[ "$name" == sleep ]]; then exit 42; fi
""",
                )
            self.executable(
                web / "manage.py",
                """#!/usr/bin/env bash
echo "manage.py $*" >> "$COMMAND_LOG"
if [[ "$1" == makemigrations ]]; then
  if [[ "$*" != *--check* || "$*" != *--dry-run* ]]; then
    touch generated-unreviewed-migration.py
    exit 0
  fi
  if [[ "$FAIL_STAGE" == model-drift ]]; then exit 19; fi
fi
if [[ "$1" == migrate && "$FAIL_STAGE" == migrate ]]; then exit 23; fi
""",
            )
            result = subprocess.run(
                [bash, "entrypoint.sh", "maintenance"],
                cwd=root,
                env={
                    **os.environ,
                    "COMMAND_LOG": str(commands),
                    "FAIL_STAGE": failure,
                    "SERVER_NUMBER": "4",
                    "PATH": f"{binary}{os.pathsep}{os.environ['PATH']}",
                },
                capture_output=True,
                text=True,
                timeout=10,
            )
            return (
                result,
                commands.read_text() if commands.exists() else "",
                marker.exists(),
                (web / "generated-unreviewed-migration.py").exists(),
            )

    @staticmethod
    def executable(path, text):
        path.write_text(text, encoding="utf-8", newline="\n")
        path.chmod(0o755)

    def test_shipped_migrations_are_checked_and_applied_before_readiness(self):
        result, commands, ready, generated = self.run_maintenance(stale_marker=True)
        self.assertEqual(result.returncode, 42, result.stderr)
        self.assertFalse(generated)
        self.assertTrue(ready)
        self.assertLess(commands.index("makemigrations"), commands.index("manage.py migrate"))
        self.assertLess(commands.index("manage.py migrate"), commands.index("sleep infinity"))

    def test_model_drift_does_not_generate_files_apply_django_or_reuse_readiness(self):
        result, commands, ready, generated = self.run_maintenance(
            failure="model-drift", stale_marker=True
        )
        self.assertEqual(result.returncode, 19, result.stderr)
        self.assertFalse(generated)
        self.assertFalse(ready)
        self.assertNotIn("manage.py migrate ", commands)
        self.assertNotIn("sleep infinity", commands)

    def test_failed_migrations_never_reuse_a_stale_success_marker(self):
        for stage, status in (("alembic", 17), ("migrate", 23)):
            with self.subTest(stage=stage):
                result, commands, ready, generated = self.run_maintenance(
                    failure=stage, stale_marker=True
                )
                self.assertEqual(result.returncode, status, result.stderr)
                self.assertFalse(ready)
                self.assertFalse(generated)
                self.assertNotIn("sleep infinity", commands)
