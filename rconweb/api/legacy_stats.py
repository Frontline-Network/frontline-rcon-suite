"""Migration responses for retired third-party stats endpoints.

These routes used to be requested by external bots but were never part of the
supported Frontline API contract.  Returning a documented response is safer
than guessing an old payload shape: a guessed alias could make a moderation or
stats integration act on incomplete data.
"""

import hashlib
import logging
import os

from django.core.cache import cache
from django.views.decorators.csrf import csrf_exempt
from django_ratelimit.decorators import ratelimit

from .auth import api_response
from .decorators import require_http_methods
from .ratelimits import request_rate_limit_key

logger = logging.getLogger("rconweb")

LEGACY_STATS_RATE_LIMIT = "6/m"
LEGACY_STATS_SAMPLE_SECONDS = max(
    60, int(os.getenv("HLL_LEGACY_STATS_SAMPLE_SECONDS", "3600"))
)

LEGACY_STATS_ENDPOINTS = {
    "get_player_list": {
        "successor": "/api/get_detailed_players",
        "alternatives": ["/api/get_players", "/api/get_team_view"],
        "description": "Use get_detailed_players for a full live roster.",
    },
    "get_scoreboard": {
        "successor": "/api/get_live_scoreboard",
        "alternatives": ["/api/get_scoreboard_maps", "/api/get_map_scoreboard"],
        "description": "Use get_live_scoreboard for the current match.",
    },
}


def _sample_legacy_probe(request, endpoint: str, successor: str) -> None:
    """Log at most once per endpoint/client window without exposing identity."""

    client_key = request_rate_limit_key("legacy-stats-endpoints", request)
    fingerprint = hashlib.sha256(client_key.encode("utf-8")).hexdigest()[:12]
    cache_key = f"legacy-stats-probe:{endpoint}:{fingerprint}"
    try:
        first_probe_in_window = cache.add(
            cache_key, True, timeout=LEGACY_STATS_SAMPLE_SECONDS
        )
    except Exception:
        # A deprecation response must remain available when an optional cache
        # backend is temporarily unavailable.
        first_probe_in_window = False
    if first_probe_in_window:
        logger.info(
            "Legacy stats endpoint probe: endpoint=%s successor=%s client=%s",
            endpoint,
            successor,
            fingerprint,
        )


def _deprecated_stats_response(request, endpoint: str):
    metadata = LEGACY_STATS_ENDPOINTS[endpoint]
    successor = metadata["successor"]
    _sample_legacy_probe(request, endpoint, successor)
    response = api_response(
        result={
            "deprecated_endpoint": f"/api/{endpoint}",
            "successor": successor,
            "alternatives": metadata["alternatives"],
            "documentation_endpoint": "/api/get_api_documentation",
        },
        command=endpoint,
        failed=True,
        error=(
            f"{endpoint} has been retired. {metadata['description']} "
            f"Migrate to {successor}."
        ),
        status_code=410,
    )
    response["Deprecation"] = "true"
    response["Link"] = f'<{successor}>; rel="successor-version"'
    response["Retry-After"] = "300"
    response["Cache-Control"] = "no-store"
    return response


@csrf_exempt
@ratelimit(
    group="legacy-stats-endpoints",
    key=request_rate_limit_key,
    rate=LEGACY_STATS_RATE_LIMIT,
    block=True,
)
@require_http_methods(["GET"])
def get_player_list(request):
    """Retired: migrate clients to ``get_detailed_players``."""

    return _deprecated_stats_response(request, "get_player_list")


@csrf_exempt
@ratelimit(
    group="legacy-stats-endpoints",
    key=request_rate_limit_key,
    rate=LEGACY_STATS_RATE_LIMIT,
    block=True,
)
@require_http_methods(["GET"])
def get_scoreboard(request):
    """Retired: migrate clients to ``get_live_scoreboard``."""

    return _deprecated_stats_response(request, "get_scoreboard")
