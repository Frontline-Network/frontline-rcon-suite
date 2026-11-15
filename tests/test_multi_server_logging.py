import json
import logging
import os
from types import SimpleNamespace

import pytest
import requests

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")

import django
django.setup()
from django.test import RequestFactory
from api import multi_servers


@pytest.mark.parametrize("fails", [False, True])
def test_peer_forwarding_does_not_log_request_response_or_exception(monkeypatch, caplog, fails):
    secret = "fake-forward-secret"
    keys = SimpleNamespace(get_all_keys=lambda: {"peer": "other"}, get_key=lambda: "local")
    monkeypatch.setattr(multi_servers, "ApiKey", lambda: keys)
    sent = []

    def post(url, **kwargs):
        sent.append(kwargs)
        if fails:
            raise requests.exceptions.RequestException(secret)
        return SimpleNamespace(ok=True, status_code=200, json=lambda: {"result": secret})

    monkeypatch.setattr(multi_servers.requests, "post", post)
    request = RequestFactory().post(
        "/api/example?secret=" + secret,
        data=json.dumps({"password": secret, "forward": True}),
        content_type="application/json",
        HTTP_AUTHORIZATION=secret,
    )
    request.COOKIES["sessionid"] = secret
    with caplog.at_level(logging.DEBUG, logger=multi_servers.logger.name):
        result = multi_servers.forward_request(request)

    assert sent[0]["json"]["password"] == secret
    assert sent[0]["params"]["secret"] == [secret]
    assert secret not in caplog.text
    assert result == ([] if fails else [{"host": "peer", "response": {"result": secret}}])
