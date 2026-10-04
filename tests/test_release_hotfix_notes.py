import importlib.util
import json
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest import TestCase
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    "verify_notes", ROOT / "scripts/verify_bundled_release.py"
)
verifier = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(verifier)


class HotfixReleaseNotesTests(TestCase):
    def snapshot(self, body, tag="v0.9.1"):
        return {"releases": [{
            "tag_name": tag, "name": f"Frontline RCON Suite {tag}",
            "body": body, "draft": False, "prerelease": False,
            "published_at": "2026-10-04T00:00:00Z",
        }]}

    def verify_snapshot(self, snapshot):
        with TemporaryDirectory() as directory:
            path = Path(directory) / "release_notes.json"
            path.write_text(json.dumps(snapshot), encoding="utf-8")
            with patch.object(verifier.channel, "SNAPSHOT_PATH", path):
                with redirect_stdout(StringIO()):
                    verifier.verify("v0.9.1")

    def test_bilingual_hotfix_has_no_automatic_feature_spotlight(self):
        body = (ROOT / "docs/releases/v0.9.1.md").read_text(encoding="utf-8")
        notes, highlights = verifier.channel.extract_highlights(body)
        self.assertIsNone(highlights)
        for text in ("## Deutsch", "## English", "Aurora", "CSRF"):
            self.assertIn(text, notes)
        self.verify_snapshot(self.snapshot(body))

    def test_no_highlights_does_not_bypass_reviewed_note_verification(self):
        with self.assertRaisesRegex(AssertionError, "notes differ"):
            self.verify_snapshot(self.snapshot("Unreviewed notes"))

    def test_previous_release_cannot_stand_in_for_the_hotfix(self):
        with self.assertRaisesRegex(AssertionError, "release missing"):
            self.verify_snapshot(self.snapshot("Old release", tag="v0.9.0"))
