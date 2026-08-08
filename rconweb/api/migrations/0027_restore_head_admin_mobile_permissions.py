"""Restore the mobile-admin permissions for the Frontline head-admin group.

The first Mobile Admin migration only knew CRCON's three stock group names.
Existing Frontline installations also use ``head-admin``; leaving that group
without its mobile permissions makes the Apps setup page return 403 although
the permissions themselves exist in Django's admin.
"""

from django.db import migrations


MOBILE_PERMISSIONS = (
    "can_manage_own_mobile_devices",
    "can_view_admin_incidents",
    "can_create_admin_incidents",
    "can_claim_admin_incidents",
    "can_resolve_admin_incidents",
    "can_reassign_admin_incidents",
)


def restore_head_admin_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")

    # Do not create a new role on installations that do not use Frontline's
    # optional head-admin group.
    group = Group.objects.filter(name="head-admin").first()
    if group is None:
        return

    permissions = Permission.objects.filter(
        content_type__app_label="api",
        content_type__model="mobiledevice",
        codename__in=MOBILE_PERMISSIONS,
    )
    group.permissions.add(*permissions)


def remove_head_admin_permissions(apps, schema_editor):
    Group = apps.get_model("auth", "Group")
    Permission = apps.get_model("auth", "Permission")
    group = Group.objects.filter(name="head-admin").first()
    if group is None:
        return

    permissions = Permission.objects.filter(
        content_type__app_label="api",
        content_type__model="mobiledevice",
        codename__in=MOBILE_PERMISSIONS,
    )
    group.permissions.remove(*permissions)


class Migration(migrations.Migration):
    dependencies = [("api", "0026_desktop_device_code_pairing")]

    operations = [
        migrations.RunPython(
            restore_head_admin_permissions,
            remove_head_admin_permissions,
        )
    ]
