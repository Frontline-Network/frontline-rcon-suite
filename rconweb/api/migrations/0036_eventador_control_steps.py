import uuid

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0035_tactical_archive_permission")]

    operations = [
        migrations.CreateModel(
            name="EventadorControlStep",
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
                ("event_id", models.UUIDField(db_index=True)),
                ("event_revision", models.PositiveIntegerField()),
                ("workflow_revision", models.PositiveIntegerField()),
                ("step_id", models.CharField(max_length=64)),
                ("idempotency_key", models.UUIDField(unique=True)),
                ("plan", models.JSONField()),
                ("plan_digest", models.CharField(max_length=64)),
                ("prepared_by", models.CharField(max_length=150)),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("prepared", "Prepared"),
                            ("executing", "Executing"),
                            ("succeeded", "Succeeded"),
                            ("conflict", "Conflict"),
                            ("failed", "Failed"),
                            ("unknown", "Unknown"),
                        ],
                        db_index=True,
                        default="prepared",
                        max_length=16,
                    ),
                ),
                ("execute_at", models.DateTimeField()),
                ("expires_at", models.DateTimeField(db_index=True)),
                ("execution_started_at", models.DateTimeField(blank=True, null=True)),
                ("finished_at", models.DateTimeField(blank=True, null=True)),
                ("result", models.JSONField(default=dict)),
                ("error_code", models.CharField(blank=True, max_length=64, null=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "default_permissions": (),
                "permissions": (
                    (
                        "can_control_eventador_events",
                        "Can prepare and execute Eventador match-control steps",
                    ),
                ),
                "constraints": [
                    models.UniqueConstraint(
                        fields=("event_id", "workflow_revision", "step_id"),
                        name="api_eventador_step_scope_unique",
                    )
                ],
            },
        )
    ]
