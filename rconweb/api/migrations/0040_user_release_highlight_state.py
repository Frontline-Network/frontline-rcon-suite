from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0039_population_history_permissions"),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]
    operations = [
        migrations.CreateModel(
            name="UserReleaseHighlightState",
            fields=[
                ("id", models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("release_version", models.CharField(max_length=64)),
                ("seen", models.BooleanField(default=False)),
                ("snoozed_until", models.DateTimeField(blank=True, null=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("user", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="release_highlight_states", to=settings.AUTH_USER_MODEL)),
            ],
            options={"default_permissions": (), "constraints": [models.UniqueConstraint(fields=("user", "release_version"), name="unique_user_release_highlights")]},
        ),
    ]
