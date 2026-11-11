import os
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]


class EntrypointStartupTests(unittest.TestCase):
    def test_web_starts_when_orphaned_map_cleanup_fails(self):
        bash = os.environ.get("BASH") or shutil.which("bash")
        if bash is None:
            self.skipTest("bash is required for the entrypoint behavior test")

        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            bin_dir = root / "bin"
            web_dir = root / "rconweb"
            bin_dir.mkdir()
            web_dir.mkdir()

            shutil.copy2(REPO_ROOT / "entrypoint.sh", root / "entrypoint.sh")
            command_log = root / "commands.log"

            self._write_executable(
                bin_dir / "python",
                """#!/usr/bin/env bash
echo "python $*" >> "$COMMAND_LOG"
if [[ "$*" == *"remove_orphaned_map_ids"* ]]; then
  exit 1
fi
exit 0
""",
            )
            for command in ("daphne", "gunicorn"):
                self._write_executable(
                    bin_dir / command,
                    f"#!/usr/bin/env bash\necho \"{command} $*\" >> \"$COMMAND_LOG\"\n",
                )
            for manage_py in (root / "manage.py", web_dir / "manage.py"):
                self._write_executable(
                    manage_py,
                    "#!/usr/bin/env bash\necho \"manage.py $*\" >> \"$COMMAND_LOG\"\n",
                )

            env = os.environ.copy()
            env.update(
                {
                    "COMMAND_LOG": str(command_log),
                    "DONT_SEED_ADMIN_USER": "1",
                    "HLL_DB_PASSWORD": "test-password",
                    "HLL_HOST": "unreachable.example",
                    "NB_API_THREADS": "1",
                    "NB_API_WORKERS": "1",
                    "SERVER_NUMBER": "1",
                    "PATH": f"{bin_dir}{os.pathsep}{env['PATH']}",
                }
            )

            result = subprocess.run(
                [bash, "entrypoint.sh", "web"],
                cwd=root,
                env=env,
                capture_output=True,
                text=True,
                timeout=15,
                check=False,
            )

            self.assertEqual(0, result.returncode, result.stderr)
            self.assertNotIn(env["HLL_DB_PASSWORD"], result.stdout + result.stderr)
            self.assertIn("orphaned-map-id cleanup was deferred", result.stderr)
            commands = command_log.read_text(encoding="utf-8")
            self.assertIn("python -m rcon.cli remove_orphaned_map_ids", commands)
            self.assertIn("gunicorn", commands)
            self.assertIn("manage.py unregister_api", commands)

    @staticmethod
    def _write_executable(path, contents):
        path.write_text(contents, encoding="utf-8", newline="\n")
        path.chmod(0o755)


if __name__ == "__main__":
    unittest.main()
