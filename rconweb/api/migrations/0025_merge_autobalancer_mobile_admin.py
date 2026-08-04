from django.db import migrations


class Migration(migrations.Migration):
    """Merge the parallel Autobalancer and Mobile Admin 0024 migrations."""

    dependencies = [
        ("api", "0024_add_autobalancer_permissions"),
        ("api", "0024_mobile_admin_auth"),
    ]

    operations = []
