"""Preserve existing customer data through release migrations and retries."""

from django.contrib.auth.hashers import check_password, make_password
from django.core.management import call_command
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

    def test_existing_093_customer_configuration_survives_repeated_upgrade(self):
        executor = MigrationExecutor(connection)
        latest = executor.loader.graph.leaf_nodes()
        released = [("api", "0041_user_appearance_default")]
        try:
            executor.migrate(released)
            apps = executor.loader.project_state(released).apps
            user = apps.get_model("auth", "User").objects.create(
                username="customer-admin",
                email="admin@example.invalid",
                password=make_password("isolated-upgrade-password"),
                is_staff=True,
                is_active=True,
                is_superuser=False,
            )
            content_type = apps.get_model("contenttypes", "ContentType").objects.create(
                app_label="customer",
                model="upgrade_fixture",
            )
            permission = apps.get_model("auth", "Permission").objects.create(
                content_type_id=content_type.pk,
                codename="customer_read_reports",
                name="Customer report access",
            )
            group = apps.get_model("auth", "Group").objects.create(name="Customer junior admins")
            group.permissions.add(permission)
            user.groups.add(group)
            user.user_permissions.add(permission)
            fixtures = [user, group, permission]
            for model, values in (
                (
                    "DjangoAPIKey",
                    {
                        "user_id": user.pk,
                        "api_key": make_password("fixture-api-key"),
                        "notes": "Keep customer integration",
                    },
                ),
                (
                    "UserAppearancePreference",
                    {
                        "user_id": user.pk,
                        "preferences": {
                            "preset": "wardogs",
                            "mode": "dark",
                            "customAccent": "#123456",
                            "customerExtra": True,
                        },
                    },
                ),
                (
                    "UserLiveViewPreference",
                    {
                        "user_id": user.pk,
                        "preferences": {
                            "cards": {"score": True, "vips": False},
                            "customerExtra": ["keep"],
                        },
                    },
                ),
                (
                    "DiscordReportIntegration",
                    {
                        "enabled": True,
                        "guild_id": "123456789",
                        "channel_id": "987654321",
                        "service_url": "https://discord.example.invalid",
                        "moderator_role_ids": ["111", "222"],
                        "allowed_actions": ["message"],
                        "ai_config": {"enabled": False},
                        "policy": {"customerRule": True},
                        "ai_api_key_ciphertext": b"isolated-ciphertext-fixture",
                        "outbound_capability_ciphertext": b"isolated-capability-fixture",
                    },
                ),
            ):
                fixtures.append(apps.get_model("api", model).objects.create(**values))
            snapshots = []
            for record in fixtures:
                model = type(record)
                fields = [field.attname for field in model._meta.concrete_fields]
                snapshots.append(
                    (
                        model._meta.app_label,
                        model._meta.model_name,
                        record.pk,
                        fields,
                        model.objects.values(*fields).get(pk=record.pk),
                    )
                )

            for _ in range(2):
                call_command("migrate", interactive=False, verbosity=0)
                current = MigrationExecutor(connection).loader.project_state(latest).apps
                for app, model, key, fields, expected in snapshots:
                    self.assertEqual(
                        current.get_model(app, model).objects.values(*fields).get(pk=key),
                        expected,
                    )
                upgraded = current.get_model("auth", "User").objects.get(pk=user.pk)
                self.assertTrue(check_password("isolated-upgrade-password", upgraded.password))
                self.assertEqual(
                    list(upgraded.groups.values_list("pk", flat=True)), [group.pk]
                )
                self.assertEqual(
                    list(upgraded.user_permissions.values_list("pk", flat=True)),
                    [permission.pk],
                )
                upgraded_group = current.get_model("auth", "Group").objects.get(pk=group.pk)
                self.assertEqual(
                    list(upgraded_group.permissions.values_list("pk", flat=True)),
                    [permission.pk],
                )
                self.assertFalse(upgraded.is_superuser)
        finally:
            MigrationExecutor(connection).migrate(latest)
