from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0033_user_appearance_preference")]
    operations = [migrations.CreateModel(
        name="TacticalAccess",
        fields=[("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID"))],
        options={"managed": False, "default_permissions": (), "permissions": (
            ("can_view_live_map", "Can view private tactical positions and history"),
            ("can_manage_live_map", "Can configure tactical collection and protected players"),
            ("can_view_live_map_cases", "Can access private tactical case evidence"),
        )},
    )]
