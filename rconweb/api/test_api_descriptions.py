"""Keep the published API snapshot complete and its source metadata intact."""

import copy
import json
import unittest
from pathlib import Path

from .api_descriptions import describe_api_endpoints, endpoint_descriptions


class ApiDescriptionTests(unittest.TestCase):
    def test_every_published_endpoint_has_both_languages(self):
        snapshot = Path(__file__).resolve().parents[2] / (
            "rcongui/src/mirage/data/api-documentation.json"
        )
        entries = json.loads(snapshot.read_text(encoding="utf-8"))
        self.assertTrue(entries)
        self.assertEqual(len(entries), len({entry["endpoint"] for entry in entries}))
        for entry in entries:
            with self.subTest(endpoint=entry["endpoint"]):
                translations = endpoint_descriptions(entry["endpoint"])
                self.assertEqual(set(translations), {"de", "en"})
                self.assertTrue(all(text.strip() for text in translations.values()))
                self.assertEqual(entry["description_translations"], translations)

    def test_enrichment_preserves_permissions_methods_and_original_docs(self):
        entries = [{
            "endpoint": "get_bans",
            "doc_string": "Original technical notes",
            "arguments": {"player_id": {"default": None, "annotation": "str"}},
            "permissions_required": ["api.can_view_temp_bans", "api.can_view_perma_bans"],
            "allowed_http_methods": ["GET", "POST"],
        }]
        original = copy.deepcopy(entries)
        enriched = describe_api_endpoints(entries)
        self.assertEqual(entries, original)
        self.assertIsNot(enriched[0], entries[0])
        self.assertEqual(
            {k: v for k, v in enriched[0].items() if k != "description_translations"},
            original[0],
        )
        self.assertEqual(set(enriched[0]["description_translations"]), {"de", "en"})

    def test_unknown_endpoint_does_not_acquire_guessed_semantics(self):
        for name in ("get_future_config", "set_future_config", "validate_future_config"):
            self.assertEqual(endpoint_descriptions(name), {})
        original = {"endpoint": "get_future_config", "doc_string": "Vendor documentation"}
        enriched = describe_api_endpoints([original])[0]
        self.assertEqual(enriched["doc_string"], original["doc_string"])
        self.assertEqual(enriched["description_translations"], {})


if __name__ == "__main__":
    unittest.main()
