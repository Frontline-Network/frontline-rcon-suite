from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Run the private tactical collector (disabled until configured)"

    def handle(self, *args, **options):
        from rcon.live_map.service import run
        run()
