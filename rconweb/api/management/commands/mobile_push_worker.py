import os
import time
from datetime import datetime, timezone

import requests
from django.core.management.base import BaseCommand
from sqlalchemy import exists, select

from api.mobile import _installation_id, mobile_integration_enabled
from api.models import MobileDevice
from rcon.models import (
    AdminIncidentEvent,
    AdminIncidentPushDelivery,
    enter_session,
)


class Command(BaseCommand):
    help = "Deliver opaque CRCON incident notifications to the push relay"

    def handle(self, *args, **options):
        relay_url = os.getenv("MOBILE_PUSH_RELAY_URL", "").rstrip("/")
        if not mobile_integration_enabled() or not relay_url:
            self.stderr.write("Mobile integration or MOBILE_PUSH_RELAY_URL is disabled")
            return
        self.stdout.write("CRCON mobile push worker started")
        while True:
            self._deliver_batch(relay_url)
            time.sleep(1)

    def _deliver_batch(self, relay_url: str):
        candidate_devices = list(
            MobileDevice.objects.filter(
                revoked_at__isnull=True,
                notifications_enabled=True,
                user__is_active=True,
            )
            .select_related("user")
            .exclude(push_handle="")
            .exclude(push_capability="")
        )
        devices = [
            device
            for device in candidate_devices
            if device.user.has_perm("api.can_view_admin_incidents")
        ]
        if not devices:
            return

        with enter_session() as session:
            for device in devices:
                pending_delivery = exists().where(
                    AdminIncidentPushDelivery.event_id == AdminIncidentEvent.id,
                    AdminIncidentPushDelivery.device_id == str(device.id),
                )
                events = (
                    session.execute(
                        select(AdminIncidentEvent)
                        .where(
                            AdminIncidentEvent.created_at >= device.created_at,
                            AdminIncidentEvent.event_type != "action_started",
                            ~pending_delivery,
                        )
                        .order_by(AdminIncidentEvent.id.asc())
                        .limit(100)
                    )
                    .scalars()
                    .all()
                )
                for event in events:
                    delivery = AdminIncidentPushDelivery(
                        event_id=event.id,
                        device_id=str(device.id),
                    )
                    try:
                        response = requests.post(
                            f"{relay_url}/v1/notify/{device.push_handle}",
                            headers={
                                "Authorization": f"Bearer {device.push_capability}"
                            },
                            json={
                                "connection_key": _installation_id(),
                                "incident_id": str(event.incident_id),
                                "event_type": event.event_type,
                                "timestamp": event.created_at.isoformat(),
                            },
                            timeout=5,
                        )
                        response.raise_for_status()
                        delivery.delivered_at = datetime.now(tz=timezone.utc)
                    except requests.RequestException as exc:
                        relay_status = getattr(exc.response, "status_code", None)
                        if relay_status in {404, 410}:
                            delivery.error = f"relay_status_{relay_status}"
                            MobileDevice.objects.filter(pk=device.pk).update(
                                push_handle="", push_capability=""
                            )
                        else:
                            # Transient provider and network errors are retried.
                            continue
                    session.add(delivery)
