import importlib.util
import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import Mock, patch

VERSION_MODULE_PATH = Path(__file__).resolve().parents[1] / "rcon" / "version.py"
VERSION_SPEC = importlib.util.spec_from_file_location("crcon_version", VERSION_MODULE_PATH)
version_module = importlib.util.module_from_spec(VERSION_SPEC)
VERSION_SPEC.loader.exec_module(version_module)
get_version = version_module.get_version


class VersionTests(unittest.TestCase):
    def test_configured_version_wins(self):
        with patch.dict(os.environ, {"CRCON_VERSION": "v0.3.3"}, clear=False):
            self.assertEqual(get_version(), "v0.3.3")

    def test_version_file_is_used_without_git(self):
        with tempfile.TemporaryDirectory() as directory:
            version_file = Path(directory) / "tag_version"
            version_file.write_text("v0.3.3\n", encoding="utf-8")

            with patch.dict(os.environ, {}, clear=True), patch.object(
                version_module, "_VERSION_FILES", (version_file,)
            ), patch.object(version_module, "run") as git_run:
                self.assertEqual(get_version(), "v0.3.3")
                git_run.assert_not_called()

    def test_failed_git_lookup_returns_unknown(self):
        result = Mock(returncode=128, stdout=b"")

        with patch.dict(os.environ, {}, clear=True), patch.object(
            version_module, "_VERSION_FILES", (Path("/missing"),)
        ), patch.object(version_module, "run", return_value=result):
            self.assertEqual(get_version(), "unknown")


if __name__ == "__main__":
    unittest.main()
