"""Permission-aware player and squad context for the native mobile client."""

from django.http import HttpResponse
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from rcon.utils import get_server_number

from .auth import api_response, login_required
from .decorators import require_http_methods
from .mobile import _error, _require_enabled
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
    return api_response(
        command=command,
        failed=False,
        result={
            "player_id": str(player_id),
            "server_number": server_number,
            "capabilities": capabilities,
            "history": history,
            "live": live,
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
