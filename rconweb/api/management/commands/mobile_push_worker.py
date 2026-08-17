import os
import time
from datetime import datetime, timezone

import requests
from django.core.management.base import BaseCommand
from sqlalchemy import exists, select

from api.models import MobileDevice
from api.mobile_settings import mobile_installation_id, mobile_integration_enabled
from rcon.models import (
    AdminIncidentEvent,
    AdminIncidentPushDelivery,
    enter_session,
)


class Command(BaseCommand):
    help = "Deliver opaque CRCON incident notifications to the push relay"
    # Avoid importing the full API/view graph into a background-only process.
    requires_system_checks = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._devices = []
        self._devices_refresh_at = 0.0
        self._http = requests.Session()

    def handle(self, *args, **options):
        relay_url = os.getenv("MOBILE_PUSH_RELAY_URL", "").rstrip("/")
        if not mobile_integration_enabled() or not relay_url:
            self.stderr.write("Mobile integration or MOBILE_PUSH_RELAY_URL is disabled")
            return
        self.stdout.write("CRCON mobile push worker started")
        minimum_sleep = max(
            0.25, float(os.getenv("MOBILE_PUSH_ACTIVE_POLL_SECONDS", "1"))
        )
        maximum_sleep = max(
            minimum_sleep,
            float(os.getenv("MOBILE_PUSH_IDLE_POLL_SECONDS", "10")),
        )
        sleep_seconds = minimum_sleep
        while True:
            did_work = self._deliver_batch(relay_url)
            if did_work:
                sleep_seconds = minimum_sleep
            else:
                sleep_seconds = min(maximum_sleep, sleep_seconds * 2)
            time.sleep(sleep_seconds)

    def _eligible_devices(self):
        now = time.monotonic()
        if now < self._devices_refresh_at:
            return self._devices

        candidate_devices = list(
            MobileDevice.objects.filter(
                revoked_at__isnull=True,
                notifications_enabled=True,
                user__is_active=True,
            )
            .select_related("user")
            .prefetch_related("user__user_permissions", "user__groups__permissions")
            .exclude(push_handle="")
            .exclude(push_capability="")
        )
        self._devices = [
            device
            for device in candidate_devices
            if device.user.has_perm("api.can_view_admin_incidents")
        ]
        self._devices_refresh_at = now + max(
            5.0, float(os.getenv("MOBILE_PUSH_DEVICE_CACHE_SECONDS", "60"))
        )
        return self._devices

    def _deliver_batch(self, relay_url: str):
        devices = self._eligible_devices()
        if not devices:
            return False

        pending_by_device = self._load_pending_events(devices)
        did_work = False
        deliveries = []
        for device, events in pending_by_device:
            for event in events:
                delivery = AdminIncidentPushDelivery(
                    event_id=event["id"],
                    device_id=str(device.id),
                )
                try:
                    response = self._http.post(
                        f"{relay_url}/v1/notify/{device.push_handle}",
                        headers={"Authorization": f"Bearer {device.push_capability}"},
                        json={
                            "connection_key": mobile_installation_id(),
                            "incident_id": event["incident_id"],
                            "event_type": event["event_type"],
                            "timestamp": event["created_at"].isoformat(),
                        },
                        timeout=5,
                    )
                    response.raise_for_status()
                    delivery.delivered_at = datetime.now(tz=timezone.utc)
                    did_work = True
                except requests.RequestException as exc:
                    relay_status = getattr(exc.response, "status_code", None)
                    if relay_status in {404, 410}:
                        delivery.error = f"relay_status_{relay_status}"
                        MobileDevice.objects.filter(pk=device.pk).update(
                            push_handle="", push_capability=""
                        )
                        # Do not keep a revoked relay capability in the
                        # in-memory cache for another minute.
                        self._devices_refresh_at = 0.0
                        did_work = True
                        deliveries.append(delivery)
                        break
                    # Transient provider and network errors are retried.
                    continue
                deliveries.append(delivery)

        if deliveries:
            with enter_session() as session:
                session.add_all(deliveries)
        return did_work

    @staticmethod
    def _load_pending_events(devices):
        """Read pending work without holding a DB transaction during HTTP."""

        pending_by_device = []
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
                pending_by_device.append(
                    (
                        device,
                        [
                            {
                                "id": event.id,
                                "incident_id": str(event.incident_id),
                                "event_type": event.event_type,
                                "created_at": event.created_at,
                            }
                            for event in events
                        ],
                    )
                )
        return pending_by_device
