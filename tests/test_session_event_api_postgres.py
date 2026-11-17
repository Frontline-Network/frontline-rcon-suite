"""Permission and audit checks for session event review endpoints."""
import json
import os
from datetime import datetime
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "3")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")
import django
django.setup()

from api import auth, decorators, views
from django.test import RequestFactory
from rcon import session_event_review
from rcon.models import PendingPlayerConnect, PendingPlayerDisconnect, PlayerID, PlayerSession, SessionEventResolution, UnidentifiedSessionEvent


@pytest.fixture
def review_api(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "session_api_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    for model in (PlayerID, PlayerSession, PendingPlayerConnect, PendingPlayerDisconnect, SessionEventResolution, UnidentifiedSessionEvent):
        model.__table__.create(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(session_event_review, "get_session_maker", lambda: maker)
    monkeypatch.setattr("rcon.api_commands.get_server_number", lambda: "3")
    monkeypatch.setattr("rcon.api_commands.RconServerSettingsUserConfig.load_from_db", lambda: SimpleNamespace(short_name="test", broadcast_unbans=False))
    event_us = 1_700_000_000_000_000
    with maker.begin() as session:
        player = PlayerID(player_id="fake-console-id")
        session.add(player)
        session.flush()
        legacy = PlayerSession(player=player, start=datetime.fromtimestamp(event_us / 1_000_000), server_number=3, server_name="test")
        session.add(legacy)
        session.add(PendingPlayerConnect(server_number=3, player_id="fake-console-id", started_event_us=event_us,
                                         started_at=datetime.fromtimestamp(event_us / 1_000_000)))
        session.flush()
        legacy_id = legacy.id
    try:
        yield maker, event_us, legacy_id
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def invoke(name, method, permissions, body=None):
    func = getattr(views.rcon_api, name)
    with (mock.patch.dict(decorators.ENDPOINT_HTTP_METHODS, {}, clear=True),
          mock.patch.dict(decorators.ENDPOINT_PERMISSIONS_LOOKUP, {}, clear=True)):
        endpoint = views.expose_api_endpoint(func=func, command_name=name,
            permissions=views.ENDPOINT_PERMISSIONS[func], endpoint_allowed_http_methods=views.RCON_ENDPOINT_HTTP_METHODS)
    factory = RequestFactory()
    request = (factory.post(f"/api/{name}", data=json.dumps(body or {}), content_type="application/json")
               if method == "POST" else factory.get(f"/api/{name}", data=body or {}))
    request.user = SimpleNamespace(is_authenticated=True, username="Operator",
                                   has_perms=lambda needed: set(needed).issubset(permissions))
    with mock.patch.object(auth, "check_api_key"), mock.patch("api.audit_log.enter_session"):
        return endpoint(request)


def test_session_event_review_requires_permissions_and_records_actor(review_api):
    maker, event_us, legacy_id = review_api
    assert invoke("get_pending_session_events", "GET", set()).status_code == 403
    view = invoke("get_pending_session_events", "GET", {"api.can_view_player_profile"})
    assert view.status_code == 200
    event = json.loads(view.content)["result"]["results"][0]
    assert event["player_id"] == "fake-console-id" and event["legacy_candidates"][0]["id"] == legacy_id
    body = {"player_id": "fake-console-id", "event_kind": "connect", "event_us": str(event_us),
            "decision": "link", "reason": "server logs verified", "session_id": legacy_id}
    assert invoke("resolve_pending_session_event", "POST", {"api.can_view_player_profile"}, body).status_code == 403
    result = invoke("resolve_pending_session_event", "POST", {"api.can_view_player_profile", "api.can_run_raw_commands"}, body)
    assert result.status_code == 200 and json.loads(result.content)["result"] is True
    with maker() as session:
        assert session.get(PlayerSession, legacy_id).start_event_us == event_us
        audit = session.scalar(select(SessionEventResolution))
        assert audit.actor == "Operator" and audit.reason == "server logs verified"
        assert session.scalars(select(PendingPlayerConnect)).all() == []


def test_unidentified_event_review_requires_write_permission(review_api):
    maker, _, _ = review_api
    fingerprint = session_event_review.record_unidentified(3, "disconnect", 1_700_000_000_000_000, "", "DISCONNECTED ()")
    view = invoke("get_pending_session_events", "GET", {"api.can_view_player_profile"})
    assert any(row.get("fingerprint") == fingerprint for row in json.loads(view.content)["result"]["results"])
    body = {"player_id": "", "event_kind": "unidentified", "event_us": "1700000000000000",
            "fingerprint": fingerprint, "decision": "discard", "reason": "verified"}
    assert invoke("resolve_pending_session_event", "POST", {"api.can_view_player_profile"}, body).status_code == 403
    response = invoke("resolve_pending_session_event", "POST", {"api.can_view_player_profile", "api.can_run_raw_commands"}, body)
    assert response.status_code == 200 and json.loads(response.content)["result"] is True
    with maker() as session:
        row = session.get(UnidentifiedSessionEvent, fingerprint)
        assert (row.resolved_by, row.resolution_reason) == ("Operator", "verified")
