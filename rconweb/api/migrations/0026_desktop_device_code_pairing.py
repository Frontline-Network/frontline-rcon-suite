# Generated manually for the CRCON Windows device-code authorization flow.

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("api", "0025_merge_autobalancer_mobile_admin"),
    ]

    operations = [
        migrations.AlterField(
            model_name="mobilepairing",
            name="user",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.CASCADE,
                related_name="mobile_pairings",
                to="auth.user",
            ),
        ),
        migrations.AddField(
            model_name="mobilepairing",
            name="kind",
            field=models.CharField(
                choices=[("qr", "QR"), ("desktop", "Desktop device code")],
                default="qr",
                max_length=16,
            ),
        ),
        migrations.AddField(
            model_name="mobilepairing",
            name="user_code_digest",
            field=models.CharField(
                blank=True,
                max_length=64,
                null=True,
                unique=True,
            ),
        ),
    ]
