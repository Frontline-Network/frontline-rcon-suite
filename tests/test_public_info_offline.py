import inspect
import json
import os
from contextlib import nullcontext
from datetime import timedelta
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")

import django
django.setup()
from django.test import RequestFactory
from api import views
from rcon.connection import HLLBrokenConnectionError


@pytest.fixture
def api(monkeypatch):
    fake = MagicMock()
    fake.without_retries.side_effect = nullcontext
    fake.get_gamestate.return_value = {
        "current_map": "map1", "next_map": "map2", "allied_score": 2,
        "axis_score": 1, "num_allied_players": 10, "num_axis_players": 11,
        "time_remaining": timedelta(minutes=30),
    }
    fake.get_slots.return_value = {"current_players": 21, "max_players": 100}
    fake.get_server_config.return_value = {}
    fake.get_votemap_status.return_value = {}
    fake.get_name.return_value = "Test server"
    monkeypatch.setattr(views, "rcon_api", fake)
    monkeypatch.setattr(views, "MapsHistory", lambda: SimpleNamespace(get_current_map=lambda: None))
    monkeypatch.setattr(views.RconServerSettingsUserConfig, "load_from_db",
                        lambda: SimpleNamespace(short_name="Test"))
    return fake


def request():
    return inspect.unwrap(views.get_public_info)(RequestFactory().get("/api/get_public_info"))


@pytest.mark.parametrize("method", ["get_gamestate", "get_slots", "get_server_config",
                                   "get_votemap_status", "get_name"])
@pytest.mark.parametrize("error", [ConnectionRefusedError("secret host"),
                                  TimeoutError("secret host"),
                                  HLLBrokenConnectionError("secret host")])
def test_unavailable_game_server_returns_structured_503_without_secrets(api, method, error):
    getattr(api, method).side_effect = error
    response = request()
    body = json.loads(response.content)
    assert response.status_code == 503
    assert body["failed"] is True and body["result"] is None
    assert body["error"] == "game_server_unavailable"
    assert b"secret host" not in response.content
    api.without_retries.assert_called_once()


def test_endpoint_recovers_when_game_server_returns(api):
    api.get_gamestate.side_effect = [ConnectionRefusedError(), api.get_gamestate.return_value]
    assert request().status_code == 503
    response = request()
    body = json.loads(response.content)
    assert response.status_code == 200 and body["failed"] is False
    assert body["result"]["player_count"] == 21
    assert body["result"]["current_map"]["map"] == "map1"


def test_unexpected_programming_error_is_not_reported_as_offline(api):
    api.get_gamestate.side_effect = ValueError("unexpected")
    with pytest.raises(ValueError, match="unexpected"):
        request()
