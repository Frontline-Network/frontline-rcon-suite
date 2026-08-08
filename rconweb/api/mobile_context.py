"""Permission-aware player and squad context for the native mobile client."""

from datetime import datetime, timedelta, timezone as datetime_timezone

from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rcon.autobalancer.store import AutobalancerStore
from rcon.message_templates import get_message_templates
from rcon.types import MessageTemplateCategory
from rcon.utils import get_server_number

from .auth import api_response, login_required
from .decorators import require_http_methods
from .mobile import (
    _error,
    _json_body,
    _require_enabled,
    _require_feature,
    mobile_feature_enabled,
)
from .mobile_audit import record_mobile_audit
from .multi_servers import forward_mobile_request_to_server


def _rcon_api():
    # Importing the full command layer while Django is still constructing its URL
    # configuration triggers legacy modules that configure Channels themselves.
    from . import views

    return views.rcon_api


def _forward_get(request, server_number: int):
    if server_number == int(get_server_number()) or request.GET.get("forwarded"):
        return None
    try:
        response = forward_mobile_request_to_server(
            request,
            server_number,
            request.path,
            method="GET",
            params={
                key: value for key, value in request.GET.items() if key != "forwarded"
            },
        )
    except ValueError as exc:
        return _error("mobile_context", str(exc), 503)
    return HttpResponse(
        content=response.content,
        status=response.status_code,
        content_type=response.headers.get("content-type", "application/json"),
    )


def _server_number(request) -> int:
    return int(request.GET.get("server_number", get_server_number()))


def _forward_mutation(request, server_number: int, data: dict):
    if server_number == int(get_server_number()) or data.get("forwarded"):
        return None
    try:
        response = forward_mobile_request_to_server(
            request,
            server_number,
            request.path,
            data=data,
            method=request.method,
            params={key: value for key, value in request.GET.items() if key != "forwarded"},
        )
    except ValueError as exc:
        return _error("mobile_context", str(exc), 503)
    return HttpResponse(
        content=response.content,
        status=response.status_code,
        content_type=response.headers.get("content-type", "application/json"),
    )


def _display_player_name(player: dict) -> str:
    soldier = player.get("soldier") or {}
    names = player.get("names") or []
    return str(
        player.get("name")
        or player.get("player_name")
        or soldier.get("name")
        or (names[0].get("name") if names and isinstance(names[0], dict) else "")
        or player.get("player_id")
        or "Unknown"
    )


def _watch_summary(player: dict) -> dict:
    watch = player.get("watchlist") or {}
    return {
        "player_id": str(player.get("player_id") or watch.get("player_id") or ""),
        "name": _display_player_name(player),
        "reason": str(watch.get("reason") or ""),
        "by": watch.get("by"),
        "modified": watch.get("modified"),
        "count": int(watch.get("count") or 0),
        "last_seen_timestamp_ms": player.get("last_seen_timestamp_ms"),
        "online": bool(player.get("online", False)),
    }


def _incident_time(value) -> datetime:
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=datetime_timezone.utc)
    return parsed


def _event_type(action: str | None) -> str | None:
    normalized = str(action or "").upper()
    if normalized == "TEAM KILL":
        return "teamkill"
    if normalized == "KILL":
        return "kill"
    if normalized.startswith("CHAT"):
        return "chat"
    if normalized == "CONNECTED":
        return "join"
    if normalized == "DISCONNECTED":
        return "leave"
    return None


def _context_event(log: dict) -> dict | None:
    kind = _event_type(log.get("type") or log.get("action"))
    if kind is None:
        return None
    occurred_at = log.get("event_time") or log.get("timestamp")
    return {
        "id": str(log.get("id") or ""),
        "type": kind,
        "occurred_at": occurred_at,
        "actor_name": log.get("player1_name") or log.get("player_name_1"),
        "other_name": log.get("player2_name") or log.get("player_name_2"),
        "message": log.get("content") or log.get("message") or "",
        "weapon": log.get("weapon"),
    }


def _team_view_for_user(request):
    if not request.user.has_perm("api.can_view_team_view"):
        raise PermissionError("Missing team view permission")
    return _rcon_api().get_team_view()


def _find_live_player(team_view: dict, player_id: str):
    for team_name, team in team_view.items():
        if team_name == "fail_count" or not isinstance(team, dict):
            continue
        commander = team.get("commander")
        if commander and str(commander.get("player_id")) == player_id:
            return {**commander, "team": commander.get("team") or team_name}
        for squad_name, squad in (team.get("squads") or {}).items():
            for player in squad.get("players") or []:
                if str(player.get("player_id")) == player_id:
                    return {
                        **player,
                        "team": player.get("team") or team_name,
                        "unit_name": player.get("unit_name") or squad_name,
                        "squad_type": squad.get("type"),
                    }
    return None


def incident_live_context(request, incident: dict) -> dict:
    """Attach a live counterpart to immutable report snapshots when permitted."""

    if not request.user.has_perm("api.can_view_team_view"):
        return {
            "available": False,
            "reason": "missing_permission",
            "reporter": None,
            "subjects": {},
        }
    team_view = _rcon_api().get_team_view()
    subject_context = {}
    for subject in incident.get("subjects") or []:
        if subject.get("kind") == "player":
            subject_context[subject["id"]] = _find_live_player(
                team_view, str(subject.get("player_id") or "")
            )
            continue
        matched = None
        for team_name, team in team_view.items():
            if not isinstance(team, dict) or team_name == "fail_count":
                continue
            if (
                subject.get("team")
                and str(subject["team"]).casefold() != str(team_name).casefold()
            ):
                continue
            for squad_name, squad in (team.get("squads") or {}).items():
                if (
                    str(squad_name).casefold()
                    == str(subject.get("squad_name") or "").casefold()
                ):
                    matched = {
                        "team": team_name,
                        "squad_name": squad_name,
                        **squad,
                    }
                    break
        subject_context[subject["id"]] = matched
    return {
        "available": True,
        "captured_at": timezone.now().isoformat(),
        "reporter": _find_live_player(
            team_view, str(incident.get("reporter_id") or "")
        ),
        "subjects": subject_context,
    }


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def players_search(request):
    command = "mobile_players_search"
    if disabled := _require_enabled(command):
        return disabled
    try:
        server_number = _server_number(request)
    except ValueError as exc:
        return _error(command, str(exc), 400)
    if forwarded := _forward_get(request, server_number):
        return forwarded
    query = str(request.GET.get("q") or "").strip()
    if len(query) < 2:
        return _error(command, "Search text must contain at least two characters", 400)
    can_history = request.user.has_perm("api.can_view_player_history")
    can_live = request.user.has_perm("api.can_view_detailed_players")
    if not can_history and not can_live:
        return _error(command, "Missing player search permission", 403)

    results: dict[str, dict] = {}
    if can_history:
        history = _rcon_api().get_players_history(
            player_name=query, page=1, page_size=50
        )
        for player in history.get("players") or []:
            player_id = str(player.get("player_id") or "")
            if player_id:
                results[player_id] = {**player, "online": False}
    if can_live:
        detailed = _rcon_api().get_detailed_players()
        normalized = query.casefold()
        for player_id, player in (detailed.get("players") or {}).items():
            if (
                normalized in str(player.get("name") or "").casefold()
                or normalized in str(player_id).casefold()
            ):
                results[str(player_id)] = {
                    **results.get(str(player_id), {}),
                    **player,
                    "online": True,
                }
    return api_response(command=command, failed=False, result=list(results.values()))


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def player_detail(request, player_id):
    command = "mobile_player_detail"
    if disabled := _require_enabled(command):
        return disabled
    try:
        server_number = _server_number(request)
    except ValueError as exc:
        return _error(command, str(exc), 400)
    if forwarded := _forward_get(request, server_number):
        return forwarded

    player_operations_enabled = mobile_feature_enabled("MOBILE_PLAYER_OPERATIONS")
    capabilities = {
        "history": request.user.has_perm("api.can_view_player_profile"),
        "live": request.user.has_perm("api.can_view_detailed_player_info"),
        "bans": request.user.has_perm("api.can_view_player_bans"),
        "comments": request.user.has_perm("api.can_view_player_comments"),
        "message": request.user.has_perm("api.can_message_players"),
        "punish": request.user.has_perm("api.can_punish_players"),
        "kick": request.user.has_perm("api.can_kick_players"),
        "temp_ban": request.user.has_perm("api.can_temp_ban_players"),
        "comment": request.user.has_perm("api.can_add_player_comments"),
        "watch_view": player_operations_enabled
        and request.user.has_perm("api.can_view_player_history"),
        "watch_add": player_operations_enabled
        and request.user.has_perm("api.can_add_player_watch"),
        "watch_remove": player_operations_enabled
        and request.user.has_perm("api.can_remove_player_watch"),
        "incident_context": player_operations_enabled
        and request.user.has_perm("api.can_view_historical_logs"),
    }
    if not capabilities["history"] and not capabilities["live"]:
        return _error(command, "Missing player detail permission", 403)

    history = None
    if capabilities["history"]:
        history = _rcon_api().get_player_profile(str(player_id))
        if history:
            history = dict(history)
            if not capabilities["bans"]:
                history.pop("bans", None)
            if not capabilities["comments"]:
                history.pop("comments", None)
    live = None
    if capabilities["live"]:
        try:
            live = _rcon_api().get_detailed_player_info(str(player_id))
        except Exception:
            live = None
    # ``player_id`` is a legacy CRCON name and can contain a SteamID64, an
    # EOS identifier, or another platform identifier.  Do not present it to a
    # mobile admin as a SteamID unless it actually has the SteamID64 shape.
    # The EOS value is maintained separately on the soldier profile.
    soldier = (history or {}).get("soldier") or {}
    canonical_player_id = str((history or {}).get("player_id") or player_id)
    steam_id = (
        canonical_player_id
        if canonical_player_id.isdigit() and len(canonical_player_id) == 17
        else None
    )
    eos_id = str(soldier.get("eos_id") or "").strip() or None
    identifiers = {
        "steam_id": steam_id,
        "eos_id": eos_id,
        # Retain an unknown platform identifier without falsely calling it a
        # SteamID or EOS-ID.  This is useful for Xbox/PlayStation records.
        "platform_player_id": (
            canonical_player_id
            if canonical_player_id not in {steam_id, eos_id}
            else None
        ),
    }
    return api_response(
        command=command,
        failed=False,
        result={
            "player_id": str(player_id),
            "server_number": server_number,
            "capabilities": capabilities,
            "identifiers": identifiers,
            "history": history,
            "live": live,
        },
    )


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def autobalancer_status(request):
    """Return the minimal, read-only live balance view for a mobile admin."""

    command = "mobile_autobalancer_status"
    if disabled := _require_enabled(command):
        return disabled
    if not request.user.has_perm("api.can_view_autobalancer"):
        return _error(command, "Missing autobalancer view permission", 403)
    try:
        server_number = _server_number(request)
    except ValueError as exc:
        return _error(command, str(exc), 400)
    if forwarded := _forward_get(request, server_number):
        return forwarded

    # Keep this surface intentionally read-only and do not disclose an
    # actionable candidate or plan. Existing CRCON controls remain the sole
    # place that can approve, cancel, or configure the Fair Autobalancer.
    status = AutobalancerStore().load_status()
    return api_response(
        command=command,
        failed=False,
        result={
            "server_number": int(get_server_number()),
            "mode": status.get("mode", "disabled"),
            "phase": status.get("phase", "idle"),
            "team_counts": status.get("team_counts") or {},
            "team_difference": status.get("team_difference"),
            "required_switches": status.get("required_switches", 0),
            "team_ratings": status.get("team_ratings") or {},
            "data_confidence": status.get("data_confidence"),
            "rating_model_version": status.get("rating_model_version"),
            "strategy": status.get("strategy"),
            "block_reasons": status.get("block_reasons") or [],
            "warnings": status.get("warnings") or [],
            "native_autobalance": status.get("native_autobalance") or {},
            "updated_at": status.get("updated_at"),
        },
    )


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def watchlist(request):
    """List the existing CRCON watchlist without introducing a second list."""

    command = "mobile_watchlist"
    if disabled := _require_feature(command, "MOBILE_PLAYER_OPERATIONS"):
        return disabled
    if not request.user.has_perm("api.can_view_player_history"):
        return _error(command, "Missing watchlist view permission", 403)
    try:
        server_number = _server_number(request)
        limit = min(max(int(request.GET.get("limit", 100)), 1), 100)
    except ValueError as exc:
        return _error(command, str(exc), 400)
    if forwarded := _forward_get(request, server_number):
        return forwarded

    api = _rcon_api()
    history = api.get_players_history(
        page=1, page_size=limit, is_watched=True
    )
    players = [_watch_summary(item) for item in history.get("players") or []]
    if request.user.has_perm("api.can_view_detailed_players"):
        try:
            live_ids = {
                str(player_id)
                for player_id in (api.get_detailed_players().get("players") or {})
            }
            for player in players:
                player["online"] = player["player_id"] in live_ids
        except Exception:
            # The database-backed watchlist remains useful during a temporary
            # RCON outage; do not turn a live-status embellishment into a
            # failed list request.
            pass
    return api_response(
        command=command,
        failed=False,
        result={
            "server_number": server_number,
            "players": players,
            "total": history.get("total", len(players)),
        },
    )


@csrf_exempt
@login_required()
@require_http_methods(["PUT", "DELETE"])
def player_watch(request, player_id):
    """Add or remove a watch using CRCON's native watchlist permission model."""

    command = "mobile_player_watch"
    if disabled := _require_feature(command, "MOBILE_PLAYER_OPERATIONS"):
        return disabled
    try:
        data = _json_body(request)
        server_number = int(data.get("server_number", request.GET.get("server_number", get_server_number())))
    except (TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    if forwarded := _forward_mutation(request, server_number, data):
        return forwarded

    player_id = str(player_id)
    incident_id = str(data.get("incident_id") or "") or None
    if request.method == "PUT":
        if not request.user.has_perm("api.can_add_player_watch"):
            return _error(command, "Missing watchlist add permission", 403)
        reason = str(data.get("reason") or "").strip()
        if not reason:
            return _error(command, "A watch reason is required", 400)
        player_name = str(data.get("player_name") or "").strip() or None
        _rcon_api().watch_player(
            player_id=player_id,
            reason=reason,
            by=request.user.username,
            player_name=player_name,
        )
        record_mobile_audit(
            username=request.user.username,
            command="mobile_watch_player",
            request=request,
            server_number=server_number,
            incident_id=incident_id,
            arguments={"player_id": player_id, "reason": reason},
            result={"watched": True},
        )
        return api_response(
            command=command,
            failed=False,
            result={"player_id": player_id, "watched": True},
        )

    if not request.user.has_perm("api.can_remove_player_watch"):
        return _error(command, "Missing watchlist remove permission", 403)
    _rcon_api().unwatch_player(player_id=player_id)
    record_mobile_audit(
        username=request.user.username,
        command="mobile_unwatch_player",
        request=request,
        server_number=server_number,
        incident_id=incident_id,
        arguments={"player_id": player_id},
        result={"watched": False},
    )
    return api_response(
        command=command,
        failed=False,
        result={"player_id": player_id, "watched": False},
    )


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def incident_player_context(request, incident_id):
    """Return a bounded ten-minute event excerpt for an incident player.

    This deliberately exposes only the five event classes useful for first
    response. It is not a general purpose raw-log browser.
    """

    command = "mobile_incident_player_context"
    if disabled := _require_feature(command, "MOBILE_PLAYER_OPERATIONS"):
        return disabled
    if not request.user.has_perm("api.can_view_admin_incidents"):
        return _error(command, "Missing incident view permission", 403)
    if not request.user.has_perm("api.can_view_historical_logs"):
        return _error(command, "Missing historical log permission", 403)
    player_id = str(request.GET.get("player_id") or "").strip()
    if not player_id:
        return _error(command, "player_id is required", 400)
    try:
        from rcon.admin_incidents import IncidentNotFound, get_incident

        incident = get_incident(str(incident_id))
    except (IncidentNotFound, ValueError):
        return _error(command, "Incident not found", 404)
    server_number = int(incident.get("server_number", get_server_number()))
    if forwarded := _forward_get(request, server_number):
        return forwarded

    confirmed_players = {
        str(subject.get("player_id"))
        for subject in incident.get("subjects") or []
        if subject.get("kind") == "player"
        and subject.get("state") == "confirmed"
        and subject.get("player_id")
    }
    reporter_id = str(incident.get("reporter_id") or "")
    if player_id not in confirmed_players and player_id != reporter_id:
        return _error(command, "Player is not available in this incident", 403)
    try:
        report_time = _incident_time(incident.get("created_at"))
    except (TypeError, ValueError):
        return _error(command, "Incident timestamp is invalid", 500)
    start = report_time - timedelta(minutes=5)
    end = report_time + timedelta(minutes=5)
    logs = _rcon_api().get_historical_logs(
        player_id=player_id,
        from_=start,
        till=end,
        limit=80,
        time_sort="asc",
        exact_player_match=True,
        server_filter=str(server_number),
    )
    events: list[dict] = []
    seen: set[tuple] = set()
    for log in logs or []:
        event = _context_event(log)
        if event is None:
            continue
        marker = (
            event["type"],
            str(event.get("occurred_at")),
            event.get("actor_name"),
            event.get("other_name"),
            event.get("message"),
        )
        if marker in seen:
            continue
        seen.add(marker)
        events.append(event)
    limit = min(max(int(request.GET.get("limit", 5)), 1), 50)
    return api_response(
        command=command,
        failed=False,
        result={
            "incident_id": str(incident_id),
            "player_id": player_id,
            "server_number": server_number,
            "window_start": start,
            "window_end": end,
            "events": events[:limit],
            "total": len(events),
        },
    )


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def live_status(request, server_number):
    """Read-only server situation with each field guarded by its CRCON right."""

    command = "mobile_live_status"
    if disabled := _require_feature(command, "MOBILE_LIVE_STATUS"):
        return disabled
    try:
        server_number = int(server_number)
    except (TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    if forwarded := _forward_get(request, server_number):
        return forwarded
    permissions = {
        "status": request.user.has_perm("api.can_view_get_status"),
        "gamestate": request.user.has_perm("api.can_view_gamestate"),
        "next_map": request.user.has_perm("api.can_view_next_map"),
        "queue": request.user.has_perm("api.can_view_queue_length"),
        "ingame_admins": request.user.has_perm("api.can_view_ingame_admins"),
        "crcon_admins": request.user.has_perm("api.can_view_online_admins"),
    }
    if not any(permissions.values()):
        return _error(command, "Missing live status permission", 403)
    api = _rcon_api()
    result = {"server_number": server_number, "captured_at": timezone.now()}
    if permissions["status"]:
        result["status"] = api.get_status()
    if permissions["gamestate"]:
        game = api.get_gamestate()
        result["match"] = {
            "current_map": game.get("current_map"),
            "time_remaining": game.get("raw_time_remaining"),
            "time_remaining_seconds": int(game.get("time_remaining").total_seconds())
            if game.get("time_remaining")
            else None,
            "team_counts": {
                "allies": game.get("num_allied_players"),
                "axis": game.get("num_axis_players"),
            },
            "team_scores": {
                "allies": game.get("allied_score"),
                "axis": game.get("axis_score"),
            },
        }
    if permissions["next_map"]:
        result["next_map"] = api.get_next_map()
    if permissions["queue"]:
        result["queue_length"] = api.get_queue_length()
    if permissions["ingame_admins"]:
        result["ingame_admin_count"] = len(api.get_ingame_mods() or [])
    if permissions["crcon_admins"]:
        result["crcon_admin_count"] = len(api.get_online_mods() or [])
    return api_response(command=command, failed=False, result=result)


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def action_templates(request):
    """Expose CRCON's shared player-message and reason templates to mobile.

    Template authoring remains in the existing CRCON settings UI.  Returning
    only action-safe categories avoids disclosing unrelated broadcast or
    welcome-message templates through the mobile device API.
    """

    command = "mobile_action_templates"
    if disabled := _require_enabled(command):
        return disabled
    if not request.user.has_perm("api.can_view_message_templates"):
        return _error(command, "Missing message template permission", 403)
    return api_response(
        command=command,
        failed=False,
        result={
            "message": get_message_templates(MessageTemplateCategory.MESSAGE),
            "reason": get_message_templates(MessageTemplateCategory.REASON),
        },
    )


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def roster(request, server_number):
    command = "mobile_server_roster"
    if disabled := _require_enabled(command):
        return disabled
    try:
        server_number = int(server_number)
    except (TypeError, ValueError) as exc:
        return _error(command, str(exc), 400)
    if forwarded := _forward_get(request, server_number):
        return forwarded
    try:
        team_view = _team_view_for_user(request)
    except PermissionError as exc:
        return _error(command, str(exc), 403)
    return api_response(
        command=command,
        failed=False,
        result={"server_number": server_number, "teams": team_view},
    )


@csrf_exempt
@login_required()
@require_http_methods(["GET"])
def squad_detail(request, server_number, team, squad):
    command = "mobile_squad_detail"
    if disabled := _require_enabled(command):
        return disabled
    server_number = int(server_number)
    if forwarded := _forward_get(request, server_number):
        return forwarded
    try:
        team_view = _team_view_for_user(request)
    except PermissionError as exc:
        return _error(command, str(exc), 403)
    selected_team = next(
        (
            (team_name, value)
            for team_name, value in team_view.items()
            if str(team_name).casefold() == str(team).casefold()
        ),
        None,
    )
    if not selected_team:
        return _error(command, "Team not found", 404)
    squad_data = next(
        (
            (name, value)
            for name, value in (selected_team[1].get("squads") or {}).items()
            if str(name).casefold() == str(squad).casefold()
        ),
        None,
    )
    if not squad_data:
        return _error(command, "Squad not found", 404)
    return api_response(
        command=command,
        failed=False,
        result={
            "server_number": server_number,
            "team": selected_team[0],
            "squad_name": squad_data[0],
            **squad_data[1],
        },
    )
