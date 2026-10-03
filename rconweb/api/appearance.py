import json
import re

from django.views.decorators.csrf import csrf_exempt

from .auth import api_response, login_required
from .decorators import require_content_type, require_http_methods
from .models import UserAppearancePreference, default_user_appearance
from .wardogs_styles import normalize_wardogs_style

APPEARANCE_VERSION = 1
MODES = {"light", "dark", "system"}
PRESETS = {
    "frontline-gold",
    "wardogs",
    "tactical-blue",
    "signal-green",
    "command-red",
    "neutral",
    "custom",
}
COLOR_VISION_MODES = {"standard", "deuteranopia", "protanopia", "tritanopia"}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")
INTERNAL_ROUTE = re.compile(r"^/[a-z0-9_-]+(?:/[a-z0-9_-]+)*$")


def normalize_wardogs_shortcuts(value):
    if not isinstance(value, list) or len(value) > 64:
        raise ValueError("wardogsShortcuts must be a list of up to 64 routes.")
    if any(
        not isinstance(route, str)
        or len(route) > 200
        or not INTERNAL_ROUTE.fullmatch(route)
        for route in value
    ):
        raise ValueError("Shortcuts must be internal navigation routes.")
    return list(dict.fromkeys(value))


def normalize_appearance(value):
    if not isinstance(value, dict):
        raise ValueError("Appearance preferences must be a JSON object.")

    defaults = default_user_appearance()
    mode = value.get("mode", defaults["mode"])
    preset = value.get("preset", defaults["preset"])
    custom_accent = value.get("customAccent", defaults["customAccent"])
    color_vision = value.get("colorVision", defaults["colorVision"])

    if mode not in MODES:
        raise ValueError("Unsupported appearance mode.")
    if preset not in PRESETS:
        raise ValueError("Unsupported appearance preset.")
    if color_vision not in COLOR_VISION_MODES:
        raise ValueError("Unsupported color-vision mode.")
    if not isinstance(custom_accent, str) or not HEX_COLOR.fullmatch(custom_accent):
        raise ValueError("customAccent must be a six-digit hex color.")

    return {
        "version": APPEARANCE_VERSION,
        "mode": mode,
        "preset": preset,
        "customAccent": custom_accent.lower(),
        "colorVision": color_vision,
        "wardogsStyle": normalize_wardogs_style(value.get("wardogsStyle", defaults["wardogsStyle"])),
        "wardogsShortcuts": normalize_wardogs_shortcuts(
            value.get("wardogsShortcuts", defaults["wardogsShortcuts"])
        ),
    }


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def get_own_user_appearance(request):
    record, _ = UserAppearancePreference.objects.get_or_create(user=request.user)
    try:
        preferences = normalize_appearance(record.preferences)
    except ValueError:
        preferences = default_user_appearance()
        record.preferences = preferences
        record.save(update_fields=("preferences", "updated_at"))
    return api_response(
        command="get_own_user_appearance", result=preferences, failed=False
    )


@login_required()
@require_http_methods(["PUT"])
@require_content_type()
def set_own_user_appearance(request):
    command = "set_own_user_appearance"
    try:
        payload = json.loads(request.body or b"{}")
        preferences = normalize_appearance(payload)
    except (json.JSONDecodeError, ValueError) as exc:
        return api_response(
            command=command,
            error=str(exc),
            failed=True,
            status_code=400,
        )

    # Older clients omit newer fields. Preserve those while still accepting
    # any shortcut/style update explicitly included in this request.
    if "wardogsShortcuts" not in payload or "wardogsStyle" not in payload:
        current = (
            UserAppearancePreference.objects.filter(user=request.user)
            .values_list("preferences", flat=True)
            .first()
        )
        if "wardogsShortcuts" not in payload and isinstance(current, dict) and "wardogsShortcuts" in current:
            try:
                preferences["wardogsShortcuts"] = normalize_wardogs_shortcuts(
                    current["wardogsShortcuts"]
                )
            except ValueError:
                pass
        if "wardogsStyle" not in payload and isinstance(current, dict) and "wardogsStyle" in current:
            try:
                preferences["wardogsStyle"] = normalize_wardogs_style(current["wardogsStyle"])
            except ValueError:
                pass

    UserAppearancePreference.objects.update_or_create(
        user=request.user, defaults={"preferences": preferences}
    )
    return api_response(command=command, result=preferences, failed=False)
