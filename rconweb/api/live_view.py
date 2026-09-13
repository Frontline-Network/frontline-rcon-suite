import json

from .auth import api_response, login_required
from .decorators import require_content_type, require_http_methods
from .live_view_preferences import default_user_live_view, normalize_live_view
from .models import UserLiveViewPreference


@login_required()
@require_http_methods(["GET"])
def get_own_user_live_view(request):
    record = UserLiveViewPreference.objects.filter(user=request.user).first()
    try:
        preferences = (
            normalize_live_view(record.preferences)
            if record else default_user_live_view()
        )
    except ValueError:
        preferences = default_user_live_view()
    return api_response(command="get_own_user_live_view", result=preferences, failed=False)


@login_required()
@require_http_methods(["PUT"])
@require_content_type()
def set_own_user_live_view(request):
    command = "set_own_user_live_view"
    try:
        preferences = normalize_live_view(json.loads(request.body or b"{}"))
    except (ValueError, UnicodeDecodeError) as exc:
        return api_response(command=command, error=str(exc), failed=True, status_code=400)
    UserLiveViewPreference.objects.update_or_create(
        user=request.user, defaults={"preferences": preferences}
    )
    return api_response(command=command, result=preferences, failed=False)
