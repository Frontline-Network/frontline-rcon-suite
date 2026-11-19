"""The experimental consumer route is opt-in and needs an authenticated binding."""
import asyncio
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from contextlib import nullcontext

import django
import pytest
from asgiref.testing import ApplicationCommunicator
from channels.layers import InMemoryChannelLayer

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api.barricade import BarricadeConsumer
from api import auth


@pytest.mark.parametrize(('flag', 'namespace', 'credential', 'expected'), [
    ('0', 'integration:synthetic', 1, 'none'),
    ('1', None, 1, 'none'),
    (None, None, 1, 'none'),
    (None, 'integration:synthetic', 1, 'durable'),
    ('1', 'integration:synthetic', None, 'reject'),
    ('1', 'integration:synthetic', 1, 'durable'),
])
def test_consumer_selects_mode_only_for_registered_opt_in(monkeypatch, flag, namespace, credential, expected):
    monkeypatch.setenv('SERVER_NUMBER', '9')
    if flag is None:
        monkeypatch.delenv('HLL_BARRICADE_DURABLE_SCANS', raising=False)
    else:
        monkeypatch.setenv('HLL_BARRICADE_DURABLE_SCANS', flag)
    async def run():
        consumer = BarricadeConsumer()
        consumer.scope = {'barricade_scan_namespace': namespace, 'barricade_credential_id': credential}
        consumer.accept = AsyncMock()
        consumer.close = AsyncMock()
        consumer._durable_scan_loop = AsyncMock()
        with patch('api.barricade.logger.info') as accepted:
            await consumer.connect()
            if expected != 'reject':
                mode = 'registered' if expected == 'durable' else 'off'
                assert accepted.call_args.args[1:] == ('9', credential, mode)
        await asyncio.sleep(0)
        assert consumer.close.await_count == (expected == 'reject')
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


def test_disabled_durable_namespace_keeps_incoming_connection(monkeypatch):
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
        consumer.close.assert_not_awaited()
        consumer.accept.assert_awaited_once()
        consumer._scan_players_loop.assert_not_called()
    asyncio.run(run())


def test_registered_key_with_malformed_query_never_falls_back_to_legacy(monkeypatch):
    monkeypatch.setenv('HLL_BARRICADE_DURABLE_SCANS', '1')
    async def run():
        consumer = BarricadeConsumer()
        consumer.scope = {'query_string': b'other=value', 'barricade_scan_namespace': None,
                          'barricade_registered_namespace': 'integration:synthetic',
                          'barricade_credential_id': 1}
        consumer.accept = AsyncMock()
        consumer.close = AsyncMock()
        consumer._scan_players_loop = AsyncMock()
        await consumer.connect()
        consumer.close.assert_awaited_once_with(code=4403)
        consumer.accept.assert_not_called()
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


@pytest.mark.parametrize('bound', [False, True])
def test_scan_broadcast_is_ignored_but_other_broadcasts_still_work(bound):
    async def run():
        consumer = BarricadeConsumer()
        consumer.scope = {'barricade_scan_namespace': 'integration:synthetic' if bound else None}
        consumer.send_request = AsyncMock()
        await consumer.handle_broadcast({'request_type': 'scan_players', 'payload': {}})
        consumer.send_request.assert_not_awaited()
        await consumer.handle_broadcast({'request_type': 'other_event', 'payload': {'ok': True}})
        consumer.send_request.assert_awaited_once_with('other_event', {'ok': True})
    asyncio.run(run())


def test_unregistered_report_is_acknowledged_without_scan(monkeypatch):
    from rcon.barricade import NewReportRequestPayload
    monkeypatch.setenv('HLL_GAME', 'hllv')
    async def run():
        consumer = BarricadeConsumer()
        consumer.scope = {'barricade_scan_namespace': None, 'barricade_credential_id': 1}
        consumer.send_request = AsyncMock()
        payload = NewReportRequestPayload.model_validate({'game': 'HLLV', 'created_at': '2026-01-01T00:00:00Z',
            'body': '', 'reasons': [], 'attachment_urls': [], 'players': []})
        assert await consumer.new_report(payload) is None
        assert consumer._report_scan_tasks == set()
        consumer.send_request.assert_not_awaited()
    asyncio.run(run())


@pytest.mark.parametrize('server,game', [(3, 'hllv'), (4, 'hllv'), (3, 'hll'), (4, 'hll')])
def test_report_schedules_only_origin_socket_without_blocking_receive(monkeypatch, server, game):
    from rcon import barricade_scan_dispatch as dispatch
    from rcon.barricade import NewReportRequestPayload
    monkeypatch.setenv('SERVER_NUMBER', str(server))
    monkeypatch.setenv('HLL_GAME', game)
    monkeypatch.delenv('HLL_BARRICADE_DURABLE_SCANS', raising=False)
    async def run():
        consumer = BarricadeConsumer()
        consumer.scope = {'barricade_scan_namespace': 'integration:synthetic', 'barricade_credential_id': 1}
        consumer.send_request = AsyncMock()
        started = asyncio.Event()
        release = asyncio.Event()
        async def dispatch_report(server_arg, namespace, credential, player_ids, sender):
            assert (server_arg, namespace, credential, player_ids) == (server, 'integration:synthetic', 1, ['synthetic'])
            started.set()
            await release.wait()
            await sender(player_ids)
        monkeypatch.setattr(dispatch, 'dispatch_report_scan', dispatch_report)
        payload = NewReportRequestPayload.model_validate({'game': game.upper(), 'created_at': '2026-01-01T00:00:00Z',
            'body': '', 'reasons': [], 'attachment_urls': [], 'players': [
                {'player_id': 'synthetic', 'player_name': 'Synthetic', 'bm_rcon_url': None}]})
        await consumer.new_report(payload)
        await asyncio.wait_for(started.wait(), 1)
        consumer.send_request.assert_not_awaited()
        release.set()
        await asyncio.gather(*consumer._report_scan_tasks)
        assert consumer.send_request.await_args.args[1] == {'player_ids': ['synthetic'], 'game': game.upper()}
    asyncio.run(run())
