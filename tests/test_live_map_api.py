import copy
import json
import os
import time
from contextlib import contextmanager
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")

import django

django.setup()
from django.conf import settings
from django.http import JsonResponse
from django.test import RequestFactory

import rcon.admin_incidents as incidents
from api import auth
from api import live_map as api
from api.tactical_privacy import TacticalPrivacyMiddleware
from rcon.live_map import storage
from rcon.live_map.models import (
    TacticalArchive,
    TacticalBlock,
    TacticalDetection,
    TacticalReview,
    TacticalSettings,
)
from rcon.models import AdminIncident, AdminIncidentEvent, AdminIncidentSubject
from rconweb.rconweb.middleware import SessionCsrfProtectionMiddleware


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://")
    for model in (
        TacticalBlock,
        TacticalReview,
        TacticalSettings,
        TacticalArchive,
        TacticalDetection,
        AdminIncident,
        AdminIncidentEvent,
        AdminIncidentSubject,
    ):
        model.__table__.create(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)
    @contextmanager
    def session():
        with sessions.begin() as db:
            yield db
    monkeypatch.setattr(storage, "enter_session", session)
    monkeypatch.setattr(incidents, "enter_session", session)
    yield session
    engine.dispose()


@pytest.fixture
def request_api(monkeypatch, database):
    monkeypatch.setattr(auth, "check_api_key", lambda r: None)
    monkeypatch.setattr(api, "audit", lambda *a, **kw: None)
    red = SimpleNamespace(delete=lambda *a: None)
    monkeypatch.setattr(api, "resources", lambda: (red, 1))
    monkeypatch.setattr(api, "read_pending", lambda *a: [])
    monkeypatch.setattr(api, "read_snapshot", lambda *a: None)
    factory = RequestFactory()
    def call(view, method="GET", data=None, perms=(), **kwargs):
        request = getattr(factory, method.lower())("/api/live-map/v1/test", data=json.dumps(data or {}) if method != "GET" else data or {}, content_type="application/json")
        request.user = SimpleNamespace(username="tester", is_authenticated=True, is_active=True,
                                       has_perm=lambda p: p in perms, has_perms=lambda ps: all(p in perms for p in ps))
        return view(request, **kwargs)
    return call


def test_map_right_is_required_even_for_monitor_or_case_admin(request_api):
    assert request_api(api.capabilities).status_code == 403
    assert request_api(api.reviews, perms=[api.CASES]).status_code == 403
    assert request_api(api.settings, "POST", {"enabled": True}, [api.MANAGE]).status_code == 403
    assert request_api(api.capabilities, perms=[api.VIEW]).status_code == 200
    assert request_api(api.settings, "POST", {"enabled": True}, [api.VIEW]).status_code == 403
    assert request_api(api.monitors, "DELETE", {"player_id": "a"}, [api.VIEW]).status_code == 403


def test_switches_default_off_and_accept_only_explicit_booleans(request_api):
    assert not json.loads(request_api(api.capabilities, perms=[api.VIEW]).content)["result"]["enabled"]
    assert request_api(api.settings, "POST", {"enabled": "true"}, [api.VIEW, api.MANAGE]).status_code == 400
    assert request_api(api.settings, "POST", {"enabled": True, "calibrations": {}}, [api.VIEW, api.MANAGE]).status_code == 400
    assert request_api(api.settings, "POST", {"enabled": True}, [api.VIEW, api.MANAGE]).status_code == 200
    assert storage.get_settings(1)["enabled"]
    assert not storage.get_settings(2)["enabled"]


def test_legacy_roster_public_mobile_and_nested_raw_are_redacted():
    source = {"result": [{"name": "keep", "world_position": {"x": 1}, "p_coord": {"x": 9}}],
              "forwards_results": {"2": {"WorldPosition": {"X": 5}}},
              "raw": json.dumps({"WorldPosition": {"X": 8}})}
    original = copy.deepcopy(source)
    for route in ("/api/get_detailed_players", "/api/get_team_view", "/api/mobile/v1/players", "/api/get_map_history"):
        request = RequestFactory().get(route)
        request.user = SimpleNamespace(is_authenticated=False)
        response = TacticalPrivacyMiddleware(lambda _: JsonResponse(source))(request)
        parsed = json.loads(response.content)
        assert parsed["result"] == [{"name": "keep"}]
        assert parsed["forwards_results"] == {"2": {}}
        assert json.loads(parsed["raw"]) == {}
    assert source == original
    request.user = SimpleNamespace(is_authenticated=True, is_active=True, has_perm=lambda _: True)
    authorized = TacticalPrivacyMiddleware(lambda _: JsonResponse(source))(request)
    assert json.loads(authorized.content) == source
    assert authorized["Cache-Control"] == "private, no-store"


def test_all_tactical_writes_use_existing_session_csrf_guard():
    guard = SessionCsrfProtectionMiddleware(lambda _: JsonResponse({}))
    for view in (api.settings, api.monitors, api.calibration, api.reviews, api.archives):
        request = RequestFactory().post("/api/live-map/v1/test", data="{}", content_type="application/json")
        request.COOKIES[settings.SESSION_COOKIE_NAME] = "browser-session"
        assert guard.process_view(request, view, (), {}).status_code == 403


def test_history_is_bounded_and_server_scoped(database):
    now = time.time()
    storage.save_block(1, [{"round_id": "r1", "captured_at": now - 60, "players": []}])
    storage.save_block(2, [{"round_id": "r2", "captured_at": now - 60, "players": [{"player_id": "private"}]}])
    assert [f["round_id"] for f in storage.history(1, now - 90, now, now=now)] == ["r1"]
    assert not storage.history(1, now - 90, now, round_id="r2", now=now)
    for start, end in ((now - 90000, now - 89500), (now - 1000, now), (now, now + 30)):
        with pytest.raises(ValueError):
            storage.history(1, start, end, now=now)


def test_event_history_deduplicates_kills_and_marks_real_data_gaps(database):
    now = time.time()
    kill = {
        "id": "kill",
        "round_id": "round",
        "time": now - 48,
        "attacker": "a",
        "victim": "v",
        "teamkill": False,
    }
    storage.save_block(
        1,
        [
            {
                "round_id": "round",
                "captured_at": now - 50,
                "collector_interval": 2,
                "events": [kill],
            },
            {
                "round_id": "round",
                "captured_at": now - 20,
                "collector_interval": 2,
                "events": [kill],
            },
        ],
    )
    events = storage.event_history(1, now - 60, now, "round", now=now)
    assert [item["kind"] for item in events].count("kill") == 1
    gap = next(item for item in events if item["kind"] == "data_gap")
    assert gap["duration_seconds"] == 30


def test_retention_expires_private_evidence_without_deleting_generic_cases(database, monkeypatch):
    now = 1800000000.
    monkeypatch.setattr(storage.time, "time", lambda: now)
    storage.save_block(1, [{"round_id": "r", "captured_at": now - 86401}])
    storage.save_block(2, [{"round_id": "other", "captured_at": now - 86401}])
    storage.attach_review(1, "a", "case", {"frames": [{"position": {"x": 1}}]})
    storage.attach_review(1, "b", "case2")
    storage.cleanup(1, now + 86400)
    with database() as db:
        assert not db.scalars(select(TacticalBlock).where(TacticalBlock.server_number == 1)).all()
        assert db.scalars(select(TacticalBlock).where(TacticalBlock.server_number == 2)).all()
        assert db.get(TacticalReview, (1, "b")) is None
        assert db.get(TacticalReview, (1, "a")) is not None
    with pytest.raises(LookupError):
        storage.get_evidence(2, "a")
    storage.cleanup(1, now + 30 * 86400)
    with pytest.raises(LookupError):
        storage.get_evidence(1, "a")


def test_case_claim_dismiss_and_private_excerpt_use_existing_incident_engine(request_api, monkeypatch):
    now = time.time()
    signal = {"id": "sig", "round_id": "r", "attacker": "a", "victim": "v", "first_at": now - 60, "last_at": now - 5}
    frame = {"round_id": "r", "captured_at": now, "signals": [signal]}
    monkeypatch.setattr(api, "read_snapshot", lambda *a: copy.deepcopy(frame))
    perms = [api.VIEW, api.CASES, "api.can_create_admin_incidents", "api.can_claim_admin_incidents", "api.can_resolve_admin_incidents"]
    response = request_api(api.reviews, "POST", {"action": "claim"}, perms, signal_id="sig")
    assert response.status_code == 200, response.content
    record = json.loads(response.content)["result"]
    assert record["status"] == "claimed"
    response = request_api(api.reviews, "POST", {"action": "dismiss", "revision": record["revision"]}, perms, signal_id="sig")
    assert response.status_code == 200, response.content
    assert json.loads(response.content)["result"]["status"] == "dismissed"
    assert request_api(api.reviews, "GET", perms=[api.VIEW], signal_id="sig").status_code == 403
    assert request_api(api.reviews, "POST", {"action": "save"}, perms, signal_id="sig").status_code == 200
    incident = incidents.get_incident(record["incident_id"])
    assert "position" not in json.dumps(incident, default=str).lower()
    assert "signal" not in json.dumps(incident, default=str).lower()


def test_round_archive_pins_blocks_without_copy_and_can_be_extended(database):
    now = 1800000000.0
    storage.save_block(
        1,
        [
            {"round_id": "round", "captured_at": now - 60, "players": []},
            {"round_id": "round", "captured_at": now - 30, "players": []},
        ],
    )
    archive = storage.create_archive(
        1, "round", now - 60, now - 30, "tester", "Prüfung", 30, now=now
    )
    with database() as db:
        assert db.scalars(select(TacticalBlock)).one()
        assert db.scalars(select(TacticalArchive)).one().estimated_bytes > 0
    updated = storage.update_archive(
        1, archive["id"], retention_days=90, now=now
    )
    assert updated["expires_at"] == pytest.approx(updated["end"] + 90 * 86400)
    with pytest.raises(ValueError, match="nur verlängert"):
        storage.update_archive(
            1, archive["id"], retention_days=30, now=now
        )
    storage.cleanup(1, now + 2 * 86400)
    assert storage.history(
        1,
        now - 60,
        now - 30,
        "round",
        now=now + 2 * 86400,
        archive_id=archive["id"],
    )


def test_archive_limits_reject_new_round_without_overwriting(database, monkeypatch):
    now = 1800000000.0
    storage.create_archive(1, "one", now - 10, now, "tester", "one", 30, now=now)
    monkeypatch.setattr(storage, "ARCHIVE_MAX_ROUNDS", 1)
    with pytest.raises(ValueError, match="50 Runden"):
        storage.create_archive(
            1, "two", now - 10, now, "tester", "two", 30, now=now
        )
    assert [item["round_id"] for item in storage.list_archives(1, now)] == ["one"]


def test_collecting_archive_keeps_future_blocks_until_round_finishes(database):
    now = 1800000000.0
    storage.save_block(
        1, [{"round_id": "live-round", "captured_at": now - 10, "players": []}]
    )
    archive = storage.create_archive(
        1,
        "live-round",
        now - 10,
        now - 10,
        "tester",
        "Laufende Prüfung",
        30,
        collecting=True,
        now=now,
    )
    storage.save_block(
        1, [{"round_id": "live-round", "captured_at": now + 10, "players": []}]
    )
    storage.finish_archive(1, "live-round", now + 20)
    updated = storage.list_archives(1, now)[0]
    assert updated["id"] == archive["id"]
    assert updated["status"] == "complete"
    assert updated["end"] == now + 20
    assert updated["bytes"] > archive["bytes"]


def test_archive_api_requires_separate_permission_and_feature_switch(request_api):
    now = time.time()
    storage.save_block(1, [{"round_id": "round", "captured_at": now - 10, "players": []}])
    perms = [api.VIEW, api.CASES]
    payload = {"round_id": "round", "retention_days": 30, "reason": "Prüfung"}
    assert request_api(api.archives, "POST", payload, perms).status_code == 403
    perms.append(api.ARCHIVES)
    assert request_api(api.archives, "POST", payload, perms).status_code == 400
    storage.update_settings(1, lambda value: value.update(archive_enabled=True))
    created = request_api(api.archives, "POST", payload, perms)
    assert created.status_code == 200, created.content
    archive_id = json.loads(created.content)["result"]["id"]
    assert request_api(api.archives, "PATCH", {"retention_days": 90}, perms, archive_id=archive_id).status_code == 200
    assert request_api(api.archives, "DELETE", {}, perms, archive_id=archive_id).status_code == 200


def test_persisted_detection_is_scoped_and_previous_rounds_are_context_only(request_api):
    now = time.time()
    storage.update_settings(1, lambda value: value.update(detection_enabled=True))
    base = {
        "kind": "gameplay_pattern",
        "severity": "review",
        "first_at": now - 60,
        "last_at": now - 10,
        "rule_version": "2",
        "signals": [{"kind": "kill_rate"}, {"kind": "kill_burst"}],
    }
    storage.upsert_detections(
        1,
        [
            {**base, "id": "current", "round_id": "r2", "player_id": "p", "player_name": "Player"},
            {**base, "id": "previous", "round_id": "r1", "player_id": "p", "player_name": "Player"},
        ],
        now,
    )
    storage.upsert_detections(
        2,
        [
            {
                **base,
                "id": "current",
                "round_id": "r2",
                "player_id": "other-server-player",
                "player_name": "Other",
            }
        ],
        now,
    )
    response = request_api(
        api.detections,
        perms=[api.VIEW, api.CASES],
        detection_id="current",
    )
    assert response.status_code == 200, response.content
    result = json.loads(response.content)["result"]
    assert result["severity"] == "review"
    assert [item["id"] for item in result["previous_24h"]] == ["previous"]
    assert storage.get_detection(2, "current", now)["player_id"] == "other-server-player"
