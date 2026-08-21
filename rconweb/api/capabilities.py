"""Stable, anonymous discovery contract for external CRCON integrations."""

from __future__ import annotations

from collections.abc import Iterable

from rcon.game.base import GameProfile

# ``manage.py`` exposes the inner Django package as ``rconweb`` in production,
# whereas repository-level tests import the outer namespace package.  Support
# both import roots without changing the deployed settings module.
try:
    from rconweb.settings import TAG_VERSION
except ModuleNotFoundError as exc:
    if exc.name != "rconweb.settings":
        raise
    from rconweb.rconweb.settings import TAG_VERSION

CAPABILITIES_SCHEMA_VERSION = 1

# These are the operations that Frontline commits to expose for both supported
# game profiles.  Less complete or legacy-only routes deliberately stay out of
# this contract until they have an equally stable cross-game implementation.
OPERATION_REQUIREMENTS = {
    "live_status": ("get_status",),
    "live_roster": ("get_players", "get_team_view"),
    "player_context": ("get_player_info", "get_player_profile"),
    "player_moderation": ("punish", "kick", "temp_ban", "perma_ban"),
    "map_rotation": ("get_map_rotation", "set_map_rotation"),
    "map_vote": ("get_votemap_status", "set_votemap_config"),
    "auto_settings": (
        "get_auto_settings",
        "preview_auto_settings",
        "set_auto_settings",
    ),
}


def build_capabilities(
    profile: GameProfile, registered_commands: Iterable[str]
) -> dict:
    """Build the versioned contract without contacting the game server."""
    commands = frozenset(registered_commands)

    return {
        "schema_version": CAPABILITIES_SCHEMA_VERSION,
        "crcon_version": TAG_VERSION,
        "game": {
            "id": profile.game.value,
            "supported_game_modes": sorted(
                game_mode.value for game_mode in profile.supported_game_modes
            ),
            "timer_controls": {
                "match_timer_modes": sorted(
                    game_mode.value for game_mode in profile.match_timer_modes
                ),
                "warmup_timer_modes": sorted(
                    game_mode.value for game_mode in profile.warmup_timer_modes
                ),
            },
        },
        "operations": {
            operation: {
                "available": all(command in commands for command in requirements),
                "required_legacy_commands": list(requirements),
            }
            for operation, requirements in OPERATION_REQUIREMENTS.items()
        },
        "interfaces": {
            "capabilities": {
                "version": "v1",
                "path": "/api/v1/capabilities",
                "methods": ["GET"],
                "authentication": "none",
            },
            "legacy_api": {
                "version": "unversioned",
                "documentation_path": "/api/get_api_documentation",
                "authentication": "session_or_api_key_per_endpoint",
            },
            "mobile_api": {
                "version": "v1",
                "discovery_path": "/api/mobile/v1/discovery",
                "authentication": "bearer_or_session_per_endpoint",
            },
        },
    }


def capabilities(request):
    """Expose supported integration operations without a probe request."""
    if request.method != "GET":
        # Keep the pure builder importable in repository-level contract tests;
        # Django's HTTP/auth modules are only needed for an actual request.
        from django.http import HttpResponseNotAllowed

        return HttpResponseNotAllowed(["GET"])

    from .auth import api_response

    # Import at request time: ``api.urls`` registers the legacy endpoints while
    # Django builds its URL tree, so importing it during module import would be
    # circular.  This has no RCON I/O and is only a tiny in-process lookup.
    from .urls import endpoints
    from .views import rcon_api

    result = build_capabilities(
        rcon_api.game_profile,
        (name for name, _function in endpoints),
    )
    return api_response(result=result, command="get_capabilities", failed=False)
