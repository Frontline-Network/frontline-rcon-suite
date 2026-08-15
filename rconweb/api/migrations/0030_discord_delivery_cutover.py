from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0029_discord_report_integration")]

    operations = [
        migrations.AddField(
            model_name="discordreportintegration",
            name="delivery_started_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
