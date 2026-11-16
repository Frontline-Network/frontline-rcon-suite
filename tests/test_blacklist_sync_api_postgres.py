"""Review endpoints enforce permissions and never execute game commands."""
import json
import os
from contextlib import nullcontext
from types import SimpleNamespace
from unittest import mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "3")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")
import django
django.setup()

from api import auth, decorators, views
from django.test import RequestFactory
from rcon import blacklist_sync_journal as journal
from rcon.blacklist import BlacklistCommand, BlacklistCommandType


@pytest.fixture
def review_api(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "blacklist_api_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    journal.BlacklistSyncDelivery.__table__.create(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(journal, "get_session_maker", lambda: maker)
    monkeypatch.setattr(journal, "lock", lambda _: nullcontext())
    monkeypatch.setattr("rcon.api_commands.get_server_number", lambda: "3")
    cmd = BlacklistCommand(command=BlacklistCommandType.EXPIRE_ALL, server_mask=4,
                           payload={"player_id": "fake-console-id"})
    with maker() as session, session.begin():
        journal.enqueue(session, cmd.encode(), 4)
    assert journal.process_one(3, lambda _: False) == "review"
    try:
        yield maker
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
            permissions=views.ENDPOINT_PERMISSIONS[func],
            endpoint_allowed_http_methods=views.RCON_ENDPOINT_HTTP_METHODS)
    factory = RequestFactory()
    request = (factory.post(f"/api/{name}", data=json.dumps(body or {}), content_type="application/json")
               if method == "POST" else factory.get(f"/api/{name}"))
    request.user = SimpleNamespace(is_authenticated=True, username="Operator",
                                   has_perms=lambda needed: set(needed).issubset(permissions))
    with mock.patch.object(auth, "check_api_key"), mock.patch("api.audit_log.enter_session"):
        return endpoint(request)


def test_review_permissions_and_no_rcon_side_effect(review_api):
    assert invoke("get_blacklist_sync_reviews", "GET", set()).status_code == 403
    response = invoke("get_blacklist_sync_reviews", "GET", {"api.can_view_blacklists"})
    assert response.status_code == 200
    result = json.loads(response.content)["result"]
    assert result["results"][0]["payload"]["player_id"] == "fake-console-id"
    delivery_id = result["results"][0]["id"]
    assert invoke("acknowledge_blacklist_sync_review", "POST", set(), {"delivery_id": delivery_id}).status_code == 403
    with mock.patch("rcon.blacklist.BlacklistCommandHandler.dispatch") as dispatch:
        response = invoke("acknowledge_blacklist_sync_review", "POST", {"api.can_change_blacklists"}, {"delivery_id": delivery_id})
    assert response.status_code == 200 and json.loads(response.content)["result"] is True
    dispatch.assert_not_called()
    with review_api() as session:
        saved = session.get(journal.BlacklistSyncDelivery, delivery_id)
        assert saved.status == "reviewed"
        assert "Operator" in saved.reason
    result = json.loads(invoke("get_blacklist_sync_reviews", "GET", {"api.can_view_blacklists"}).content)["result"]
    assert result["total"] == 0
