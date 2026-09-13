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
from api import auth, leadership_vote as api
from rcon.leadership_vote import storage
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config
from tests.test_leadership_vote import activate, db, vote


@pytest.fixture
def request_api(monkeypatch, db):
    monkeypatch.setattr(auth, "check_api_key", lambda r: None)
    monkeypatch.setattr(api, "audit", lambda *a, **kw: None)
    monkeypatch.setattr(api, "get_server_number", lambda: 1)

    def call(view, method="GET", data=None, perms=(), authenticated=True, **kwargs):
        req = getattr(RequestFactory(), method.lower())(
            "/api/leadership-vote/v1/config",
            data=json.dumps(data or {}) if method != "GET" else data or {},
            content_type="application/json",
        )
        req.user = SimpleNamespace(
            username="admin",
            is_authenticated=authenticated,
            is_active=True,
            has_perm=lambda p: p in perms,
            has_perms=lambda ps: all(p in perms for p in ps),
        )
        return view(req, **kwargs)

    return call


def test_private_configuration_and_no_browser_ballots(request_api):
    assert request_api(api.status).status_code == 403
    assert (
        request_api(api.status, perms=[api.VIEW], authenticated=False).status_code
        == 401
    )
    assert request_api(api.configuration, perms=[api.VIEW]).status_code == 403
    assert request_api(api.configuration, perms=[api.MANAGE]).status_code == 200
    assert (
        request_api(
            api.status, method="POST", data={"yes": True}, perms=[api.VIEW]
        ).status_code
        == 405
    )


def test_activation_requires_kick_and_valid_mode_bounds(request_api):
    assert (
        request_api(
            api.configuration, "PUT", Config(enabled=True).model_dump(), [api.MANAGE]
        ).status_code
        == 403
    )
    assert (
        request_api(
            api.configuration,
            "PUT",
            Config(enabled=True).model_dump(),
            [api.MANAGE, api.KICK],
        ).status_code
        == 200
    )
    for invalid in (
        {"enabled": "true"},
        {"mode": "automatic"},
        {"minimum_participants": 2},
        {"leadership_seconds": 299},
        {"confirmation_seconds": 0},
        {"duration_seconds": 0},
        {"team_gap_seconds": 0},
        {"numerator": 0},
        {"numerator": 4, "denominator": 3},
        {"denominator": 0},
        {"minimum_yes": 2},
        {"server_number": 2},
        {"numerator": 0.67},
    ):
        assert (
            request_api(
                api.configuration, "PUT", invalid, [api.MANAGE, api.KICK]
            ).status_code
            == 400
        )


def test_cancel_permission_scope_and_disable_cancels(db, request_api):
    vid, _ = activate(db, 3)
    assert (
        request_api(api.cancel, "POST", {}, [api.VIEW], vote_id=vid).status_code == 403
    )
    assert (
        request_api(api.cancel, "POST", {}, [api.CLAIM], vote_id=vid).status_code == 403
    )
    assert (
        request_api(
            api.cancel, "POST", {}, [api.VIEW, api.CLAIM], vote_id="unknown"
        ).status_code
        == 404
    )
    assert (
        request_api(
            api.configuration, "PUT", Config(enabled=False).model_dump(), [api.MANAGE]
        ).status_code
        == 200
    )
    assert vote(db, vid)["status"] == "cancelled"


def test_server_filter_cannot_be_overridden(request_api):
    data = json.loads(
        request_api(api.status, data={"server_number": 999}, perms=[api.VIEW]).content
    )
    assert data["result"]["votes"] == []


def test_config_write_is_csrf_protected_for_sessions(request_api):
    from django.conf import settings
    from rconweb.rconweb.middleware import SessionCsrfProtectionMiddleware

    request = RequestFactory().put(
        "/api/leadership-vote/v1/config", data="{}", content_type="application/json"
    )
    request.COOKIES[settings.SESSION_COOKIE_NAME] = "session"
    middleware = SessionCsrfProtectionMiddleware(lambda r: None)
    assert (
        middleware.process_view(request, api.configuration, (), {}).status_code == 403
    )
