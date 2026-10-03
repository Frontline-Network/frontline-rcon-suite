from django.conf import settings
from django.core.cache import cache

from rcon.release_channel import get_channel
from .auth import api_response, login_required
from .decorators import require_http_methods


@login_required()
@require_http_methods(["GET"])
def get_update_channel(request):
    """Read private release notes up to the matching deployed frontend/backend version."""
    result = get_channel(settings.TAG_VERSION, request.GET.get("frontend_version", "")[:100], cache)
    result = {**result, "reader_id": str(request.user.pk)}
    response = api_response(result, failed=False, command="get_update_channel")
    response["Cache-Control"] = "private, no-store"
    return response
