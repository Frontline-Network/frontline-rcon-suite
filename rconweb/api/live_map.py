"""Server-local, permission-checked tactical API. Never calls game-server commands."""
import hashlib
import json
import math
import time
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from rcon.live_map import storage
from rcon.live_map.domain import UNAVAILABLE, calibrate
from rcon.live_map.service import key, read_pending, read_snapshot
from rcon.admin_incidents import IncidentConflict, IncidentNotFound
from .auth import api_response, login_required
from .mobile_audit import record_mobile_audit

VIEW = "api.can_view_live_map"
MANAGE = "api.can_manage_live_map"
CASES = "api.can_view_live_map_cases"


def resources():
    from rcon.cache_utils import get_redis_client
    from rcon.utils import get_server_number
    return get_redis_client(), int(get_server_number())


def endpoint(permission=VIEW, methods=("GET",)):
    def decorate(func):
        @csrf_exempt
        @login_required()
        @wraps(func)
        def wrapped(request, **kwargs):
            if not request.user.has_perms([VIEW, permission]):
                raise PermissionDenied
            if request.method not in methods:
                return api_response(failed=True, error="Methode nicht erlaubt", status_code=405)
            try:
                result = func(request, **kwargs)
                response = api_response(result=result, failed=False, command="live_map")
                response["Cache-Control"] = "private, no-store"
                return response
            except IncidentConflict as exc:
                return api_response(failed=True, error=str(exc), status_code=409)
            except IncidentNotFound as exc:
                return api_response(failed=True, error=str(exc), status_code=404)
            except (ValueError, TypeError, KeyError) as exc:
                return api_response(failed=True, error=str(exc), status_code=400)
            except LookupError as exc:
                return api_response(failed=True, error=str(exc), status_code=404)
        return wrapped
    return decorate


def body(request):
    if len(request.body) > 16384 or request.content_type != "application/json":
        raise ValueError("Kleine JSON-Anfrage erforderlich")
    result = json.loads(request.body)
    if not isinstance(result, dict):
        raise ValueError("Ungültige Anfrage")
    return result


def audit(request, command, server, arguments=None):
    record_mobile_audit(username=request.user.username, command=f"live_map_{command}",
                        server_number=server, arguments=arguments or {})


def combined_history(red, server, start, end, round_id=None):
    frames = storage.history(server, start, end, round_id)
    frames += [f for f in read_pending(red, server) if start <= f["captured_at"] <= end and (not round_id or f["round_id"] == round_id)]
    return sorted({(f["round_id"], f["captured_at"]): f for f in frames}.values(), key=lambda f: f["captured_at"])


@endpoint()
def capabilities(request):
    red, server = resources()
    settings = storage.get_settings(server)
    snapshot = read_snapshot(red, server)
    # No object provider has been verified for either game. Discovery is honest
    # about each capability rather than deriving objects from nearby players.
    result = {"server_number": server, "enabled": settings["enabled"], "monitor_enabled": settings["monitor_enabled"],
              "positions": "observed" if snapshot and snapshot["quality"]["valid_positions"] else "not_observed",
              "objects": {k: {"available": False, "reason": UNAVAILABLE} for k in ("positions", "losses", "actors")},
              "calibrated": bool(snapshot and snapshot.get("calibration", {}) and snapshot["calibration"].get("verified")),
              "permissions": {"manage": request.user.has_perm(MANAGE), "cases": request.user.has_perm(CASES)},
              "retention_hours": 24, "case_retention_days": 30}
    audit(request, "open", server)
    return result


@endpoint()
def snapshot(request):
    red, server = resources()
    settings = storage.get_settings(server)
    if not settings["enabled"]:
        return {"enabled": False, "snapshot": None}
    frame = read_snapshot(red, server)
    if frame:
        frame["age_seconds"] = max(0, time.time() - frame["captured_at"])
        frame["stale"] = frame["age_seconds"] > max(6, frame["collector_interval"] * 3)
        if not settings["monitor_enabled"]:
            frame["signals"] = []
        statuses = storage.review_statuses(server)
        for signal in frame["signals"]:
            signal["review"] = statuses.get(signal["id"])
    return {"enabled": True, "snapshot": frame}


@endpoint()
def history(request):
    red, server = resources()
    start, end = float(request.GET["start"]), float(request.GET["end"])
    if not math.isfinite(start) or not math.isfinite(end):
        raise ValueError("Ungültiger Zeitraum")
    result = combined_history(red, server, start, end, request.GET.get("round_id"))
    audit(request, "history", server, {"start": start, "end": end})
    return {"frames": result, "start": start, "end": end}


@endpoint()
def rounds(request):
    red, server = resources()
    result = storage.rounds(server)
    current = read_snapshot(red, server)
    if current:
        existing = next((r for r in result if r["round_id"] == current["round_id"]), None)
        if existing:
            existing["end"] = current["captured_at"]
        else:
            result.insert(0, {"round_id": current["round_id"], "start": current["captured_at"], "end": current["captured_at"]})
    return result


@endpoint(MANAGE, ("POST",))
def settings(request):
    red, server = resources()
    data = body(request)
    if not data or set(data) - {"enabled", "monitor_enabled"} or any(type(v) is not bool for v in data.values()):
        raise ValueError("Nur die beiden Ein-/Ausschalter sind zulässig")
    value = storage.update_settings(server, lambda s: s.update(data))
    if not value["enabled"]:
        red.delete(key(server, "snapshot"))
    audit(request, "settings", server, data)
    return {k: value[k] for k in ("enabled", "monitor_enabled")}


def confirmed_aliases(player_id):
    from sqlalchemy import select
    from rcon.models import PlayerID, enter_session
    from rcon.player_history import get_player_identity_links
    with enter_session() as session:
        row = session.scalar(select(PlayerID).where(PlayerID.player_id == player_id))
        if not row:
            return [player_id]
        links = get_player_identity_links(session, [row]).get(player_id, {})
        return list({player_id, *(p["player_id"] for p in links.get("linked_accounts", []))})


@endpoint(methods=("GET", "POST", "DELETE"))
def monitors(request):
    red, server = resources()
    if request.method == "GET":
        return storage.get_settings(server)["monitors"]
    if not request.user.has_perm(MANAGE):
        raise PermissionDenied
    data = body(request)
    player_id = str(data.get("player_id", ""))
    if not player_id or len(player_id) > 100:
        raise ValueError("Spieler-ID erforderlich")
    if request.method == "DELETE":
        storage.update_settings(server, lambda s: s.update(monitors=[m for m in s["monitors"] if m["player_id"] != player_id]))
    else:
        scope = data.get("scope", "session")
        if scope not in {"session", "permanent"}:
            raise ValueError("Ungültiger Beobachtungszeitraum")
        current = read_snapshot(red, server)
        if not current or time.time() - current["captured_at"] > 30:
            raise ValueError("Aktuelle Spielerdaten erforderlich")
        player = next((p for p in current["players"] if p["player_id"] == player_id), None)
        if not player or (scope == "session" and not player["session_id"]):
            raise ValueError("Spieler bzw. aktuelle Sitzung nicht verfügbar")
        item = {"player_id": player_id, "name": player["name"], "scope": scope, "session_id": player["session_id"],
                "aliases": confirmed_aliases(player_id), "created_by": request.user.username}
        def add(value):
            items = [m for m in value["monitors"] if m["player_id"] != player_id]
            if len(items) >= 200:
                raise ValueError("Maximal 200 Beobachtungseinträge")
            value["monitors"] = items + [item]
        storage.update_settings(server, add)
    audit(request, "monitor", server, {"player_id": player_id, "method": request.method})
    return storage.get_settings(server)["monitors"]


@endpoint(MANAGE, ("POST",))
def calibration(request):
    _, server = resources()
    from .views import rcon_api
    data = body(request)
    map_id = str(data["map_id"]).lower()
    known = {str(m.id).lower() for m in rcon_api.game_profile.maps.values()}
    if map_id not in known:
        raise ValueError("Unbekannte Karte")
    result = calibrate(data["anchors"], data["checks"], data["units_per_meter"], data["source"])
    calibration_key = f"{rcon_api.config.game.value}:{map_id}"
    storage.update_settings(server, lambda s: s["calibrations"].update({calibration_key: result}))
    audit(request, "calibration", server, {"map_id": map_id, "max_error_m": result["max_error_m"]})
    return result


@endpoint(CASES, ("GET", "POST"))
def reviews(request, signal_id=None):
    from rcon.admin_incidents import create_incident, mutate_incident
    red, server = resources()
    if request.method == "GET":
        if signal_id is None:
            return storage.review_statuses(server)
        evidence = storage.get_evidence(server, signal_id)
        audit(request, "evidence", server, {"signal_id": signal_id})
        return evidence
    data = body(request)
    action = data.get("action")
    permission = {"claim": "api.can_claim_admin_incidents", "dismiss": "api.can_resolve_admin_incidents", "save": "api.can_create_admin_incidents"}.get(action)
    if not permission or not request.user.has_perm(permission):
        raise PermissionDenied
    frame = read_snapshot(red, server)
    if not frame or time.time() - frame["captured_at"] > 30:
        raise ValueError("Aktueller Hinweis erforderlich")
    signal = next((s for s in frame["signals"] if s["id"] == signal_id), None)
    if not signal:
        raise LookupError("Hinweis nicht mehr aktiv")
    states = storage.review_statuses(server)
    record = states.get(signal_id)
    if not record:
        if not request.user.has_perm("api.can_create_admin_incidents"):
            raise PermissionDenied
        incident, _ = create_incident(server_number=server, source="manual", actor=request.user.username,
                                      reason="Wiederholte Begegnungen: menschliche Prüfung angefordert. Kein Nachweis für Streamsniping.",
                                      target_id=signal["attacker"], target_name=signal.get("attacker_name") or signal["attacker"],
                                      idempotency_key=hashlib.sha256(f"live-map:{server}:{signal_id}".encode()).hexdigest())
        storage.attach_review(server, signal_id, incident["id"])
        record = {"incident_id": incident["id"], "revision": incident["revision"]}
    if action == "save":
        now = time.time()
        start, end = max(now - 86400, signal["first_at"] - 30), min(now, signal["last_at"] + 5)
        # An encounter window is 15 min; keep the request bounded.
        start = max(start, end - 900)
        frames = combined_history(red, server, start, end, signal["round_id"])
        ids = {signal["attacker"], signal["victim"]}
        selected = [{**f, "players": [p for p in f["players"] if p["player_id"] in ids],
                     "events": [e for e in f["events"] if e["attacker"] in ids or e["victim"] in ids]} for f in frames]
        storage.attach_review(server, signal_id, record["incident_id"], {"signal": signal, "frames": selected})
    else:
        mutate_incident(record["incident_id"], actor=request.user.username, operation="dismissed" if action == "dismiss" else action,
                        expected_revision=int(data.get("revision", record["revision"])))
    audit(request, "review", server, {"signal_id": signal_id, "action": action})
    return storage.review_statuses(server).get(signal_id)


urlpatterns = [path("capabilities", capabilities), path("snapshot", snapshot), path("history", history),
               path("rounds", rounds), path("settings", settings), path("monitors", monitors),
               path("calibration", calibration), path("reviews", reviews), path("reviews/<str:signal_id>", reviews)]
