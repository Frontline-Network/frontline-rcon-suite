"""Defense in depth for legacy, mobile, public and raw response surfaces."""
import json
import re

from django.http import HttpResponse

from rcon.live_map.domain import redact_positions

TACTICAL_KEYS = re.compile(rb'"(?:world_?position|position_m|position_valid|map_position|trajectory|positions|garrisons|outposts|tactical_evidence)"\s*:', re.I)


class TacticalPrivacyMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if not request.path.startswith("/api/"):
            return response
        user = getattr(request, "user", None)
        allowed = bool(user and user.is_authenticated and user.is_active and user.has_perm("api.can_view_live_map"))
        if allowed:
            return response
        if getattr(response, "streaming", False):
            # There is no HTTP streaming API contract today. A future generic
            # stream must explicitly enforce tactical redaction before opting in.
            return HttpResponse(status=403)
        content_type = response.get("Content-Type", "")
        if "application/json" in content_type:
            raw = response.content
            if TACTICAL_KEYS.search(raw) or b'position' in raw.lower() or b'p_coord' in raw.lower() or b'pcoord' in raw.lower():
                try:
                    value = json.loads(raw)
                    response.content = json.dumps(redact_positions(value), ensure_ascii=False).encode()
                    response["Content-Length"] = str(len(response.content))
                    response["Cache-Control"] = "private, no-store"
                except (ValueError, TypeError):
                    return HttpResponse(status=403)
        return response
