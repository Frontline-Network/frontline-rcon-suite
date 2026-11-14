"""French copy coverage and safety properties; no permissions are modified."""
import unittest
from types import SimpleNamespace

from .permission_help import ACTIONS, RESOURCES, permission_help
from .permission_help_fr import ACTIONS_FR, RESOURCES_FR


def permission(code, model="rconuser", app="api"):
    return SimpleNamespace(pk=7, codename=code, name=f"Can {code}",
                           content_type=SimpleNamespace(app_label=app, model=model, name=model))


class FrenchPermissionHelpTests(unittest.TestCase):
    def test_reviewed_catalogs_cover_every_known_action_and_resource(self):
        self.assertEqual(set(RESOURCES_FR), set(RESOURCES))
        self.assertEqual(set(ACTIONS_FR), set(ACTIONS))
        for key, scope in RESOURCES_FR.items():
            self.assertTrue(scope.strip(), key)
        for key, (title, description) in ACTIONS_FR.items():
            self.assertTrue(title.strip() and description.strip(), key)

    def test_all_read_and_change_permissions_keep_ids_and_safety_guidance(self):
        for resource in RESOURCES:
            for verb in ("view", "change"):
                with self.subTest(resource=resource, verb=verb):
                    value = permission(f"can_{verb}_{resource}")
                    english = permission_help(value, False)
                    french = permission_help(value, False, "fr")
                    for key in ("id", "code", "kind", "sensitive", "internal", "documented"):
                        self.assertEqual(french[key], english[key])
                    if verb == "view" and resource not in {"admins", "admin_ids", "admin_groups"}:
                        self.assertIn("ne permet aucune modification", french["description"])
                    if verb == "change" and f"change_{resource}" not in ACTIONS:
                        self.assertIn("modifier", french["description"])

    def test_all_actions_preserve_sensitivity_and_specific_scope(self):
        for action in ACTIONS:
            with self.subTest(action=action):
                value = permission("can_" + action)
                english = permission_help(value, False)
                french = permission_help(value, False, "fr")
                self.assertEqual((french["code"], french["kind"], french["sensitive"]),
                                 (english["code"], english["kind"], english["sensitive"]))
                self.assertTrue(french["title"] and french["description"])
        self.assertIn("ne le bannit pas", permission_help(permission("can_kick_players"), False, "fr")["description"])
        self.assertIn("groupes utilisateur RCON", permission_help(permission("can_remove_admin_roles"), False, "fr")["description"])

    def test_unknown_and_internal_permissions_are_not_guessed(self):
        unknown = permission_help(permission("can_future_extension"), False, "fr")
        self.assertFalse(unknown["documented"])
        self.assertIn("sans description CRCON vérifiée", unknown["description"])
        internal = permission_help(permission("change_contenttype", "contenttype", "contenttypes"), False, "fr")
        self.assertTrue(internal["internal"] and internal["sensitive"])
        self.assertIn("Django", internal["description"])
        self.assertIn("endommager", internal["description"])


if __name__ == "__main__":
    unittest.main()
