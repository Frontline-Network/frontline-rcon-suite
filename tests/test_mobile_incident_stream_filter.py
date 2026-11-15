"""Filtered incremental streams must evict incidents leaving the view."""
import asyncio
import os

import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("RCONWEB_TEST_MODE", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "rconweb.rconweb.test_settings")
import django
django.setup()

from api import mobile_stream


@pytest.mark.parametrize("subscription,expected,removed", [
    ({"cursor": 10, "status": ["new"]}, ["visible"], ["finished", "other-server"]),
    ({"cursor": 10, "status": ["new"], "server_number": [3]}, ["visible"], ["finished"]),
    ({"cursor": 10, "server_number": [3]}, ["visible", "finished"], None),
])
def test_filtered_stream_reports_departures_and_keeps_server_scope(monkeypatch, subscription, expected, removed):
    incidents = [
        {"id": "visible", "status": "new", "server_number": 3},
        {"id": "finished", "status": "resolved", "server_number": 3},
        {"id": "other-server", "status": "resolved", "server_number": 4},
    ]
    async def allowed(*_args): return True
    def as_async(_reader):
        async def read(*_args, **_kwargs): return incidents, 11
        return read
    async def no_wait(_seconds): pass
    monkeypatch.setattr(mobile_stream, "has_perms", allowed)
    monkeypatch.setattr(mobile_stream, "database_sync_to_async", as_async)
    monkeypatch.setattr(mobile_stream.asyncio, "sleep", no_wait)
    consumer = mobile_stream.MobileIncidentStreamConsumer()
    consumer.connected = True
    consumer.scope = {}
    sent = []
    async def capture(payload):
        sent.append(payload)
        consumer.connected = False
    consumer.send_json = capture
    asyncio.run(consumer.receive_json(subscription))
    assert [item["id"] for item in sent[0]["incidents"]] == expected
    assert sent[0]["cursor"] == 11
    assert sent[0].get("removed_incident_ids") == removed


def test_filtered_departure_over_asgi_websocket(monkeypatch):
    from channels.testing import WebsocketCommunicator
    from django.test import override_settings

    async def allowed(*_args): return True
    def as_async(_reader):
        async def read(cursor, **_kwargs):
            if cursor == 10:
                return [{"id": "closed", "status": "resolved", "server_number": 3}], 11
            return [], cursor
        return read
    monkeypatch.setattr(mobile_stream, "mobile_integration_enabled", lambda: True)
    monkeypatch.setattr(mobile_stream, "has_perms", allowed)
    monkeypatch.setattr(mobile_stream, "database_sync_to_async", as_async)

    async def exercise():
        socket = WebsocketCommunicator(mobile_stream.MobileIncidentStreamConsumer.as_asgi(), "/")
        connected, _ = await socket.connect()
        assert connected
        try:
            await socket.send_json_to({"cursor": 10, "status": ["new"], "server_number": 3})
            message = await socket.receive_json_from(timeout=3)
            assert message == {"cursor": 11, "error": None, "incidents": [], "removed_incident_ids": ["closed"]}
        finally:
            socket.future.cancel()
            await asyncio.gather(socket.future, return_exceptions=True)
    with override_settings(CHANNEL_LAYERS={"default": {"BACKEND": "channels.layers.InMemoryChannelLayer"}}):
        asyncio.run(exercise())
