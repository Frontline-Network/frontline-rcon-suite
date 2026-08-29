from __future__ import annotations

import ast
import os
from dataclasses import dataclass, field
from pathlib import Path

import pytest
import requests

os.environ.setdefault("SERVER_NUMBER", "1")

if os.getenv("CRCON_TEST_FAKE_REDIS") == "1":
    import fakeredis
    import redis

    _fake_redis_server = fakeredis.FakeServer()

    class LocalFakeRedis(fakeredis.FakeStrictRedis):
        def __init__(self, *_args, **_kwargs):
            super().__init__(server=_fake_redis_server)

    redis.Redis = LocalFakeRedis
    redis.StrictRedis = LocalFakeRedis

from rconweb.api import forwarding


@dataclass
class FakeResponse:
    status_code: int
    payload: object = None
    invalid_json: bool = False
    headers: dict[str, str] = field(default_factory=dict)
    cookies: dict[str, str] = field(default_factory=dict)

    @property
    def ok(self) -> bool:
        return 200 <= self.status_code < 400

    def json(self):
        if self.invalid_json:
            raise ValueError("invalid JSON")
        return self.payload


class FakeApiKey:
    def __init__(self, keys: dict[str, str], local_key: str = "key-1"):
        self.keys = keys
        self.local_key = local_key

    def get_all_keys(self) -> dict[str, str]:
        return self.keys

    def get_key(self) -> str:
        return self.local_key


def configure_targets(monkeypatch, keys: dict[str, str]) -> None:
    api_key = FakeApiKey(keys)
    monkeypatch.setattr(forwarding, "ApiKey", lambda: api_key)
    monkeypatch.setattr(forwarding, "get_server_number", lambda: "1")


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (None, None),
        (2, (2,)),
        ("3", (3,)),
        ([3, "2", 3], (3, 2)),
        ([], ()),
    ],
)
def test_normalize_forward_server_numbers(value, expected):
    assert forwarding.normalize_forward_server_numbers(value) == expected


@pytest.mark.parametrize(
    "value",
    [True, [False], 0, -1, 2.5, "not-a-number", list(range(1, 52))],
)
def test_normalize_forward_server_numbers_rejects_invalid_values(value):
    with pytest.raises(ValueError):
        forwarding.normalize_forward_server_numbers(value)


def test_forward_command_returns_deterministic_results_for_every_peer(monkeypatch):
    configure_targets(
        monkeypatch,
        {
            "frontend_3": "key-3",
            "frontend_1": "key-1",
            "frontend_2": "key-2",
        },
    )
    calls = []

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return FakeResponse(200, {"failed": False, "result": "ok"})

    monkeypatch.setattr(forwarding.requests, "post", post)

    results = forwarding.forward_command(
        path="/api/kick",
        sessionid="session",
        auth_header="Bearer token",
        json={"forward": True, "player_id": "player"},
    )

    assert [result["server_number"] for result in results] == [2, 3]
    assert [result["status_code"] for result in results] == [200, 200]
    assert all(result["response"]["failed"] is False for result in results)
    assert [call[0] for call in calls] == [
        "http://frontend_2/api/kick",
        "http://frontend_3/api/kick",
    ]
    assert all(
        call[1]["json"] == {"player_id": "player", "forwarded": True} for call in calls
    )


def test_forward_command_targets_only_requested_servers(monkeypatch):
    configure_targets(
        monkeypatch,
        {
            "frontend_1": "key-1",
            "frontend_2": "key-2",
            "frontend_3": "key-3",
        },
    )
    called_urls = []

    def post(url, **_kwargs):
        called_urls.append(url)
        return FakeResponse(200, {"failed": False, "result": "ok"})

    monkeypatch.setattr(forwarding.requests, "post", post)

    results = forwarding.forward_command(
        path="/api/kick",
        sessionid=None,
        auth_header=None,
        json={"forward": True, "forward_server_numbers": [3]},
    )

    assert called_urls == ["http://frontend_3/api/kick"]
    assert [result["server_number"] for result in results] == [3]


def test_forward_command_retries_method_not_allowed_as_get(monkeypatch):
    configure_targets(
        monkeypatch,
        {"frontend_1": "key-1", "frontend_2": "key-2"},
    )
    post_calls = []
    get_calls = []

    def post(url, **kwargs):
        post_calls.append((url, kwargs))
        return FakeResponse(405, {"failed": True})

    def get(url, **kwargs):
        get_calls.append((url, kwargs))
        return FakeResponse(200, {"failed": False, "result": "ok"})

    monkeypatch.setattr(forwarding.requests, "post", post)
    monkeypatch.setattr(forwarding.requests, "get", get)

    results = forwarding.forward_command(
        path="/api/get_status",
        sessionid=None,
        auth_header=None,
        params={"forward": True},
    )

    assert len(post_calls) == 1
    assert len(get_calls) == 1
    assert get_calls[0][1]["params"] == {"forwarded": True}
    assert results[0]["status_code"] == 200
    assert results[0]["response"]["failed"] is False


def test_forward_command_recovers_session_csrf_rejection_once(monkeypatch):
    configure_targets(
        monkeypatch,
        {"frontend_1": "key-1", "frontend_2": "key-2"},
    )
    calls = []
    responses = iter(
        [
            FakeResponse(
                403,
                {"failed": True, "error": "CSRF cookie not set"},
                headers={
                    "X-CRCON-CSRF-Recovery": "1",
                    "X-CRCON-CSRF-Token": "fresh-token",
                },
                cookies={"csrftoken": "fresh-cookie"},
            ),
            FakeResponse(200, {"failed": False, "result": "ok"}),
        ]
    )

    def post(url, **kwargs):
        calls.append((url, kwargs))
        return next(responses)

    monkeypatch.setattr(forwarding.requests, "post", post)

    results = forwarding.forward_command(
        path="/api/add_vip",
        sessionid="browser-session",
        auth_header=None,
        json={"forward": True, "player_id": "player"},
    )

    assert len(calls) == 2
    assert calls[0][1]["cookies"] == {"sessionid": "browser-session"}
    assert calls[1][1]["cookies"] == {
        "sessionid": "browser-session",
        "csrftoken": "fresh-cookie",
    }
    assert calls[1][1]["headers"]["X-CSRFToken"] == "fresh-token"
    assert results[0]["status_code"] == 200
    assert results[0]["response"]["failed"] is False


@pytest.mark.parametrize(
    "payload",
    [
        {"forwarded": True},
        {"forward": True, "forward_server_numbers": []},
        {"forward": True, "forward_server_numbers": [1]},
    ],
)
def test_forward_command_skips_discovery_when_no_remote_target_is_needed(
    monkeypatch, payload
):
    monkeypatch.setattr(forwarding, "get_server_number", lambda: "1")
    monkeypatch.setattr(
        forwarding,
        "ApiKey",
        lambda: pytest.fail("API key discovery must not run"),
    )

    assert (
        forwarding.forward_command(
            path="/api/kick",
            sessionid=None,
            auth_header=None,
            json=payload,
        )
        == []
    )


@pytest.mark.parametrize(
    ("response", "expected_error"),
    [
        (
            FakeResponse(503, {"failed": True, "error": "peer unavailable"}),
            "peer unavailable",
        ),
        (
            FakeResponse(500, {"error": {"private": "detail"}}),
            "CRCON peer returned HTTP 500",
        ),
        (
            FakeResponse(200, invalid_json=True),
            "The CRCON peer returned an invalid response",
        ),
    ],
)
def test_forward_command_retains_sanitized_http_failures(
    monkeypatch, response, expected_error
):
    configure_targets(
        monkeypatch,
        {"frontend_1": "key-1", "frontend_2": "key-2"},
    )
    monkeypatch.setattr(forwarding.requests, "post", lambda *_args, **_kwargs: response)

    results = forwarding.forward_command(
        path="/api/kick",
        sessionid=None,
        auth_header=None,
        json={"forward": True},
    )

    assert results == [
        {
            "host": "frontend_2",
            "server_number": 2,
            "status_code": response.status_code,
            "response": {
                "result": None,
                "failed": True,
                "error": expected_error,
                "forward_results": None,
            },
        }
    ]


def test_forward_command_retains_connection_failures(monkeypatch):
    configure_targets(
        monkeypatch,
        {"frontend_1": "key-1", "frontend_2": "key-2"},
    )

    def post(*_args, **_kwargs):
        raise requests.ConnectionError("secret transport detail")

    monkeypatch.setattr(forwarding.requests, "post", post)

    results = forwarding.forward_command(
        path="/api/kick",
        sessionid=None,
        auth_header=None,
        json={"forward": True},
    )

    assert results[0]["server_number"] == 2
    assert results[0]["status_code"] is None
    assert results[0]["response"]["failed"] is True
    assert results[0]["response"]["error"] == "The target CRCON server did not respond"
    assert "secret" not in results[0]["response"]["error"]


def test_forward_command_reports_requested_unregistered_server(monkeypatch):
    configure_targets(
        monkeypatch,
        {"frontend_1": "key-1", "frontend_2": "key-2"},
    )
    monkeypatch.setattr(
        forwarding.requests,
        "post",
        lambda *_args, **_kwargs: FakeResponse(200, {"failed": False, "result": "ok"}),
    )

    results = forwarding.forward_command(
        path="/api/kick",
        sessionid=None,
        auth_header=None,
        json={"forward": True, "forward_server_numbers": [1, 2, 4]},
    )

    assert [result["server_number"] for result in results] == [2, 4]
    assert results[1]["host"] is None
    assert results[1]["response"]["failed"] is True
    assert (
        results[1]["response"]["error"] == "The target CRCON server is not registered"
    )


def test_forwarding_unavailable_results_preserve_requested_targets(monkeypatch):
    monkeypatch.setattr(forwarding, "get_server_number", lambda: "1")

    results = forwarding.forwarding_unavailable_results([1, 3, 2])

    assert [result["server_number"] for result in results] == [3, 2]
    assert all(result["response"]["failed"] is True for result in results)
    assert all(
        result["response"]["error"] == "CRCON multi-server forwarding is unavailable"
        for result in results
    )


def test_api_wrapper_validates_and_forwards_before_serializing_response():
    source = Path("rconweb/api/views.py").read_text(encoding="utf-8")
    tree = ast.parse(source)
    wrapper = next(
        node
        for node in ast.walk(tree)
        if isinstance(node, ast.FunctionDef) and node.name == "wrapper"
    )

    calls = [node for node in ast.walk(wrapper) if isinstance(node, ast.Call)]
    normalize_call = next(
        call
        for call in calls
        if isinstance(call.func, ast.Name)
        and call.func.id == "normalize_forward_server_numbers"
    )
    local_action_call = next(
        call
        for call in calls
        if isinstance(call.func, ast.Name) and call.func.id == "func"
    )
    response_call = next(
        call
        for call in calls
        if isinstance(call.func, ast.Name)
        and call.func.id == "RconJsonResponse"
        and call.lineno > local_action_call.lineno
    )
    forward_assignments = [
        node
        for node in ast.walk(wrapper)
        if isinstance(node, ast.Assign)
        and isinstance(node.value, ast.Call)
        and isinstance(node.value.func, ast.Name)
        and node.value.func.id == "forward_command"
    ]

    assert normalize_call.lineno < local_action_call.lineno
    assert len(forward_assignments) == 2
    assert all(
        assignment.lineno < response_call.lineno for assignment in forward_assignments
    )
    assert all(
        any(
            isinstance(target, ast.Name) and target.id == "others"
            for target in assignment.targets
        )
        for assignment in forward_assignments
    )
    response_dict = response_call.args[0]
    assert isinstance(response_dict, ast.Call)
    assert isinstance(response_dict.func, ast.Name)
    assert response_dict.func.id == "dict"
    assert any(
        keyword.arg == "forward_results"
        and isinstance(keyword.value, ast.Name)
        and keyword.value.id == "others"
        for keyword in response_dict.keywords
    )
