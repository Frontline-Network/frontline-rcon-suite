"""Synthetic ASGI scan with real isolated PostgreSQL, Redis and local journal."""
import asyncio
import json
import os
import time
from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch
from uuid import uuid4

import django
import pytest
import redis
from asgiref.testing import ApplicationCommunicator
from channels.layers import InMemoryChannelLayer
from sqlalchemy import select

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api import auth, barricade
from rcon import barricade_scan_dispatch as adapter, barricade_scan_journal as journal
from rcon import barricade_scan_presence as presence, session_journal_observation as observations
from rcon.barricade import ServerRequestType
from rcon.models import PlayerID, PlayerSession, PendingPlayerConnect, PendingPlayerDisconnect, UnidentifiedSessionEvent
from rcon.player_presence import capture_observation, redis_time, snapshot_key
from rcon.session_event_journal import SessionEventJournal
from tests.test_barricade_scan_journal_postgres import database, prepare_adapter


@pytest.mark.parametrize('scenario', ['confirmed', 'lost_response', 'pending_event'])
def test_scan_from_observations_through_websocket(database, monkeypatch, tmp_path, scenario):
    url = os.environ.get('TEST_REDIS_URL')
    if not url:
        pytest.skip('requires disposable Redis')
    prepare_adapter(database, monkeypatch)
    for model in (PlayerID, PlayerSession, PendingPlayerConnect, PendingPlayerDisconnect, UnidentifiedSessionEvent):
        model.__table__.create(database.kw['bind'], checkfirst=True)
    monkeypatch.setattr(presence, 'get_session_maker', lambda: database)
    start = time.time() - 60
    with database.begin() as session:
        binding = session.get(journal.BarricadeScanIntegration,
                              (3, '01234567-89ab-4def-8012-0123456789ab'))
        binding.registered_at_us = int((start - 60) * 1_000_000)
        player = PlayerID(player_id='synthetic-eos')
        session.add(player)
        session.flush()
        row = PlayerSession(player_id_id=player.id, server_number=3, start=datetime.fromtimestamp(int(start)),
                            start_event_us=int(start) * 1_000_000)
        session.add(row)
        session.flush()
        session_id = row.id
    red = redis.Redis.from_url(url, decode_responses=True)
    scope = uuid4().hex * 2
    namespace = 'integration:01234567-89ab-4def-8012-0123456789ab'
    monkeypatch.setenv('HLL_DB_URL', 'postgresql://synthetic@localhost/synthetic')
    monkeypatch.setattr('rcon.cache_utils.get_redis_client', lambda **_kwargs: red)
    monkeypatch.setattr('rcon.player_presence.database_scope', lambda _url: scope)
    monkeypatch.setattr(barricade, 'get_server_number', lambda: '3')
    monkeypatch.setattr(barricade, 'barricade_game_for_server', lambda: 'HLLV')
    try:
        api = SimpleNamespace(without_retries=lambda: nullcontext(),
                              get_player_ids=lambda: [('synthetic', 'synthetic-eos')])
        assert capture_observation(red, api, scope=scope, server_number=3)
        local = SessionEventJournal(tmp_path / 'session.sqlite')
        if scenario == 'pending_event':
            local.remember(3, 'synthetic-eos', 'disconnect', int(time.time() * 1_000_000))
        poll_start, poll_end = redis_time(red), redis_time(red)
        assert observations.publish(red, local, scope=scope, server_number=3,
                                    poll_started_at=poll_start, poll_finished_at=poll_end)

        async def run():
            results = asyncio.Queue()
            class TestConsumer(barricade.BarricadeConsumer):
                async def connect(self):
                    await self.accept()
                    async def start_scan():
                        result = await self._durable_scan_once()
                        await results.put(result)
                    self.scan_task = asyncio.create_task(start_scan())
                async def send_request(self, request_type, payload):
                    return await asyncio.wait_for(super().send_request(request_type, payload), timeout=0.7)
            app = auth.APITokenAuthMiddleware(TestConsumer.as_asgi(), perms=('synthetic',))
            ws_scope = {'type': 'websocket', 'path': '/ws/barricade',
                'query_string': b'frontline_integration=synthetic',
                'headers': [(b'authorization', b'Bearer synthetic-key')], 'subprotocols': []}
            with patch.object(auth, 'get_user', AsyncMock(return_value=(SimpleNamespace(pk=7), None))), \
                 patch.object(auth, 'has_perms', AsyncMock(return_value=True)), \
                 patch.object(auth, 'get_barricade_api_key_id', AsyncMock(return_value=1)), \
                 patch.object(auth, 'get_barricade_scan_namespace', AsyncMock(return_value=namespace)), \
                 patch('channels.consumer.get_channel_layer', return_value=InMemoryChannelLayer()):
                socket = ApplicationCommunicator(app, ws_scope)
                await socket.send_input({'type': 'websocket.connect'})
                assert (await socket.receive_output(timeout=5))['type'] == 'websocket.accept'
                if scenario != 'pending_event':
                    request = json.loads((await socket.receive_output(timeout=5))['text'])
                    assert request['request'] == 'scan_players'
                    assert request['payload'] == {'player_ids': ['synthetic-eos'], 'game': 'HLLV'}
                    if scenario == 'confirmed':
                        await socket.send_input({'type': 'websocket.receive', 'text': json.dumps(
                            {'id': request['id'], 'request': None, 'failed': False, 'response': None})})
                assert await asyncio.wait_for(results.get(), 5) is None
                await socket.send_input({'type': 'websocket.disconnect', 'code': 1000})
                await socket.wait(timeout=5)
        asyncio.run(run())
        with database() as session:
            statuses = session.scalars(select(journal.BarricadeScanDelivery.status)).all()
            assert statuses == {'confirmed': ['done'], 'lost_response': ['review'], 'pending_event': []}[scenario]
    finally:
        red.delete(snapshot_key(scope, 3), observations.observation_key(scope, 3))
        red.close()
