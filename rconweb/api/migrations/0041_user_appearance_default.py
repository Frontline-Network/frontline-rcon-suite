import api.models
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0040_user_release_highlight_state")]

    operations = [
        migrations.AlterField(
            model_name="userappearancepreference",
            name="preferences",
            field=models.JSONField(default=api.models.default_user_appearance),
        ),
    ]
