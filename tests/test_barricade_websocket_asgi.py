import asyncio
import json
import os
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import AsyncMock, patch

import django
from asgiref.testing import ApplicationCommunicator
from channels.layers import InMemoryChannelLayer
from sqlalchemy import select

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api import auth, barricade
from rcon.blacklist_sync_journal import BlacklistSyncDelivery
from rcon.models import BlacklistRecord
from tests.test_blacklist_sync_journal_postgres import database, existing_blacklist


def test_authorized_websocket_returns_partial_unban_failure():
    async def run():
        app = auth.APITokenAuthMiddleware(barricade.BarricadeConsumer.as_asgi(), perms=('synthetic',))
        scope = {'type': 'websocket', 'path': '/ws/barricade',
                 'headers': [(b'authorization', b'Bearer synthetic-test-key')],
                 'query_string': b'', 'subprotocols': []}
        channel_layer = InMemoryChannelLayer()
        with patch.object(auth, 'get_user', AsyncMock(return_value=(object(), None))), \
             patch.object(auth, 'has_perms', AsyncMock(return_value=True)), \
             patch('channels.consumer.get_channel_layer', return_value=channel_layer), \
             patch.object(barricade, 'get_most_recent_session_date', AsyncMock(return_value=datetime.utcnow())), \
             patch.object(barricade, 'assert_blacklist_exists', AsyncMock()), \
             patch.object(barricade, 'unban_player', AsyncMock(side_effect=[True, False])) as unban:
            socket = ApplicationCommunicator(app, scope)
            await socket.send_input({'type': 'websocket.connect'})
            assert (await socket.receive_output(timeout=5))['type'] == 'websocket.accept'
            request = {'id': 7, 'request': 'unban_players',
                       'payload': {'ban_ids': ['11', '22'], 'config': {'banlist_id': '2'}}}
            await socket.send_input({'type': 'websocket.receive', 'text': json.dumps(request)})
            output = await socket.receive_output(timeout=5)
            response = json.loads(output['text'])
            assert response['id'] == 7 and response['failed'] is True
            assert response['response']['ban_ids'] == ['11']
            assert [call.args for call in unban.await_args_list] == [(11, 2), (22, 2)]
            await socket.send_input({'type': 'websocket.disconnect', 'code': 1000})
            await socket.wait(timeout=5)
    asyncio.run(run())


def test_websocket_unban_checks_real_postgres_list_and_queues_deletion(database, existing_blacklist, monkeypatch):
    record_id, first, second = existing_blacklist

    @contextmanager
    def session_scope():
        with database() as session:
            yield session

    monkeypatch.setattr(barricade.models, 'enter_session', session_scope)

    async def run():
        app = auth.APITokenAuthMiddleware(barricade.BarricadeConsumer.as_asgi(), perms=('synthetic',))
        scope = {'type': 'websocket', 'path': '/ws/barricade',
                 'headers': [(b'authorization', b'Bearer synthetic-test-key')],
                 'query_string': b'', 'subprotocols': []}
        with patch.object(auth, 'get_user', AsyncMock(return_value=(object(), None))), \
             patch.object(auth, 'has_perms', AsyncMock(return_value=True)), \
             patch('channels.consumer.get_channel_layer', return_value=InMemoryChannelLayer()), \
             patch.object(barricade, 'get_most_recent_session_date', AsyncMock(return_value=datetime.utcnow())):
            socket = ApplicationCommunicator(app, scope)
            await socket.send_input({'type': 'websocket.connect'})
            assert (await socket.receive_output(timeout=5))['type'] == 'websocket.accept'
            for request_id, list_id, failed in ((8, second, True), (9, first, False)):
                request = {'id': request_id, 'request': 'unban_players',
                           'payload': {'ban_ids': [str(record_id)], 'config': {'banlist_id': str(list_id)}}}
                await socket.send_input({'type': 'websocket.receive', 'text': json.dumps(request)})
                response = json.loads((await socket.receive_output(timeout=10))['text'])
                assert response['id'] == request_id and response['failed'] is failed
                assert response['response']['ban_ids'] == ([] if failed else [str(record_id)])
            await socket.send_input({'type': 'websocket.disconnect', 'code': 1000})
            await socket.wait(timeout=5)
    asyncio.run(run())
    with database() as session:
        assert session.get(BlacklistRecord, record_id) is None
        deliveries = session.scalars(select(BlacklistSyncDelivery)).all()
        assert len(deliveries) == 1 and deliveries[0].server_number == 1
