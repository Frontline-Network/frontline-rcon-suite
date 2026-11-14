"""Keep the published API snapshot complete and its source metadata intact."""

import copy
import json
import re
import unittest
from pathlib import Path

from .api_descriptions import CONFIG_SUBJECTS, DESCRIPTIONS, describe_api_endpoints, endpoint_descriptions
from .api_descriptions_fr import CONFIG_SUBJECTS_FR, DESCRIPTIONS_FR


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
                self.assertEqual(set(translations), {"de", "en", "fr"})
                self.assertTrue(all(text.strip() for text in translations.values()))
                self.assertEqual(entry["description_translations"], {k: translations[k] for k in ("de", "en")})

    def test_french_subjects_cover_config_families_and_are_not_guessed(self):
        self.assertEqual(set(CONFIG_SUBJECTS_FR), set(CONFIG_SUBJECTS))
        self.assertEqual(set(DESCRIPTIONS_FR), set(DESCRIPTIONS))
        self.assertTrue(all(value.strip() for value in CONFIG_SUBJECTS_FR.values()))
        self.assertTrue(all(value.strip() for value in DESCRIPTIONS_FR.values()))
        for subject in CONFIG_SUBJECTS:
            for prefix in ("get_", "describe_", "validate_", "set_"):
                self.assertTrue(endpoint_descriptions(prefix + subject)["fr"].strip())

    def test_french_keeps_technical_identifiers_and_placeholders(self):
        token = re.compile(r"\{[a-z_]+\}|\b[a-z][a-z0-9]*_[a-z0-9_]+\b")
        for name, (_, english) in DESCRIPTIONS.items():
            with self.subTest(endpoint=name):
                self.assertTrue(set(token.findall(english)).issubset(token.findall(DESCRIPTIONS_FR[name])))

    def test_french_sensitive_api_descriptions_preserve_semantics_and_identifiers(self):
        self.assertIn("ne", endpoint_descriptions("kick")["fr"])
        self.assertIn("n'empêche pas", endpoint_descriptions("kick")["fr"])
        self.assertIn("duration_hours", endpoint_descriptions("temp_ban")["fr"])
        self.assertIn("remove_temp_ban", endpoint_descriptions("temp_ban")["fr"])
        self.assertIn("unblacklist_player", endpoint_descriptions("unban")["fr"])
        self.assertIn("ne sont pas supprimées", endpoint_descriptions("remove_perma_ban")["fr"])

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
        self.assertTrue({"de", "en"}.issubset(enriched[0]["description_translations"]))

    def test_unknown_endpoint_does_not_acquire_guessed_semantics(self):
        for name in ("get_future_config", "set_future_config", "validate_future_config"):
            self.assertEqual(endpoint_descriptions(name), {})
        original = {"endpoint": "get_future_config", "doc_string": "Vendor documentation"}
        enriched = describe_api_endpoints([original])[0]
        self.assertEqual(enriched["doc_string"], original["doc_string"])
        self.assertEqual(enriched["description_translations"], {})


if __name__ == "__main__":
    unittest.main()
