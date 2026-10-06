import json
import os
from types import SimpleNamespace

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")

import django

django.setup()
from django.test import RequestFactory
from api import auth, report_admin as api, leadership_vote
from tests.test_report_admin import setup, db, report, current


@pytest.fixture
def call(setup, monkeypatch):
    monkeypatch.setattr(auth, "check_api_key", lambda r: None)
    monkeypatch.setattr(api, "audit", lambda *a, **kw: None)
    monkeypatch.setattr(leadership_vote, "get_server_number", lambda: 1)

    def invoke(method="GET", data=None, perms=(), authenticated=True):
        request = getattr(RequestFactory(), method.lower())(
            "/api/report-admin/v1/config",
            data=json.dumps(data or {}) if method != "GET" else {},
            content_type="application/json",
        )
        request.user = SimpleNamespace(
            username="admin",
            is_authenticated=authenticated,
            is_active=True,
            has_perm=lambda p: p in perms,
            has_perms=lambda ps: all(p in perms for p in ps),
        )
        return api.configuration(request)

    return invoke


def test_permissions_and_boundaries(call):
    assert call().status_code == 403
    assert call(perms=[api.MANAGE], authenticated=False).status_code == 401
    assert call(perms=[api.MANAGE]).status_code == 200
    assert call("POST", perms=[api.MANAGE]).status_code == 405
    assert call("PUT", {"enabled": True}, [api.MANAGE]).status_code == 403
    assert call("PUT", {"enabled": True}, [api.MANAGE, api.KICK]).status_code == 200


@pytest.mark.parametrize(
    "payload",
    [
        {"server_number": 2},
        {"mode": "ban"},
        {"enabled": "yes"},
        {"teamkill_count": 1},
        {"communication_template_id": 99999},
    ],
)
def test_invalid_config(call, payload):
    assert call("PUT", payload, [api.MANAGE, api.KICK]).status_code == 400


def test_disable_cancels_pending(call, setup):
    i = report(setup)
    assert call("PUT", {"enabled": False}, [api.MANAGE]).status_code == 200
    assert current(setup[0], i["id"])["report_admin"]["status"] == "manual"


def test_csrf_protection(call):
    from django.conf import settings
    from importlib import import_module

    SessionCsrfProtectionMiddleware = import_module(
        settings.SETTINGS_MODULE.rsplit(".", 1)[0] + ".middleware"
    ).SessionCsrfProtectionMiddleware
    request = RequestFactory().put(
        "/api/report-admin/v1/config", data="{}", content_type="application/json"
    )
    request.COOKIES[settings.SESSION_COOKIE_NAME] = "session"
    middleware = SessionCsrfProtectionMiddleware(lambda r: None)
    from django.test import override_settings

    failure_view = settings.SETTINGS_MODULE.rsplit(".", 1)[0] + ".csrf.csrf_failure"
    with override_settings(CSRF_FAILURE_VIEW=failure_view):
        assert (
            middleware.process_view(request, api.configuration, (), {}).status_code
            == 403
        )
