import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models

from api.live_view_preferences import default_user_live_view


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0035_tactical_archive_permission"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="UserLiveViewPreference",
            fields=[
                (
                    "id",
                    models.AutoField(
                        auto_created=True, primary_key=True,
                        serialize=False, verbose_name="ID",
                    ),
                ),
                ("preferences", models.JSONField(default=default_user_live_view)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                (
                    "user",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="live_view_preference",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={"default_permissions": ()},
        ),
    ]
