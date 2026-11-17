"""Synthetic authenticated websocket and durable outbound scan integration."""
import asyncio
import json
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

import django
import pytest
from asgiref.testing import ApplicationCommunicator
from channels.layers import InMemoryChannelLayer
from sqlalchemy import select

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api import auth, barricade
from rcon import barricade_scan_dispatch as adapter, barricade_scan_journal as journal
from rcon.barricade import ServerRequestType
from tests.test_barricade_scan_journal_postgres import database, prepare_adapter


@pytest.mark.parametrize('acknowledged', [True, False])
def test_durable_scan_via_authenticated_websocket(database, monkeypatch, acknowledged):
    prepare_adapter(database, monkeypatch)
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'

    async def run():
        result = asyncio.Queue()

        class TestConsumer(barricade.BarricadeConsumer):
            async def connect(self):
                await self.accept()
                async def sender(player_id, game):
                    return await self.send_request(ServerRequestType.SCAN_PLAYERS,
                                                   {'player_ids': [player_id], 'game': game})
                async def start():
                    value = await adapter.dispatch(3, self.scope['barricade_scan_namespace'],
                        101, 'synthetic-eos', 'HLLV', sender,
                        credential_id=self.scope['barricade_credential_id'], timeout=0.5)
                    await result.put(value)
                asyncio.create_task(start())

        application = auth.APITokenAuthMiddleware(TestConsumer.as_asgi(), perms=('synthetic',))
        scope = {'type': 'websocket', 'path': '/ws/barricade', 'query_string': b'frontline_integration=synthetic',
                 'headers': [(b'authorization', b'Bearer synthetic-key')], 'subprotocols': []}
        with patch.object(auth, 'get_user', AsyncMock(return_value=(SimpleNamespace(pk=7), None))), \
             patch.object(auth, 'has_perms', AsyncMock(return_value=True)), \
             patch.object(auth, 'get_barricade_api_key_id', AsyncMock(return_value=1)), \
             patch.object(auth, 'get_barricade_scan_namespace', AsyncMock(return_value=namespace)), \
             patch('channels.consumer.get_channel_layer', return_value=InMemoryChannelLayer()):
            socket = ApplicationCommunicator(application, scope)
            await socket.send_input({'type': 'websocket.connect'})
            assert (await socket.receive_output(timeout=5))['type'] == 'websocket.accept'
            request = json.loads((await socket.receive_output(timeout=5))['text'])
            assert request['request'] == 'scan_players'
            assert request['payload'] == {'player_ids': ['synthetic-eos'], 'game': 'HLLV'}
            if acknowledged:
                await socket.send_input({'type': 'websocket.receive', 'text': json.dumps(
                    {'id': request['id'], 'request': None, 'failed': False, 'response': None})})
            assert await asyncio.wait_for(result.get(), 5) == ('done' if acknowledged else 'review')
            await socket.send_input({'type': 'websocket.disconnect', 'code': 1000})
            await socket.wait(timeout=5)
    asyncio.run(run())
    with database() as session:
        assert session.scalar(select(journal.BarricadeScanDelivery.status)) == ('done' if acknowledged else 'review')
