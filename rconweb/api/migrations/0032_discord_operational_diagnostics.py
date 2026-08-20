from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0031_discord_ai_provider")]

    operations = [
        migrations.AddField(
            model_name="discordreportintegration",
            name="last_test_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="discordreportintegration",
            name="last_test_success",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="discordreportintegration",
            name="last_test_error",
            field=models.CharField(blank=True, default="", max_length=128),
        ),
        migrations.AddField(
            model_name="discordreportintegration",
            name="last_diagnostic_at",
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AddField(
            model_name="discordreportintegration",
            name="last_diagnostic_result",
            field=models.JSONField(default=dict),
        ),
    ]
