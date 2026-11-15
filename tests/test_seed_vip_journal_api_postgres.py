"""Exercise review access and acknowledgement with an isolated PostgreSQL schema."""
import json
import os
from contextlib import nullcontext
from datetime import datetime, timezone
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
from rcon.models import SeedVipGrant
from rcon.seed_vip import journal


@pytest.fixture
def review_api(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "seed_api_" + uuid4().hex
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    db = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    SeedVipGrant.__table__.create(db)
    maker = sessionmaker(db, expire_on_commit=False)
    monkeypatch.setattr(journal, "get_session_maker", lambda: maker)
    monkeypatch.setattr(journal, "vip_lock", lambda _pid: nullcontext())
    monkeypatch.setattr("rcon.utils.get_server_number", lambda: "3")
    monkeypatch.setattr("rcon.api_commands.get_server_number", lambda: "3")
    now = datetime.now(timezone.utc)
    with maker.begin() as session:
        row = SeedVipGrant(server_number=3, preview=False, generation=1,
                           player_id="fake-console-id", player_name="Fake Player", status="review",
                           reward_seconds=3600, cumulative=True, reward_time=now, target=now,
                           reason="uncertain_write", updated_at=now)
        session.add(row)
        session.flush()
        grant_id = row.id
    try:
        yield maker, grant_id
    finally:
        db.dispose()
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def endpoint(name):
    func = getattr(views.rcon_api, name)
    with (mock.patch.dict(decorators.ENDPOINT_HTTP_METHODS, {}, clear=True),
          mock.patch.dict(decorators.ENDPOINT_PERMISSIONS_LOOKUP, {}, clear=True)):
        return views.expose_api_endpoint(
            func=func, command_name=name, permissions=views.ENDPOINT_PERMISSIONS[func],
            endpoint_allowed_http_methods=views.RCON_ENDPOINT_HTTP_METHODS,
        )


def invoke(name, method, granted, body=None, query=None):
    factory = RequestFactory()
    if method == "POST":
        request = factory.post(f"/api/{name}", data=json.dumps(body or {}), content_type="application/json")
    else:
        request = factory.get(f"/api/{name}", data=query or {})
    request.user = SimpleNamespace(is_authenticated=True, username="Operator",
                                   has_perms=lambda permissions: set(permissions).issubset(granted))
    with mock.patch.object(auth, "check_api_key"), mock.patch("api.audit_log.enter_session"):
        return endpoint(name)(request)


def test_review_requires_permissions_and_does_not_grant_vip(review_api):
    maker, grant_id = review_api
    assert invoke("get_seed_vip_journal", "GET", set()).status_code == 403
    read = invoke("get_seed_vip_journal", "GET", {"api.can_view_vip_ids"}, query={"status": "review"})
    assert read.status_code == 200
    assert json.loads(read.content)["result"]["results"][0]["player_id"] == "fake-console-id"
    assert invoke("acknowledge_seed_vip_review", "POST", set(), {"grant_id": grant_id}).status_code == 403
    with mock.patch("rcon.seed_vip.journal.current_vip") as read_vip:
        reviewed = invoke("acknowledge_seed_vip_review", "POST", {"api.can_add_vip"}, {"grant_id": grant_id})
    assert reviewed.status_code == 200 and json.loads(reviewed.content)["result"] is True
    read_vip.assert_not_called()
    with maker() as session:
        assert session.get(SeedVipGrant, grant_id).status == "reviewed"
    empty = invoke("get_seed_vip_journal", "GET", {"api.can_view_vip_ids"}, query={"status": "review"})
    assert json.loads(empty.content)["result"]["total"] == 0
