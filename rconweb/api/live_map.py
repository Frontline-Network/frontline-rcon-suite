"""Server-local, permission-checked tactical API. Never calls game-server commands."""
import hashlib
import json
import math
import time
from functools import wraps

from django.core.exceptions import PermissionDenied
from django.urls import path
from django.views.decorators.csrf import csrf_exempt

from rcon.admin_incidents import IncidentConflict, IncidentNotFound
from rcon.live_map import storage
from rcon.live_map.domain import UNAVAILABLE, calibrate
from rcon.live_map.projections import projection_ready
from rcon.live_map.service import key, read_pending, read_snapshot

from .auth import api_response, login_required
from .mobile_audit import record_mobile_audit

VIEW = "api.can_view_live_map"
MANAGE = "api.can_manage_live_map"
CASES = "api.can_view_live_map_cases"
ARCHIVES = "api.can_manage_live_map_archives"


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


def combined_history(red, server, start, end, round_id=None, archive_id=None):
    frames = storage.history(server, start, end, round_id, archive_id=archive_id)
    frames += [f for f in read_pending(red, server) if start <= f["captured_at"] <= end and (not round_id or f["round_id"] == round_id)]
    return sorted({(f["round_id"], f["captured_at"]): f for f in frames}.values(), key=lambda f: f["captured_at"])


def finite_time(request, name):
    value = float(request.GET[name])
    if not math.isfinite(value):
        raise ValueError("Ungültiger Zeitraum")
    return value


def profile_context(request, player_id):
    if not request.user.has_perm("api.can_view_player_info"):
        return None
    from rcon.player_history import get_player_profile
    profile = get_player_profile(player_id, 0) or {}
    steam = profile.get("steaminfo") or {}
    bans = steam.get("bans") or {}
    return {
        "source": "Steam Web API",
        "updated_at": steam.get("updated"),
        "steam_bans": {
            key: bans.get(key)
            for key in ("VACBanned", "NumberOfVACBans", "NumberOfGameBans", "DaysSinceLastBan")
            if key in bans
        },
        "has_bans": bool(steam.get("has_bans")),
        "note": "Profilkontext; fließt nicht in Auslösung oder Priorität ein.",
    }


@endpoint()
def capabilities(request):
    red, server = resources()
    settings = storage.get_settings(server)
    snapshot = read_snapshot(red, server)
    # No object provider has been verified for either game. Discovery is honest
    # about each capability rather than deriving objects from nearby players.
    result = {"server_number": server, "enabled": settings["enabled"], "monitor_enabled": settings["monitor_enabled"],
              "archive_enabled": settings["archive_enabled"], "detection_enabled": settings["detection_enabled"],
              "positions": "observed" if snapshot and snapshot["quality"]["valid_positions"] else "not_observed",
              "objects": {k: {"available": False, "reason": UNAVAILABLE} for k in ("positions", "losses", "actors")},
              "calibrated": bool(snapshot and snapshot.get("calibration", {}) and snapshot["calibration"].get("verified")),
              "display_ready": projection_ready((snapshot or {}).get("calibration")),
              "permissions": {"manage": request.user.has_perm(MANAGE), "cases": request.user.has_perm(CASES),
                              "archives": request.user.has_perm(ARCHIVES)},
              "retention_hours": 24, "case_retention_days": 30,
              "archive_retention_days": [30, 90], "archive_limits": {"rounds": 50, "bytes": 1073741824}}
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
        frame["stale"] = frame["age_seconds"] > max(12, frame["collector_interval"] * 3 + 2)
        if not settings["monitor_enabled"]:
            frame["signals"] = []
        if not settings["detection_enabled"] or not request.user.has_perm(CASES):
            frame["detections"] = []
        statuses = storage.review_statuses(server)
        for signal in frame["signals"] + frame.get("detections", []):
            signal["review"] = statuses.get(signal["id"])
    return {"enabled": True, "snapshot": frame}


@endpoint()
def history(request):
    red, server = resources()
    start, end = finite_time(request, "start"), finite_time(request, "end")
    archive_id = request.GET.get("archive_id")
    if archive_id and not request.user.has_perm(CASES):
        raise PermissionDenied
    result = combined_history(red, server, start, end, request.GET.get("round_id"), archive_id)
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


@endpoint(MANAGE, ("GET", "POST"))
def settings(request):
    red, server = resources()
    if request.method == "GET":
        value = storage.get_settings(server)
        return {key: value[key] for key in ("enabled", "monitor_enabled", "archive_enabled", "detection_enabled", "detection_profile")}
    data = body(request)
    switches = {"enabled", "monitor_enabled", "archive_enabled", "detection_enabled"}
    if not data or set(data) - (switches | {"detection_profile"}):
        raise ValueError("Unbekannte Einstellung")
    if any(type(data[key]) is not bool for key in set(data) & switches):
        raise ValueError("Schalter müssen boolesch sein")
    profile = data.get("detection_profile")
    if profile is not None:
        allowed = set(storage.DETECTION_PROFILE)
        if not isinstance(profile, dict) or set(profile) != allowed:
            raise ValueError("Vollständiges Prüfprofil erforderlich")
        bounds = {
            "min_kills": (1, 500), "killrate_infantry": (.1, 20), "killrate_mg": (.1, 20),
            "killrate_armor": (.1, 20), "killrate_artillery": (.1, 20), "burst_kills": (2, 100),
            "burst_unique_victims": (2, 100), "burst_seconds": (5, 900), "movement_mps": (1, 1000),
            "movement_consecutive": (1, 20),
        }
        if any(isinstance(value, bool) or not isinstance(value, (int, float)) or not bounds[key][0] <= value <= bounds[key][1]
               for key, value in profile.items()):
            raise ValueError("Prüfprofil enthält ungültige Grenzwerte")
        if profile["burst_unique_victims"] > profile["burst_kills"]:
            raise ValueError("Eindeutige Opfer dürfen Killserien-Kills nicht überschreiten")
    def change(value):
        value.update({key: data[key] for key in set(data) & switches})
        if profile is not None:
            value["detection_profile"] = profile
    value = storage.update_settings(server, change)
    if not value["enabled"]:
        red.delete(key(server, "snapshot"))
    audit(request, "settings", server, data)
    return {key: value[key] for key in ("enabled", "monitor_enabled", "archive_enabled", "detection_enabled", "detection_profile")}


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


@endpoint()
def events(request):
    _, server = resources()
    start, end = finite_time(request, "start"), finite_time(request, "end")
    round_id = request.GET.get("round_id")
    archive_id = request.GET.get("archive_id")
    if archive_id and not request.user.has_perm(CASES):
        raise PermissionDenied
    values = storage.event_history(server, start, end, round_id, archive_id=archive_id)
    markers = []
    if request.user.has_perm(CASES):
        markers = [
            {"id": item["id"], "time": item["last_at"], "kind": "detection", "severity": item["severity"],
             "player_id": item["player_id"], "player_name": item["player_name"]}
            for item in storage.list_detections(server, round_id=round_id)
            if start <= item["last_at"] <= end
        ]
    audit(request, "events", server, {"start": start, "end": end})
    return {"events": values, "markers": markers}


@endpoint(CASES)
def detections(request, detection_id=None):
    _, server = resources()
    if not storage.get_settings(server)["detection_enabled"]:
        if detection_id:
            raise LookupError("Spielerprüfung ist für diese Instanz deaktiviert")
        return {"detections": []}
    if detection_id:
        result = storage.get_detection(server, detection_id)
        result["previous_24h"] = [
            item for item in storage.list_detections(server, player_id=result["player_id"], limit=50)
            if item["round_id"] != result["round_id"]
        ]
        result["profile_context"] = profile_context(request, result["player_id"])
        audit(request, "detection", server, {"detection_id": detection_id})
        return result
    result = storage.list_detections(
        server,
        round_id=request.GET.get("round_id"),
        player_id=request.GET.get("player_id"),
        status=request.GET.get("status"),
        limit=int(request.GET.get("limit", 200)),
    )
    return {"detections": result}


@endpoint(CASES, ("GET", "POST", "PATCH", "DELETE"))
def archives(request, archive_id=None):
    red, server = resources()
    settings_value = storage.get_settings(server)
    if request.method == "GET":
        return {"archives": storage.list_archives(server)}
    if not request.user.has_perm(ARCHIVES):
        raise PermissionDenied
    if not settings_value["archive_enabled"]:
        raise ValueError("Rundensicherung ist für diese Instanz deaktiviert")
    data = {} if request.method == "DELETE" and not request.body else body(request)
    if request.method == "POST":
        round_id = str(data.get("round_id", ""))
        available = next((item for item in storage.rounds(server) if item["round_id"] == round_id), None)
        current = read_snapshot(red, server)
        is_current = bool(current and current.get("round_id") == round_id)
        if not available and not is_current:
            raise LookupError("Runde nicht verfügbar")
        if is_current and not current.get("quality", {}).get("round_confirmed"):
            raise ValueError("Rundenbeginn ist noch nicht bestätigt")
        start_at = (available or {}).get("start") or current["round_start"]
        end_at = current["captured_at"] if is_current else available["end"]
        result = storage.create_archive(
            server, round_id, start_at, end_at, request.user.username,
            data.get("reason"), data.get("retention_days"), data.get("incident_id"),
            collecting=is_current,
        )
        audit(request, "archive_create", server, {"archive_id": result["id"], "round_id": round_id})
        return result
    if not archive_id:
        raise ValueError("Archiv-ID erforderlich")
    if request.method == "PATCH":
        if set(data) - {"retention_days", "incident_id"} or not data:
            raise ValueError("Nur Aufbewahrung und Fallzuordnung sind änderbar")
        result = storage.update_archive(server, archive_id, **data)
        audit(request, "archive_update", server, {"archive_id": archive_id})
        return result
    result = storage.delete_archive(server, archive_id)
    audit(request, "archive_delete", server, {"archive_id": archive_id, "round_id": result["round_id"]})
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
    signal = None
    if frame and time.time() - frame["captured_at"] <= 30:
        signal = next((s for s in frame.get("signals", []) if s["id"] == signal_id), None)
    detection = None
    if signal is None:
        try:
            detection = storage.get_detection(server, signal_id)
            signal = detection.get("evidence") or detection
        except LookupError:
            pass
    if not signal:
        raise LookupError("Hinweis nicht mehr verfügbar")
    states = storage.review_statuses(server)
    record = states.get(signal_id)
    if not record:
        if not request.user.has_perm("api.can_create_admin_incidents"):
            raise PermissionDenied
        gameplay = detection is not None
        target_id = signal.get("player_id") if gameplay else signal["attacker"]
        target_name = signal.get("player_name") if gameplay else signal.get("attacker_name")
        incident, _ = create_incident(server_number=server, source="manual", actor=request.user.username,
                                      reason=("Auffälliges Spielmuster: menschliche Prüfung angefordert. Kein Cheatnachweis."
                                              if gameplay else "Wiederholte Begegnungen: menschliche Prüfung angefordert. Kein Nachweis für Streamsniping."),
                                      target_id=target_id, target_name=target_name or target_id,
                                      idempotency_key=hashlib.sha256(f"live-map:{server}:{signal_id}".encode()).hexdigest())
        storage.attach_review(server, signal_id, incident["id"])
        if detection:
            storage.attach_detection_incident(server, signal_id, incident["id"])
        record = {"incident_id": incident["id"], "revision": incident["revision"]}
    if action == "save":
        if detection:
            if not request.user.has_perm(ARCHIVES):
                raise PermissionDenied
            settings_value = storage.get_settings(server)
            if not settings_value["archive_enabled"]:
                raise ValueError("Rundensicherung ist für diese Instanz deaktiviert")
            available = next((item for item in storage.rounds(server) if item["round_id"] == signal["round_id"]), None)
            if not available:
                raise LookupError("Runde nicht mehr verfügbar")
            current = read_snapshot(red, server)
            collecting = bool(current and current.get("round_id") == signal["round_id"])
            archive = storage.create_archive(
                server, signal["round_id"], available["start"], available["end"], request.user.username,
                data.get("reason") or "Prüfhinweis: auffälliges Spielmuster",
                data.get("retention_days", 30), record["incident_id"], collecting=collecting,
            )
            storage.attach_review(server, signal_id, record["incident_id"], {"signal": signal, "archive_id": archive["id"]})
            storage.attach_detection_incident(server, signal_id, record["incident_id"], "claimed")
        else:
            now = time.time()
            start, end = max(now - 86400, signal["first_at"] - 30), min(now, signal["last_at"] + 5)
            start = max(start, end - 900)
            frames = combined_history(red, server, start, end, signal["round_id"])
            ids = {signal["attacker"], signal["victim"]}
            selected = [{**f, "players": [p for p in f["players"] if p["player_id"] in ids],
                         "events": [e for e in f["events"] if e["attacker"] in ids or e["victim"] in ids]} for f in frames]
            storage.attach_review(server, signal_id, record["incident_id"], {"signal": signal, "frames": selected})
    else:
        mutate_incident(record["incident_id"], actor=request.user.username, operation="dismissed" if action == "dismiss" else action,
                        expected_revision=int(data.get("revision", record["revision"])))
        if detection:
            updated = storage.review_statuses(server).get(signal_id)
            storage.attach_detection_incident(server, signal_id, record["incident_id"], updated.get("status") if updated else None)
    audit(request, "review", server, {"signal_id": signal_id, "action": action})
    return storage.review_statuses(server).get(signal_id)


urlpatterns = [path("capabilities", capabilities), path("snapshot", snapshot), path("history", history),
               path("rounds", rounds), path("events", events), path("settings", settings), path("monitors", monitors),
               path("calibration", calibration), path("detections", detections), path("detections/<str:detection_id>", detections),
               path("archives", archives), path("archives/<str:archive_id>", archives),
               path("reviews", reviews), path("reviews/<str:signal_id>", reviews)]
