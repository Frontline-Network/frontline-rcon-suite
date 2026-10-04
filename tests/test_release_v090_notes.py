import importlib.util
from pathlib import Path
from unittest import TestCase

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("release_channel", ROOT / "rcon/release_channel.py")
channel = importlib.util.module_from_spec(spec)
spec.loader.exec_module(channel)


class ReleaseV090NotesTests(TestCase):
    def test_reviewed_notes_use_the_real_highlight_parser(self):
        body = (ROOT / "docs/releases/v0.9.0.md").read_text(encoding="utf-8")
        self.assertEqual(len(channel.HIGHLIGHT_BLOCK.findall(body)), 1)
        notes, highlights = channel.extract_highlights(body)
        self.assertIsNotNone(highlights)
        self.assertNotIn("crcon-highlights", notes)
        self.assertEqual(highlights["image"], "theme-collection")
        self.assertEqual(highlights["action"]["id"], "appearance")
        for language in ("de", "en"):
            for key in ("title", "description", "image_alt"):
                self.assertTrue(highlights[key][language])
            self.assertTrue(highlights["action"]["label"][language])
        self.assertLessEqual(len(highlights["items"]), 2)
        self.assertNotIn("https://", str(highlights))
        self.assertNotIn("Mirage", str(highlights))
