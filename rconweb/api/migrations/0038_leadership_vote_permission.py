from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0037_merge_eventador_live_view")]
    operations = [
        migrations.CreateModel(
            name="LeadershipVoteAccess",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                )
            ],
            options={
                "managed": False,
                "default_permissions": (),
                "permissions": (
                    ("can_manage_leadership_votes", "Can configure leadership votes"),
                ),
            },
        )
    ]
