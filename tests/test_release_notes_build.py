import importlib.util
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location("sync_notes", Path(__file__).parents[1] / "scripts/sync_release_notes.py")
sync = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(sync)


class ReleaseNotesBuildTests(TestCase):
    def test_ci_bundles_only_note_metadata_not_its_private_credential(self):
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "release_notes.json"
            items = [{"tag_name": "v0.8.8", "draft": False, "body": "Notes", "author": {"login": "owner"}, "html_url": "https://private"},
                     {"tag_name": "v0.8.9", "draft": True, "body": "Unpublished"}]
            with patch.object(sync.channel, "SNAPSHOT_PATH", destination), patch.object(sync.channel, "release_token", return_value="test-secret-never-copy"), patch.object(sync.channel, "github_json", return_value=items):
                sync.main()
            raw = destination.read_text()
            payload = json.loads(raw)
            self.assertEqual(len(payload["releases"]), 1)
            self.assertNotIn("test-secret-never-copy", raw)
            self.assertNotIn("https://private", raw)
            self.assertNotIn("author", raw)

    def test_failure_stops_build_without_overwriting_notes_or_printing_credentials(self):
        with TemporaryDirectory() as directory:
            destination = Path(directory) / "release_notes.json"
            destination.write_text("previous")
            with patch.object(sync.channel, "SNAPSHOT_PATH", destination), patch.object(sync.channel, "release_token", return_value="test-secret"), patch.object(sync.channel, "github_json", side_effect=OSError("test-secret")):
                with self.assertRaises(SystemExit) as failure:
                    sync.main()
            self.assertNotIn("test-secret", str(failure.exception))
            self.assertEqual(destination.read_text(), "previous")
