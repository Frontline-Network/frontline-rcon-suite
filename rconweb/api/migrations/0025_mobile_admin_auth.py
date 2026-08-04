# Generated manually for the CRCON mobile admin integration.

import uuid

import django.db.models.deletion
from django.db import migrations, models

MOBILE_PERMISSIONS = {
    "can_manage_own_mobile_devices": "Can pair and revoke own mobile devices",
    "can_manage_all_mobile_devices": "Can inspect and revoke all mobile devices",
    "can_view_admin_incidents": "Can view mobile admin incidents",
    "can_create_admin_incidents": "Can create mobile admin incidents",
    "can_claim_admin_incidents": "Can claim mobile admin incidents",
    "can_resolve_admin_incidents": "Can resolve mobile admin incidents",
    "can_reassign_admin_incidents": "Can reassign mobile admin incidents",
}

GROUP_PERMISSIONS = {
    "owner": tuple(MOBILE_PERMISSIONS),
    "admin": (
        "can_manage_own_mobile_devices",
        "can_view_admin_incidents",
        "can_create_admin_incidents",
        "can_claim_admin_incidents",
        "can_resolve_admin_incidents",
        "can_reassign_admin_incidents",
    ),
    "moderator": (
        "can_manage_own_mobile_devices",
        "can_view_admin_incidents",
        "can_create_admin_incidents",
        "can_claim_admin_incidents",
        "can_resolve_admin_incidents",
    ),
}


def create_mobile_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    ContentType = apps.get_model("contenttypes", "ContentType")
    MobileDevice = apps.get_model("api", "MobileDevice")

    content_type, _ = ContentType.objects.get_or_create(
        app_label="api", model=MobileDevice._meta.model_name
    )
    permissions = {}
    for codename, name in MOBILE_PERMISSIONS.items():
        permission, _ = Permission.objects.get_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )
        permissions[codename] = permission

    for group_name, codenames in GROUP_PERMISSIONS.items():
        group, _ = Group.objects.get_or_create(name=group_name)
        group.permissions.add(*(permissions[codename] for codename in codenames))


def remove_mobile_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    Permission.objects.filter(codename__in=MOBILE_PERMISSIONS).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0024_add_autobalancer_permissions"),
    ]

    operations = [
        migrations.CreateModel(
            name="MobileDevice",
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
                ("name", models.CharField(max_length=128)),
                ("platform", models.CharField(max_length=32)),
                (
                    "app_version",
                    models.CharField(blank=True, default="", max_length=32),
                ),
                (
                    "refresh_token_digest",
                    models.CharField(blank=True, max_length=64, null=True, unique=True),
                ),
                ("refresh_expires_at", models.DateTimeField(blank=True, null=True)),
                ("absolute_expires_at", models.DateTimeField(blank=True, null=True)),
                (
                    "push_handle",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "push_capability",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("notifications_enabled", models.BooleanField(default=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("last_seen_at", models.DateTimeField(blank=True, null=True)),
                ("revoked_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mobile_devices",
                        to="auth.user",
                    ),
                ),
            ],
            options={
                "ordering": ("-created_at",),
                "default_permissions": (),
                "permissions": (
                    (
                        "can_manage_own_mobile_devices",
                        "Can pair and revoke own mobile devices",
                    ),
                    (
                        "can_manage_all_mobile_devices",
                        "Can inspect and revoke all mobile devices",
                    ),
                    ("can_view_admin_incidents", "Can view mobile admin incidents"),
                    (
                        "can_create_admin_incidents",
                        "Can create mobile admin incidents",
                    ),
                    ("can_claim_admin_incidents", "Can claim mobile admin incidents"),
                    (
                        "can_resolve_admin_incidents",
                        "Can resolve mobile admin incidents",
                    ),
                    (
                        "can_reassign_admin_incidents",
                        "Can reassign mobile admin incidents",
                    ),
                ),
            },
        ),
        migrations.CreateModel(
            name="MobilePairing",
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
                    "exchange_token_digest",
                    models.CharField(blank=True, max_length=64, null=True, unique=True),
                ),
                (
                    "verification_code",
                    models.CharField(blank=True, default="", max_length=6),
                ),
                (
                    "state",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("scanned", "Scanned"),
                            ("approved", "Approved"),
                            ("denied", "Denied"),
                            ("consumed", "Consumed"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                (
                    "device_name",
                    models.CharField(blank=True, default="", max_length=128),
                ),
                ("platform", models.CharField(blank=True, default="", max_length=32)),
                (
                    "app_version",
                    models.CharField(blank=True, default="", max_length=32),
                ),
                (
                    "push_handle",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                (
                    "push_capability",
                    models.CharField(blank=True, default="", max_length=255),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                ("scanned_at", models.DateTimeField(blank=True, null=True)),
                ("approved_at", models.DateTimeField(blank=True, null=True)),
                ("consumed_at", models.DateTimeField(blank=True, null=True)),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="mobile_pairings",
                        to="auth.user",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",), "default_permissions": ()},
        ),
        migrations.CreateModel(
            name="MobileAccessToken",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        primary_key=True,
                        serialize=False,
                    ),
                ),
                (
                    "token_digest",
                    models.CharField(db_index=True, max_length=64, unique=True),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("expires_at", models.DateTimeField()),
                (
                    "device",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="access_tokens",
                        to="api.mobiledevice",
                    ),
                ),
            ],
            options={"ordering": ("-created_at",), "default_permissions": ()},
        ),
        migrations.RunPython(create_mobile_permissions, remove_mobile_permissions),
    ]
