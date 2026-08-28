import os
from unittest.mock import patch

import fakeredis

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon import audit


def _client() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis()


def test_heartbeat_registers_key_and_preserves_success_result(monkeypatch):
    client = _client()
    monkeypatch.setattr(audit, "_red", lambda: client)

    assert audit.heartbeat("Moderator", "76561198000000000", timeout=120) is True

    heartbeat_key = audit._heartbeat_key("Moderator")
    assert 0 < client.ttl(heartbeat_key) <= 120
    assert client.smembers(audit.HEARTBEAT_REGISTRY_KEY) == {heartbeat_key.encode()}
    assert audit.online_mods() == [
        {"username": "Moderator", "player_id": "76561198000000000"}
    ]


def test_online_mods_imports_legacy_heartbeats_only_once(monkeypatch):
    client = _client()
    monkeypatch.setattr(audit, "_red", lambda: client)
    client.setex(
        audit._heartbeat_key("Legacy"),
        120,
        '{"username": "Legacy", "player_id": "42"}',
    )

    with patch.object(client, "scan_iter", wraps=client.scan_iter) as scan_iter:
        assert audit.online_mods() == [{"username": "Legacy", "player_id": "42"}]
        assert audit.online_mods() == [{"username": "Legacy", "player_id": "42"}]

    scan_iter.assert_called_once_with(match="heartbeat_*", count=500)
    assert client.smembers(audit.HEARTBEAT_REGISTRY_KEY) == {
        audit.HEARTBEAT_REGISTRY_SENTINEL.encode(),
        audit._heartbeat_key("Legacy").encode(),
    }


def test_online_mods_prunes_expired_registry_members_without_scanning(monkeypatch):
    client = _client()
    monkeypatch.setattr(audit, "_red", lambda: client)
    active_key = audit._heartbeat_key("Active")
    expired_key = audit._heartbeat_key("Expired")
    client.setex(
        active_key,
        120,
        '{"username": "Active", "player_id": "84"}',
    )
    client.sadd(
        audit.HEARTBEAT_REGISTRY_KEY,
        audit.HEARTBEAT_REGISTRY_SENTINEL,
        active_key,
        expired_key,
    )

    with patch.object(client, "scan_iter", wraps=client.scan_iter) as scan_iter:
        assert audit.online_mods() == [{"username": "Active", "player_id": "84"}]

    scan_iter.assert_not_called()
    assert client.smembers(audit.HEARTBEAT_REGISTRY_KEY) == {
        audit.HEARTBEAT_REGISTRY_SENTINEL.encode(),
        active_key.encode(),
    }


def test_online_mods_initializes_empty_registry_once(monkeypatch):
    client = _client()
    monkeypatch.setattr(audit, "_red", lambda: client)

    with patch.object(client, "scan_iter", wraps=client.scan_iter) as scan_iter:
        assert audit.online_mods() == []
        assert audit.online_mods() == []

    scan_iter.assert_called_once_with(match="heartbeat_*", count=500)
    assert client.smembers(audit.HEARTBEAT_REGISTRY_KEY) == {
        audit.HEARTBEAT_REGISTRY_SENTINEL.encode()
    }
