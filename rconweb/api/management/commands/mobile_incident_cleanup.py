import os
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import MobileAccessToken, MobilePairing
from rcon.admin_incidents import purge_old_incidents


class Command(BaseCommand):
    help = "Delete mobile incidents older than the configured retention period"

    def handle(self, *args, **options):
        try:
            retention_days = max(
                1, int(os.getenv("MOBILE_INCIDENT_RETENTION_DAYS", "90"))
            )
        except ValueError:
            retention_days = 90
        deleted = purge_old_incidents(retention_days)
        now = timezone.now()
        access_tokens, _ = MobileAccessToken.objects.filter(
            expires_at__lte=now
        ).delete()
        pairings, _ = MobilePairing.objects.filter(
            expires_at__lte=now - timedelta(days=1)
        ).delete()
        self.stdout.write(
            f"Deleted {deleted} incidents, {access_tokens} access tokens and "
            f"{pairings} expired pairings"
        )
