from types import SimpleNamespace

from rconweb.api.ratelimits import (
    login_account_rate_limit_key,
    request_rate_limit_key,
)


def _request(
    *,
    remote_addr="172.20.0.4",
    forwarded_for="",
    session_key=None,
    body=b"{}",
):
    return SimpleNamespace(
        body=body,
        user=SimpleNamespace(is_authenticated=False),
        session=SimpleNamespace(session_key=session_key),
        COOKIES={},
        META={
            "REMOTE_ADDR": remote_addr,
            "HTTP_X_FORWARDED_FOR": forwarded_for,
        },
    )


def test_sessions_behind_the_same_proxy_have_separate_rate_limit_buckets():
    first = _request(session_key="first", forwarded_for="203.0.113.10")
    second = _request(session_key="second", forwarded_for="203.0.113.10")

    assert request_rate_limit_key("test", first) != request_rate_limit_key(
        "test", second
    )


def test_proxy_depth_selects_the_configured_trusted_hop(monkeypatch):
    request = _request(forwarded_for="198.51.100.7, 10.0.0.2")

    monkeypatch.setenv("RATELIMIT_PROXY_DEPTH", "2")

    assert request_rate_limit_key("test", request) == "client:198.51.100.7"


def test_forwarded_header_is_ignored_from_public_peer():
    request = _request(
        remote_addr="8.8.8.8",
        forwarded_for="198.51.100.7",
    )

    assert request_rate_limit_key("test", request) == "client:8.8.8.8"


def test_login_account_bucket_is_normalized_and_does_not_expose_username():
    first = _request(body=b'{"username": " Biene "}')
    second = _request(body=b'{"username": "biene"}')

    first_key = login_account_rate_limit_key("login", first)

    assert first_key == login_account_rate_limit_key("login", second)
    assert "biene" not in first_key
