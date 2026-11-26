"""JSON expiration values must be parsed before changing bans or queueing commands."""
from datetime import datetime, timedelta, timezone
from unittest.mock import Mock

import pytest

from rcon import blacklist


@pytest.mark.parametrize("value", [
    "2026-11-26T21:54:30.123Z",
    "2026-11-26T22:54:30.123+01:00",
    "2026-11-26T16:54:30.123-05:00",
    "2026-11-26T21:54:30.123",
    "2026-11-26 21:54:30.123+00:00",
    datetime(2026, 11, 26, 21, 54, 30, 123000),
    datetime(2026, 11, 26, 22, 54, 30, 123000, tzinfo=timezone(timedelta(hours=1))),
])
def test_expiration_preserves_the_requested_instant(value):
    assert blacklist.normalize_blacklist_expiry(value) == datetime(
        2026, 11, 26, 21, 54, 30, 123000, tzinfo=timezone.utc,
    )


def test_null_expiration_remains_permanent():
    assert blacklist.normalize_blacklist_expiry(None) is None


@pytest.mark.parametrize("value", [
    "", "tomorrow", "2026-11-26", "2026-02-30T12:00:00Z",
    "2026-11-26T25:00:00Z", "2026-11-26T12:00:00+99:00",
    "9999-12-31T23:59:59-01:00", 0, True, [], {},
])
@pytest.mark.parametrize("operation", ["create", "edit"])
def test_invalid_expiration_does_not_open_a_mutation_transaction(monkeypatch, value, operation):
    mutation = Mock(side_effect=AssertionError("must not change any records"))
    monkeypatch.setattr(blacklist, "blacklist_change_session", mutation)
    with pytest.raises(blacklist.InvalidBlacklistExpiration, match="Invalid blacklist expiration date"):
        if operation == "create":
            blacklist.add_record_to_blacklist("synthetic-player", 1, "test", expires_at=value)
        else:
            blacklist.edit_record_from_blacklist(1, blacklist_id=2, reason="changed", expires_at=value)
    mutation.assert_not_called()


@pytest.mark.parametrize("endpoint, body", [
    ("add_blacklist_record", {"player_id": "synthetic-player", "blacklist_id": 1, "reason": "test"}),
    ("edit_blacklist_record", {"record_id": 1}),
])
def test_invalid_json_expiration_returns_a_client_error(monkeypatch, endpoint, body):
    import json
    from tests.test_blacklist_sync_api_postgres import invoke

    mutation = Mock(side_effect=AssertionError("must not change any records"))
    monkeypatch.setattr(blacklist, "blacklist_change_session", mutation)
    response = invoke(endpoint, "POST", {"api.can_add_blacklist_records", "api.can_change_blacklist_records"},
                      {**body, "expires_at": "not-a-date"})
    assert response.status_code == 400
    payload = json.loads(response.content)
    assert payload["failed"] is True
    assert payload["error"] == "Invalid blacklist expiration date"
    assert payload["arguments"] == {**body, "expires_at": "not-a-date"}
    mutation.assert_not_called()
