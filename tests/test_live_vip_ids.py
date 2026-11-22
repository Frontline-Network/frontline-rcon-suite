import os
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest import mock

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")

import django

django.setup()

from api import auth, decorators, views
from django.test import RequestFactory

from rcon.api_commands import RconAPI
from rcon.commands import ServerCtl
from rcon.models import PlayerVIP
from rcon.rcon import Rcon
from rcon.types import GameEnum


@pytest.fixture
def vip_reader():
    # Skip connection setup; both external read boundaries are replaced below.
    reader = object.__new__(RconAPI)
    reader.config = SimpleNamespace(game=GameEnum.HLL_WW2)
    with (
        mock.patch.object(ServerCtl, "get_vip_ids") as read,
        mock.patch("rcon.rcon.enter_session") as enter_session,
        mock.patch("rcon.rcon.get_server_number", return_value="3"),
    ):
        session = enter_session.return_value.__enter__.return_value
        session.query.return_value.filter.return_value.all.return_value = []
        Rcon.get_vip_ids.cache_clear()
        yield reader, read, session
        Rcon.get_vip_ids.cache_clear()


def test_live_vip_ids_reads_rcon_and_expirations_on_every_call(vip_reader):
    reader, read, session = vip_reader
    expiration = datetime(2026, 10, 1, tzinfo=timezone.utc)
    read.side_effect = [
        [{"player_id": "z", "name": "Zulu"}, {"player_id": "a", "name": "Alpha"}],
        [{"player_id": "new", "name": "New"}],
    ]
    session.query.return_value.filter.return_value.all.side_effect = [
        [
            SimpleNamespace(
                player=SimpleNamespace(player_id="a"), expiration=expiration
            ),
            SimpleNamespace(
                player=SimpleNamespace(player_id="db-only"), expiration=expiration
            ),
        ],
        [
            SimpleNamespace(
                player=SimpleNamespace(player_id="new"), expiration=expiration
            )
        ],
    ]

    assert reader.get_live_vip_ids() == [
        {"player_id": "a", "name": "Alpha", "vip_expiration": expiration},
        {"player_id": "z", "name": "Zulu", "vip_expiration": None},
    ]
    assert reader.get_live_vip_ids() == [
        {"player_id": "new", "name": "New", "vip_expiration": expiration},
    ]
    assert read.call_count == 2
    assert session.query.call_args_list == [mock.call(PlayerVIP), mock.call(PlayerVIP)]
    filters = session.query.return_value.filter.call_args_list
    assert len(filters) == 2
    for call in filters:
        assert call.args[0].compare(PlayerVIP.server_number == "3")


def test_cached_vip_ids_delegates_and_live_read_bypasses_cache(vip_reader):
    reader, read, _session = vip_reader
    read.side_effect = [[{"player_id": "old", "name": "Old"}], []]
    with mock.patch.object(
        reader, "get_live_vip_ids", wraps=reader.get_live_vip_ids
    ) as live:
        cached = reader.get_vip_ids()
        assert reader.get_vip_ids() == cached
        assert live.call_count == 1
        assert read.call_count == 1
        assert reader.get_live_vip_ids() == []
        assert read.call_count == 2
        assert reader.get_vip_ids() == cached
        assert read.call_count == 2


def test_rcon_api_inherits_live_vip_method():
    assert RconAPI.get_live_vip_ids is Rcon.get_live_vip_ids
    assert "get_live_vip_ids" not in RconAPI.__dict__


@pytest.mark.parametrize("name", ["get_vip_ids", "get_live_vip_ids"])
def test_vip_endpoint_registration(name):
    method = getattr(views.rcon_api, name)
    assert views.ENDPOINT_PERMISSIONS[method] == "api.can_view_vip_ids"
    assert views.RCON_ENDPOINT_HTTP_METHODS[method] == ["GET"]


@pytest.mark.parametrize("name,permission,method", [
    ("get_seed_vip_journal", "api.can_view_vip_ids", "GET"),
    ("acknowledge_seed_vip_review", "api.can_add_vip", "POST"),
])
def test_seed_vip_journal_endpoint_registration(name, permission, method):
    endpoint = getattr(views.rcon_api, name)
    assert views.ENDPOINT_PERMISSIONS[endpoint] == permission
    assert views.RCON_ENDPOINT_HTTP_METHODS[endpoint] == [method]


@pytest.mark.parametrize("name,request_method,allowed,expected", [
    ("get_seed_vip_journal", "get", False, 403),
    ("get_seed_vip_journal", "post", True, 405),
    ("acknowledge_seed_vip_review", "post", False, 403),
    ("acknowledge_seed_vip_review", "get", True, 405),
])
def test_seed_vip_journal_enforces_permission_and_method(name, request_method, allowed, expected):
    endpoint = getattr(views.rcon_api, name)
    with (
        mock.patch.dict(decorators.ENDPOINT_HTTP_METHODS, {}, clear=True),
        mock.patch.dict(decorators.ENDPOINT_PERMISSIONS_LOOKUP, {}, clear=True),
    ):
        callback = views.expose_api_endpoint(
            func=endpoint, command_name=name, permissions=views.ENDPOINT_PERMISSIONS[endpoint],
            endpoint_allowed_http_methods=views.RCON_ENDPOINT_HTTP_METHODS,
        )
    if request_method == "post":
        request = RequestFactory().post(f"/api/{name}", data='{"grant_id": 1}', content_type="application/json")
    else:
        request = RequestFactory().get(f"/api/{name}")
    request.user = SimpleNamespace(is_authenticated=True, username="tester", has_perms=lambda _: allowed)
    with mock.patch.object(auth, "check_api_key"), mock.patch("api.audit_log.enter_session"):
        assert callback(request).status_code == expected


@pytest.mark.parametrize(
    "method,allowed,status", [("get", False, 403), ("post", True, 405)]
)
def test_live_vip_endpoint_enforces_permission_and_get(method, allowed, status):
    func = views.rcon_api.get_live_vip_ids
    with (
        mock.patch.dict(decorators.ENDPOINT_HTTP_METHODS, {}, clear=True),
        mock.patch.dict(decorators.ENDPOINT_PERMISSIONS_LOOKUP, {}, clear=True),
    ):
        callback = views.expose_api_endpoint(
            func=func,
            command_name=func.__name__,
            permissions=views.ENDPOINT_PERMISSIONS[func],
            endpoint_allowed_http_methods=views.RCON_ENDPOINT_HTTP_METHODS,
        )
    request = getattr(RequestFactory(), method)("/api/get_live_vip_ids")
    request.user = SimpleNamespace(
        is_authenticated=True,
        username="tester",
        has_perms=lambda permissions: allowed
        and list(permissions) == ["api.can_view_vip_ids"],
    )
    with (
        mock.patch.object(auth, "check_api_key"),
        mock.patch.object(ServerCtl, "get_vip_ids") as read,
    ):
        assert callback(request).status_code == status
        read.assert_not_called()
