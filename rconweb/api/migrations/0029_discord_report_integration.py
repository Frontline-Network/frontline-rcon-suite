import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0028_votemap_permissions")]

    operations = [
        migrations.CreateModel(
            name="DiscordReportIntegration",
            fields=[
                (
                    "id",
                    models.PositiveSmallIntegerField(
                        default=1, editable=False, primary_key=True, serialize=False
                    ),
                ),
                (
                    "installation_id",
                    models.UUIDField(default=uuid.uuid4, editable=False, unique=True),
                ),
                ("enabled", models.BooleanField(default=False)),
                (
                    "service_url",
                    models.URLField(blank=True, default="", max_length=500),
                ),
                ("guild_id", models.CharField(blank=True, default="", max_length=32)),
                (
                    "guild_name",
                    models.CharField(blank=True, default="", max_length=128),
                ),
                ("channel_id", models.CharField(blank=True, default="", max_length=32)),
                (
                    "channel_name",
                    models.CharField(blank=True, default="", max_length=128),
                ),
                ("moderator_role_ids", models.JSONField(default=list)),
                ("allowed_actions", models.JSONField(default=list)),
                ("language", models.CharField(default="de", max_length=2)),
                ("ai_config", models.JSONField(default=dict)),
                ("policy", models.JSONField(default=dict)),
                ("reporter_templates", models.JSONField(default=dict)),
                (
                    "inbound_capability_digest",
                    models.CharField(blank=True, default="", max_length=64),
                ),
                (
                    "outbound_capability_ciphertext",
                    models.BinaryField(blank=True, default=bytes),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "default_permissions": (),
                "permissions": (
                    (
                        "can_manage_discord_report_bot",
                        "Can configure the Discord report bot and AI moderation",
                    ),
                ),
            },
        ),
        migrations.CreateModel(
            name="DiscordPairing",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("secret_digest", models.CharField(max_length=64, unique=True)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("consumed", "Consumed"),
                            ("expired", "Expired"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={"default_permissions": ()},
        ),
        migrations.CreateModel(
            name="DiscordPreparedAction",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("incident_id", models.UUIDField(db_index=True)),
                ("incident_revision", models.PositiveIntegerField()),
                ("interaction_id", models.CharField(max_length=32, unique=True)),
                ("action", models.CharField(max_length=32)),
                ("actor", models.JSONField(default=dict)),
                ("arguments", models.JSONField(default=dict)),
                ("confirmation_digest", models.CharField(max_length=64, unique=True)),
                (
                    "confirmation_ciphertext",
                    models.BinaryField(blank=True, default=bytes),
                ),
                ("preview", models.TextField()),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("executed_at", models.DateTimeField(blank=True, null=True)),
                ("execution_result", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"default_permissions": ()},
        ),
        migrations.CreateModel(
            name="DiscordInteractionReceipt",
            fields=[
                (
                    "interaction_id",
                    models.CharField(max_length=32, primary_key=True, serialize=False),
                ),
                ("operation", models.CharField(max_length=32)),
                ("result", models.JSONField(default=dict)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"default_permissions": ()},
        ),
        migrations.CreateModel(
            name="DiscordModerationFeedback",
            fields=[
                (
                    "id",
                    models.UUIDField(
                        default=uuid.uuid4,
                        editable=False,
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                ("incident_id", models.UUIDField(db_index=True)),
                ("analysis_id", models.UUIDField(db_index=True)),
                ("actor", models.JSONField(default=dict)),
                ("decision", models.CharField(max_length=16)),
                ("actual_action", models.CharField(max_length=32)),
                ("reason", models.TextField(blank=True, default="")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={"default_permissions": ()},
        ),
    ]
