from django.db import migrations


class Migration(migrations.Migration):
    dependencies = [("api", "0034_tactical_permissions")]
    operations = [
        migrations.AlterModelOptions(
            name="tacticalaccess",
            options={
                "managed": False,
                "default_permissions": (),
                "permissions": (
                    ("can_view_live_map", "Can view private tactical positions and history"),
                    ("can_manage_live_map", "Can configure tactical collection and protected players"),
                    ("can_view_live_map_cases", "Can access private tactical case evidence"),
                    ("can_manage_live_map_archives", "Can create, extend and delete tactical round archives"),
                ),
            },
        )
    ]
