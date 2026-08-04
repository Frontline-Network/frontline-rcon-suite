import hashlib
import hmac
import secrets
from datetime import timedelta

from django.db import transaction
from django.utils import timezone

from rconweb.settings import SECRET_KEY

from .models import MobileAccessToken, MobileDevice

ACCESS_TOKEN_LIFETIME = timedelta(minutes=15)
REFRESH_TOKEN_IDLE_LIFETIME = timedelta(days=30)
REFRESH_TOKEN_ABSOLUTE_LIFETIME = timedelta(days=180)


class InvalidMobileToken(ValueError):
    pass


def token_digest(value: str, purpose: str) -> str:
    """Create a deterministic, purpose-bound lookup digest without storing secrets."""

    key = SECRET_KEY.encode("utf-8")
    message = f"crcon-mobile:{purpose}:{value}".encode("utf-8")
    return hmac.new(key, message, hashlib.sha256).hexdigest()


def random_token(prefix: str) -> str:
    return f"{prefix}_{secrets.token_urlsafe(32)}"


def _new_access_token(device: MobileDevice, now) -> tuple[str, MobileAccessToken]:
    raw_access_token = random_token("crcon_access")
    access_token = MobileAccessToken.objects.create(
        token_digest=token_digest(raw_access_token, "access"),
        device=device,
        expires_at=now + ACCESS_TOKEN_LIFETIME,
    )
    return raw_access_token, access_token


@transaction.atomic
def issue_device_tokens(
    device: MobileDevice, *, initialize_absolute_expiry: bool = False
) -> dict:
    now = timezone.now()
    if initialize_absolute_expiry or not device.absolute_expires_at:
        device.absolute_expires_at = now + REFRESH_TOKEN_ABSOLUTE_LIFETIME

    if device.revoked_at or device.absolute_expires_at <= now:
        raise InvalidMobileToken("The mobile device is revoked or expired")

    raw_refresh_token = random_token("crcon_refresh")
    device.refresh_token_digest = token_digest(raw_refresh_token, "refresh")
    device.refresh_expires_at = min(
        now + REFRESH_TOKEN_IDLE_LIFETIME, device.absolute_expires_at
    )
    device.last_seen_at = now
    device.save(
        update_fields=(
            "refresh_token_digest",
            "refresh_expires_at",
            "absolute_expires_at",
            "last_seen_at",
        )
    )

    MobileAccessToken.objects.filter(device=device, expires_at__lte=now).delete()
    raw_access_token, access_token = _new_access_token(device, now)
    return {
        "token_type": "Bearer",
        "access_token": raw_access_token,
        "access_expires_at": access_token.expires_at,
        "refresh_token": raw_refresh_token,
        "refresh_expires_at": device.refresh_expires_at,
        "absolute_expires_at": device.absolute_expires_at,
        "device_id": str(device.id),
    }


def authenticate_mobile_access_token(raw_token: str | None):
    if not raw_token or not raw_token.startswith("crcon_access_"):
        return None

    now = timezone.now()
    try:
        access_token = MobileAccessToken.objects.select_related(
            "device", "device__user"
        ).get(token_digest=token_digest(raw_token, "access"))
    except MobileAccessToken.DoesNotExist:
        return None

    device = access_token.device
    if (
        access_token.expires_at <= now
        or device.revoked_at is not None
        or not device.user.is_active
        or device.absolute_expires_at is None
        or device.absolute_expires_at <= now
    ):
        return None

    if not device.last_seen_at or device.last_seen_at < now - timedelta(minutes=5):
        MobileDevice.objects.filter(pk=device.pk).update(last_seen_at=now)
        device.last_seen_at = now
    return device.user, device


@transaction.atomic
def refresh_device_tokens(device_id: str, raw_refresh_token: str) -> dict:
    now = timezone.now()
    try:
        device = (
            MobileDevice.objects.select_for_update()
            .select_related("user")
            .get(
                pk=device_id,
                refresh_token_digest=token_digest(raw_refresh_token, "refresh"),
            )
        )
    except (MobileDevice.DoesNotExist, ValueError):
        raise InvalidMobileToken("Invalid refresh token")

    if (
        device.revoked_at is not None
        or not device.user.is_active
        or device.refresh_expires_at is None
        or device.refresh_expires_at <= now
        or device.absolute_expires_at is None
        or device.absolute_expires_at <= now
    ):
        raise InvalidMobileToken("The refresh token is expired or revoked")

    MobileAccessToken.objects.filter(device=device).delete()
    return issue_device_tokens(device)


@transaction.atomic
def revoke_mobile_device(device: MobileDevice) -> None:
    device.revoked_at = timezone.now()
    device.refresh_token_digest = None
    device.refresh_expires_at = None
    device.save(
        update_fields=("revoked_at", "refresh_token_digest", "refresh_expires_at")
    )
    MobileAccessToken.objects.filter(device=device).delete()
