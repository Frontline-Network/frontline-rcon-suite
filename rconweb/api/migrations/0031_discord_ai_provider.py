from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0030_discord_delivery_cutover")]

    operations = [
        migrations.AddField(
            model_name="discordreportintegration",
            name="ai_api_key_ciphertext",
            field=models.BinaryField(blank=True, default=bytes),
        ),
    ]
