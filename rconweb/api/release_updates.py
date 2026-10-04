import json
from datetime import timedelta

from django.conf import settings
from django.core.cache import cache
from django.db import transaction
from django.utils import timezone

from rcon.release_channel import get_channel, parse_version
from .auth import api_response, login_required
from .decorators import require_content_type, require_http_methods
from .models import UserReleaseHighlightState


def current_highlight_release(channel):
    if channel.get("status") != "ready":
        return None
    return next((release for release in channel.get("releases", [])
                 if release.get("current") and release.get("highlights")), None)


def release_key(tag):
    version, prerelease = parse_version(tag)
    return "v" + ".".join(map(str, version)) + ("-" + prerelease if prerelease else "")


def highlight_state(record, key):
    seen = bool(record and record.seen)
    until = record.snoozed_until if record else None
    return {"release_version": key, "seen": seen,
            "snoozed_until": until.isoformat() if until else None,
            "auto_show": not seen and (until is None or until <= timezone.now())}


def private_response(result, command, **kwargs):
    response = api_response(result=result, command=command, **kwargs)
    response["Cache-Control"] = "private, no-store"
    return response


@login_required()
@require_http_methods(["GET"])
def get_update_channel(request):
    """Read private release notes up to the matching deployed frontend/backend version."""
    result = get_channel(settings.TAG_VERSION, request.GET.get("frontend_version", "")[:100], cache)
    result = {**result, "reader_id": str(request.user.pk)}
    release = current_highlight_release(result)
    state = None
    if release:
        key = release_key(release["tag_name"])
        record = UserReleaseHighlightState.objects.filter(user=request.user, release_version=key).first()
        state = highlight_state(record, key)
    return private_response({**result, "highlight_state": state}, "get_update_channel", failed=False)


@login_required()
@require_http_methods(["POST"])
@require_content_type()
def set_own_release_highlight_state(request):
    """Claim, acknowledge or defer installed DE/EN highlights for the signed-in account.

    JSON: frontend_version, release_version, action (claim, seen or later).
    Claim atomically reserves the one-time display; later postpones it by 24 hours.
    No other user's ID is accepted. Frontend/backend versions must match.
    """
    command = "set_own_release_highlight_state"
    try:
        payload = json.loads(request.body)
        if not isinstance(payload, dict) or set(payload) != {"frontend_version", "release_version", "action"}:
            raise ValueError()
        if payload["action"] not in ("claim", "seen", "later"):
            raise ValueError()
        if any(not isinstance(payload[key], str) or len(payload[key]) > 100
               for key in ("frontend_version", "release_version")):
            raise ValueError()
    except (ValueError, TypeError):
        return private_response(None, command, failed=True, error="Invalid highlight state request.", status_code=400)

    channel = get_channel(settings.TAG_VERSION, payload["frontend_version"], cache)
    release = current_highlight_release(channel)
    if not release or parse_version(payload["release_version"]) != parse_version(release["tag_name"]):
        return private_response(None, command, failed=True, error="Installed highlights are not available.", status_code=409)
    key = release_key(release["tag_name"])
    with transaction.atomic():
        UserReleaseHighlightState.objects.get_or_create(user=request.user, release_version=key)
        record = UserReleaseHighlightState.objects.select_for_update().get(user=request.user, release_version=key)
        eligible = highlight_state(record, key)["auto_show"]
        action = payload["action"]
        if action != "claim" or eligible:
            record.seen = action != "later"
            record.snoozed_until = timezone.now() + timedelta(hours=24) if action == "later" else None
            record.save(update_fields=("seen", "snoozed_until", "updated_at"))
        state = highlight_state(record, key)
    return private_response({**state, "show": action == "claim" and eligible}, command, failed=False)
