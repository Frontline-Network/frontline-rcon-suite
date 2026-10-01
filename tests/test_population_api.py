import json
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")

import django

django.setup()
from django.test import RequestFactory

from api import auth
from api import population as api
from tests.test_population_history import NOW, database, record


@pytest.fixture
def call(monkeypatch, database):
    monkeypatch.setattr(auth, "check_api_key", lambda r: None)
    monkeypatch.setattr(api, "get_server_number", lambda: 1)

    def invoke(
        view=api.get_player_count_history,
        method="GET",
        data=None,
        perms=(api.VIEW,),
        authenticated=True,
        active=True,
    ):
        request = getattr(RequestFactory(), method.lower())(
            "/api/test",
            data=data or {"from": NOW, "to": NOW + 60},
            content_type="application/json",
        )
        request.user = SimpleNamespace(
            username="analyst",
            is_authenticated=authenticated,
            is_active=active,
            has_perm=lambda p: p in perms,
            has_perms=lambda ps: all(p in perms for p in ps),
        )
        return view(request)

    return invoke


def test_read_permission_inactive_and_methods(call):
    assert call(authenticated=False).status_code == 401
    assert call(perms=()).status_code == 403
    assert call(active=False).status_code == 403
    assert call(method="POST").status_code == 405
    assert call().status_code == 200
    assert call()["Cache-Control"] == "private, no-store"
    assert call(api.mark_seeding_session, "POST").status_code == 403


def test_server_filter_requires_existing_cross_server_permission(call):
    record(80, server=2)
    query = {"from": NOW, "to": NOW + 60, "server": 2}
    assert call(data=query).status_code == 403
    response = call(data=query, perms=[api.VIEW, api.CROSS_SERVER])
    assert response.status_code == 200
    assert json.loads(response.content)["result"]["points"][0]["mean"] == 80


def test_invalid_queries_and_storage_failure(call, monkeypatch):
    for query in [
        {"from": "nan", "to": NOW},
        {"from": NOW},
        {"from": NOW, "to": NOW + 60, "limit": "all"},
    ]:
        assert call(data=query).status_code == 400
    from sqlalchemy.exc import OperationalError

    def fail(*args):
        raise OperationalError("private SQL", {}, Exception("private DB details"))

    monkeypatch.setattr(api.population, "history", fail)
    response = call()
    assert response.status_code == 503
    assert b"private" not in response.content


def test_manual_marker_write_permission_and_input_validation(call):
    from uuid import uuid4

    data = {"action": "start", "session_id": str(uuid4()), "seeder_count": 4}
    response = call(api.mark_seeding_session, "POST", data, [api.MANAGE])
    assert response.status_code == 200
    assert call(api.get_seeding_sessions).status_code == 200
    for invalid in [
        dict(data, server=2),
        dict(data, seeder_count=True),
        dict(data, session_id="bad"),
    ]:
        assert (
            call(api.mark_seeding_session, "POST", invalid, [api.MANAGE]).status_code
            == 400
        )
