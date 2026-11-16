import json
import logging
import os
from types import SimpleNamespace
from unittest.mock import patch

import pytest
from pydantic import BaseModel

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")

import django
django.setup()
from django.test import RequestFactory
from api import auth, decorators, views


class Payload(BaseModel):
    count: int


def validate_example(by, config=None, **kwargs):
    Payload.model_validate(config)
    return True


def call(payload):
    request = RequestFactory().post("/api/validate_example", data=json.dumps(payload), content_type="application/json")
    request.user = SimpleNamespace(username="tester", is_authenticated=True, is_active=True, has_perms=lambda _: True)
    with patch.object(auth, "check_api_key"), \
         patch.object(views.RconServerSettingsUserConfig, "load_from_db", return_value=SimpleNamespace(broadcast_unbans=False)), \
         patch.object(views.rcon_latency_tracker, "record"), \
         patch.dict(decorators.ENDPOINT_HTTP_METHODS, {}, clear=True), \
         patch.dict(decorators.ENDPOINT_PERMISSIONS_LOOKUP, {}, clear=True):
        endpoint = views.expose_api_endpoint(validate_example, "validate_example", "api.can_change_auto_broadcast_config", {validate_example: ["POST"]})
        response = endpoint(request)
    return response.status_code, json.loads(response.content)


@pytest.mark.parametrize("payload", [[], None, 1, "text"])
def test_non_object_request_is_a_consistent_400(payload):
    status, body = call(payload)
    assert status == 400
    assert body["failed"] is True
    assert body["error"] == "Expected a JSON object"


def test_validation_error_is_a_consistent_400():
    status, body = call({"config": {"count": "not-a-number"}})
    assert status == 400
    assert body["failed"] is True
    assert body["error"]


def test_forwarding_exception_does_not_log_sensitive_details(caplog):
    secret = "https://example.invalid/path?secret=fake-token"
    with patch.object(views, "forward_command", side_effect=RuntimeError(secret)):
        status, body = call({"config": {"count": 1}, "forward": True})
    assert status == 200
    assert body["forward_results"]
    assert "Unexpected forwarding error" in caplog.text
    assert secret not in caplog.text


def test_debug_logging_never_records_arbitrary_api_arguments(caplog):
    secret = "fake-password-or-webhook-token"
    with caplog.at_level(logging.DEBUG, logger=views.logger.name):
        status, _ = call({"config": {"count": 1}, "secret": secret})
    assert status == 200
    assert "API command validate_example" in caplog.text
    assert secret not in caplog.text
