from django.urls import path

from api import mobile

urlpatterns = [
    path("api/mobile/v1/pairings", mobile.create_pairing),
    path("api/mobile/v1/pairings/<uuid:pairing_id>", mobile.pairing_status),
    path("api/mobile/v1/pairings/<uuid:pairing_id>/scan", mobile.scan_pairing),
    path(
        "api/mobile/v1/pairings/<uuid:pairing_id>/approve",
        mobile.approve_pairing,
    ),
    path(
        "api/mobile/v1/pairings/<uuid:pairing_id>/exchange",
        mobile.exchange_pairing,
    ),
    path("api/mobile/v1/tokens/refresh", mobile.refresh_token),
    path("api/mobile/v1/devices", mobile.devices),
    path("api/mobile/v1/devices/<uuid:device_id>", mobile.device_detail),
]
