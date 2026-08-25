import json
import re

from django.views.decorators.csrf import csrf_exempt

from .auth import api_response, login_required
from .decorators import require_content_type, require_http_methods
from .models import UserAppearancePreference, default_user_appearance

APPEARANCE_VERSION = 1
MODES = {"light", "dark", "system"}
PRESETS = {
    "frontline-gold",
    "tactical-blue",
    "signal-green",
    "command-red",
    "neutral",
    "custom",
}
COLOR_VISION_MODES = {"standard", "deuteranopia", "protanopia", "tritanopia"}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


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

    UserAppearancePreference.objects.update_or_create(
        user=request.user, defaults={"preferences": preferences}
    )
    return api_response(command=command, result=preferences, failed=False)
