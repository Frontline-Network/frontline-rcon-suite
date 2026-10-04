from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("api", "0038_leadership_vote_permission")]
    operations = [
        migrations.CreateModel(
            name="PopulationHistoryAccess",
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
                    (
                        "can_view_population_history",
                        "Can read population history and seeding attempts",
                    ),
                    (
                        "can_mark_seeding_sessions",
                        "Can start and end manual seeding attempts",
                    ),
                ),
            },
        )
    ]
