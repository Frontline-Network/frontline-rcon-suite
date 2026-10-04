"""Upgrade an existing appearance record through the release migrations."""
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import TransactionTestCase


class ReleaseMigrationTests(TransactionTestCase):
    def test_0039_to_0041_preserves_preferences_and_creates_highlight_state(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        before = [("api", "0039_population_history_permissions")]
        try:
            executor.migrate(before)
            apps = executor.loader.project_state(before).apps
            user = apps.get_model("auth", "User").objects.create(username="migration-reader")
            original = {"preset": "wardogs", "mode": "dark", "wardogsStyle": "blue"}
            record = apps.get_model("api", "UserAppearancePreference").objects.create(
                user_id=user.pk, preferences=original, id=2**31 + 42
            )
            executor = MigrationExecutor(connection)
            executor.migrate(latest)
            apps = executor.loader.project_state(latest).apps
            appearance = apps.get_model("api", "UserAppearancePreference")
            self.assertEqual(appearance.objects.get(pk=record.pk).preferences, original)
            self.assertEqual(appearance._meta.pk.get_internal_type(), "BigAutoField")
            state = apps.get_model("api", "UserReleaseHighlightState").objects.create(
                user_id=user.pk, release_version="v0.9.0", seen=True
            )
            self.assertTrue(state.seen)
            defaults = appearance._meta.get_field("preferences").get_default()
            defaults["wardogsShortcuts"].append("/updates")
            self.assertNotIn("/updates", appearance._meta.get_field("preferences").get_default()["wardogsShortcuts"])
        finally:
            MigrationExecutor(connection).migrate(latest)
