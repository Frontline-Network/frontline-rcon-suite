from django.contrib.auth import get_user_model
from django.contrib.auth.models import Permission
from django.db import connection
from django.db.migrations.loader import MigrationLoader
from django.test import SimpleTestCase, TestCase
from unittest.mock import patch
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig


class LeadershipMigrationTests(TestCase):
    @patch("api.auth.set_registered_mods")
    def test_permission_migrated_without_automatic_assignment(self, _registered_mods):
        permission = Permission.objects.get(codename="can_manage_leadership_votes")
        user = get_user_model().objects.create_user(username="ordinary-admin")
        self.assertEqual(permission.content_type.app_label, "api")
        self.assertFalse(user.has_perm("api.can_manage_leadership_votes"))
        user.user_permissions.add(permission)
        user = get_user_model().objects.get(pk=user.pk)
        self.assertTrue(user.has_perm("api.can_manage_leadership_votes"))

    def test_single_head_and_safe_defaults(self):
        self.assertEqual(
            MigrationLoader(connection).graph.leaf_nodes("api"),
            [("api", "0038_leadership_vote_permission")],
        )
        self.assertFalse(LeadershipVoteUserConfig().enabled)
        self.assertEqual(LeadershipVoteUserConfig().mode, "dry_run")


class LeadershipMessageEndpointTests(SimpleTestCase):
    def test_information_sender_is_not_a_public_moderation_bypass(self):
        import inspect
        from api import views

        for endpoints in (views.ENDPOINT_PERMISSIONS, views.RCON_ENDPOINT_HTTP_METHODS):
            names = {function.__name__ for function in endpoints}
            self.assertIn("message_player", names)
            self.assertNotIn("message_player_info", names)
            self.assertNotIn("_send_player_message", names)
        self.assertEqual(
            set(inspect.signature(views.rcon_api.message_player).parameters),
            {"player_id", "message", "by", "save_message", "player_name"},
        )
