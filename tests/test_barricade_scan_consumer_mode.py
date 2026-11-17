"""The experimental consumer route is opt-in and needs an authenticated binding."""
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import django
import pytest
from asgiref.testing import ApplicationCommunicator
from channels.layers import InMemoryChannelLayer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api.barricade import BarricadeConsumer
from api import auth


@pytest.mark.parametrize(('flag', 'namespace', 'credential', 'expected'), [
    ('0', 'integration:synthetic', 1, 'legacy'),
    ('1', None, 1, 'legacy'),
    ('1', 'integration:synthetic', None, 'legacy'),
    ('1', 'integration:synthetic', 1, 'durable'),
])
def test_consumer_selects_mode_only_for_registered_opt_in(monkeypatch, flag, namespace, credential, expected):
    monkeypatch.setenv('HLL_BARRICADE_DURABLE_SCANS', flag)
    async def run():
        consumer = BarricadeConsumer()
        consumer.scope = {'barricade_scan_namespace': namespace, 'barricade_credential_id': credential}
        consumer.accept = AsyncMock()
        consumer._scan_players_loop = AsyncMock()
        consumer._durable_scan_loop = AsyncMock()
        await consumer.connect()
        await asyncio.sleep(0)
        assert consumer._scan_players_loop.await_count == (expected == 'legacy')
        assert consumer._durable_scan_loop.await_count == (expected == 'durable')
        await consumer.disconnect(1000)
    asyncio.run(run())


def test_durable_failure_never_falls_back_to_legacy_scanner(monkeypatch):
    async def run():
        consumer = BarricadeConsumer()
        consumer._durable_scan_once = AsyncMock(side_effect=OSError('synthetic outage'))
        consumer._scan_players_loop = AsyncMock()
        calls = 0
        async def sleep(_seconds):
            nonlocal calls
            calls += 1
            if calls > 1:
                raise asyncio.CancelledError
        monkeypatch.setattr('api.barricade.asyncio.sleep', sleep)
        with pytest.raises(asyncio.CancelledError):
            await consumer._durable_scan_loop()
        consumer._durable_scan_once.assert_awaited_once()
        consumer._scan_players_loop.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize('query', [b'frontline_integration=bad', b'frontline%5Fintegration=',
                                  b'x=1&frontline_integration=one&frontline_integration=two',
                                  b'\xff', b'x=' + b'a' * 2049])
def test_requested_unregistered_integration_is_rejected_instead_of_legacy(monkeypatch, query):
    monkeypatch.setenv('HLL_BARRICADE_DURABLE_SCANS', '1')
    async def run():
        consumer = BarricadeConsumer()
        consumer.scope = {'query_string': query, 'barricade_scan_namespace': None,
                          'barricade_credential_id': 1}
        consumer.accept = AsyncMock()
        consumer.close = AsyncMock()
        consumer._scan_players_loop = AsyncMock()
        consumer._durable_scan_loop = AsyncMock()
        await consumer.connect()
        consumer.close.assert_awaited_once_with(code=4403)
        consumer.accept.assert_not_awaited()
        consumer._scan_players_loop.assert_not_called()
        consumer._durable_scan_loop.assert_not_called()
    asyncio.run(run())


def test_disabled_durable_namespace_does_not_fall_back_to_legacy(monkeypatch):
    monkeypatch.setenv('HLL_BARRICADE_DURABLE_SCANS', '0')
    async def run():
        consumer = BarricadeConsumer()
        consumer.scope = {'query_string': b'frontline_integration=synthetic',
                          'barricade_scan_namespace': 'integration:synthetic',
                          'barricade_credential_id': 1}
        consumer.accept = AsyncMock()
        consumer.close = AsyncMock()
        consumer._scan_players_loop = AsyncMock()
        await consumer.connect()
        consumer.close.assert_awaited_once_with(code=4403)
        consumer.accept.assert_not_awaited()
        consumer._scan_players_loop.assert_not_called()
    asyncio.run(run())


def test_authenticated_websocket_rejects_unregistered_requested_integration(monkeypatch):
    monkeypatch.setenv('HLL_BARRICADE_DURABLE_SCANS', '1')
    async def run():
        app = auth.APITokenAuthMiddleware(BarricadeConsumer.as_asgi(), perms=('synthetic',))
        scope = {'type': 'websocket', 'path': '/ws/barricade', 'subprotocols': [],
                 'query_string': b'frontline_integration=unregistered',
                 'headers': [(b'authorization', b'Bearer synthetic')]}
        with patch.object(auth, 'get_user', AsyncMock(return_value=(SimpleNamespace(pk=7), None))), \
             patch.object(auth, 'has_perms', AsyncMock(return_value=True)), \
             patch.object(auth, 'get_barricade_api_key_id', AsyncMock(return_value=1)), \
             patch.object(auth, 'get_barricade_scan_namespace', AsyncMock(return_value=None)), \
             patch('channels.consumer.get_channel_layer', return_value=InMemoryChannelLayer()):
            socket = ApplicationCommunicator(app, scope)
            await socket.send_input({'type': 'websocket.connect'})
            output = await socket.receive_output(timeout=5)
            assert output['type'] == 'websocket.close' and output['code'] == 4403
            await socket.send_input({'type': 'websocket.disconnect', 'code': 4403})
            await socket.wait(timeout=5)
    asyncio.run(run())
