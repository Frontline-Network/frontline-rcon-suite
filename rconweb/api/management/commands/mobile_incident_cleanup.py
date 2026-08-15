from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from api.models import MobileAccessToken, MobilePairing
from rcon.admin_incidents import purge_old_incidents
from rcon.incident_settings import incident_retention_days
from rcon.moderation_store import purge_shadow_reviews


class Command(BaseCommand):
    help = "Delete mobile incidents older than the configured retention period"

    def handle(self, *args, **options):
        retention_days = incident_retention_days()
        deleted = purge_old_incidents(retention_days)
        shadow_deleted = purge_shadow_reviews(30)
        now = timezone.now()
        access_tokens, _ = MobileAccessToken.objects.filter(
            expires_at__lte=now
        ).delete()
        pairings, _ = MobilePairing.objects.filter(
            expires_at__lte=now - timedelta(days=1)
        ).delete()
        self.stdout.write(
            f"Deleted {deleted} incidents, {shadow_deleted} shadow reviews, "
            f"{access_tokens} access tokens and "
            f"{pairings} expired pairings"
        )
