from importlib import import_module

from django.db import migrations

PERMISSIONS = (
    ("can_view_autobalancer", "Can view autobalancer status and history"),
    (
        "can_change_autobalancer_config",
        "Can change the autobalancer configuration",
    ),
    (
        "can_execute_autobalancer",
        "Can approve or cancel autobalancer incidents",
    ),
)

_prior_migration = import_module(".0023_alter_rconuser_options", package=__package__)
PRIOR_OPTIONS = _prior_migration.Migration.operations[0].options


def add_permissions(apps, schema_editor):
    ContentType = apps.get_model("contenttypes", "ContentType")
    Permission = apps.get_model("auth", "Permission")
    content_type, _ = ContentType.objects.get_or_create(
        app_label="api", model="rconuser"
    )
    for codename, name in PERMISSIONS:
        Permission.objects.update_or_create(
            content_type=content_type,
            codename=codename,
            defaults={"name": name},
        )


def remove_permissions(apps, schema_editor):
    Permission = apps.get_model("auth", "Permission")
    Permission.objects.filter(
        content_type__app_label="api",
        content_type__model="rconuser",
        codename__in=[codename for codename, _ in PERMISSIONS],
    ).delete()


class Migration(migrations.Migration):
    dependencies = [("api", "0023_alter_rconuser_options")]

    operations = [
        migrations.AlterModelOptions(
            name="rconuser",
            options={
                **PRIOR_OPTIONS,
                "permissions": tuple(PRIOR_OPTIONS["permissions"]) + PERMISSIONS,
            },
        ),
        migrations.RunPython(add_permissions, remove_permissions),
    ]
