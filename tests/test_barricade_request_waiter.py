"""Exercise outbound Barricade requests without a network or real actions."""
import asyncio
import os
from contextlib import contextmanager
from datetime import datetime
from unittest.mock import AsyncMock, patch

import django
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api import barricade
from api.barricade import BarricadeConsumer
from rcon.barricade import BarricadeRequestError, ResponseBody, ServerRequestType
from rcon.models import PlayerID, PlayerSession


@compiles(JSONB, 'sqlite')
def sqlite_jsonb(_element, _compiler, **_kwargs):
    return 'JSON'


def test_immediate_response_is_not_lost_before_send_returns():
    async def run():
        consumer = BarricadeConsumer()

        async def immediate_response(request):
            await consumer.handle_response(ResponseBody(id=request['id'], response={'ok': True}))

        consumer.send_json = AsyncMock(side_effect=immediate_response)
        result = await asyncio.wait_for(
            consumer.send_request(ServerRequestType.SCAN_PLAYERS, {'player_ids': ['synthetic']}),
            timeout=0.2,
        )
        assert result == {'ok': True}
        assert consumer._waiters == {}

    asyncio.run(run())


def test_send_failure_cleans_up_waiter():
    async def run():
        consumer = BarricadeConsumer()
        consumer.send_json = AsyncMock(side_effect=OSError('synthetic disconnect'))
        with pytest.raises(OSError):
            await consumer.send_request(ServerRequestType.SCAN_PLAYERS, {'player_ids': []})
        assert consumer._waiters == {}

    asyncio.run(run())


def test_immediate_error_response_is_delivered_and_cleaned_up():
    async def run():
        consumer = BarricadeConsumer()

        async def immediate_error(request):
            await consumer.handle_response(ResponseBody(
                id=request['id'], response={'error': 'synthetic rejection'}, failed=True))

        consumer.send_json = AsyncMock(side_effect=immediate_error)
        with pytest.raises(BarricadeRequestError, match='synthetic rejection'):
            await consumer.send_request(ServerRequestType.SCAN_PLAYERS, {'player_ids': []})
        assert consumer._waiters == {}

    asyncio.run(run())


def test_failed_send_after_immediate_error_does_not_leak_future_error():
    async def run():
        consumer = BarricadeConsumer()
        unhandled = []
        loop = asyncio.get_running_loop()
        loop.set_exception_handler(lambda _loop, context: unhandled.append(context))

        async def respond_then_disconnect(request):
            await consumer.handle_response(ResponseBody(
                id=request['id'], response={'error': 'synthetic rejection'}, failed=True))
            raise OSError('synthetic disconnect')

        consumer.send_json = AsyncMock(side_effect=respond_then_disconnect)
        with pytest.raises(OSError, match='synthetic disconnect'):
            await consumer.send_request(ServerRequestType.SCAN_PLAYERS, {'player_ids': []})
        await asyncio.sleep(0)
        assert consumer._waiters == {}
        assert unhandled == []

    asyncio.run(run())


def test_cancelled_request_cleans_up_waiter():
    async def run():
        consumer = BarricadeConsumer()
        sent = asyncio.Event()

        async def send(_request):
            sent.set()

        consumer.send_json = AsyncMock(side_effect=send)
        task = asyncio.create_task(consumer.send_request(ServerRequestType.SCAN_PLAYERS, {'player_ids': []}))
        await sent.wait()
        assert len(consumer._waiters) == 1
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        assert consumer._waiters == {}

    asyncio.run(run())


def test_scan_starts_with_valid_cursor_when_session_history_is_empty():
    async def run():
        consumer = BarricadeConsumer()
        read = AsyncMock(return_value=[])
        with patch.object(barricade, 'get_most_recent_session_date', AsyncMock(return_value=None)), \
             patch.object(barricade, 'get_joined_players_since', read), \
             patch.object(barricade.asyncio, 'sleep', AsyncMock(side_effect=[None, asyncio.CancelledError])):
            with pytest.raises(asyncio.CancelledError):
                await consumer._scan_players_loop()
        assert isinstance(read.await_args.args[0], datetime)

    asyncio.run(run())


def test_scan_recovers_from_initial_database_error():
    async def run():
        consumer = BarricadeConsumer()
        before = datetime.now()
        initial = AsyncMock(side_effect=[OSError('synthetic database outage'), datetime(2026, 1, 1)])
        read = AsyncMock(return_value=[])
        with patch.object(barricade, 'get_most_recent_session_date', initial), \
             patch.object(barricade, 'get_joined_players_since', read), \
             patch.object(barricade.asyncio, 'sleep', AsyncMock(side_effect=[None, None, asyncio.CancelledError])):
            with pytest.raises(asyncio.CancelledError):
                await consumer._scan_players_loop()
        assert initial.await_count == 2
        assert read.await_count == 1
        assert before <= read.await_args.args[0] <= datetime.now()

    asyncio.run(run())


@pytest.mark.xfail(strict=True, reason='Unconfirmed scan is lost; see issue #397')
def test_scan_failure_does_not_advance_past_unconfirmed_players():
    async def run():
        consumer = BarricadeConsumer()
        initial = datetime(2026, 1, 1, 12)
        later = datetime(2026, 1, 1, 12, 1)
        read = AsyncMock(side_effect=[[('synthetic-player', later)], []])
        consumer.send_request = AsyncMock(side_effect=OSError('synthetic disconnect'))
        with patch.object(barricade, 'get_most_recent_session_date', AsyncMock(return_value=initial)), \
             patch.object(barricade, 'get_joined_players_since', read), \
             patch.object(barricade.asyncio, 'sleep', AsyncMock(side_effect=[None, None, asyncio.CancelledError])):
            with pytest.raises(asyncio.CancelledError):
                await consumer._scan_players_loop()
        assert read.await_args_list[1].args[0] == initial

    asyncio.run(run())


@pytest.mark.xfail(strict=True, reason='Timestamp-only cursor skips ties; see issue #397')
def test_scan_cursor_can_distinguish_sessions_with_equal_start_time():
    engine = create_engine('sqlite://')
    for model in (PlayerID, PlayerSession):
        model.__table__.create(engine)
    stamp = datetime(2026, 1, 1, 12)
    try:
        with Session(engine) as sess:
            for player_id in ('already-scanned', 'later-commit'):
                player = PlayerID(player_id=player_id)
                sess.add(player)
                sess.flush()
                sess.add(PlayerSession(player_id_id=player.id, server_number=3, start=stamp))
            sess.commit()

        @contextmanager
        def scope():
            with Session(engine) as sess:
                yield sess
        with patch.object(barricade.models, 'enter_session', scope):
            result = barricade.get_joined_players_since.func(stamp)
        # The timestamp alone cannot distinguish the later row from one
        # already acknowledged; recovery must supply additional identity.
        assert {player_id for player_id, _ in result} == {'later-commit'}
    finally:
        engine.dispose()


@pytest.mark.xfail(strict=True, reason='Reconnect skips sessions created while disconnected; see issue #397')
def test_reconnect_does_not_skip_unscanned_sessions():
    async def run():
        consumer = BarricadeConsumer()
        last_confirmed = datetime(2026, 1, 1, 12)
        joined_while_disconnected = datetime(2026, 1, 1, 12, 1)
        consumer._last_seen_session = last_confirmed
        read = AsyncMock(return_value=[])
        with patch.object(barricade, 'get_most_recent_session_date', AsyncMock(return_value=joined_while_disconnected)), \
             patch.object(barricade, 'get_joined_players_since', read), \
             patch.object(barricade.asyncio, 'sleep', AsyncMock(side_effect=[None, asyncio.CancelledError])):
            with pytest.raises(asyncio.CancelledError):
                await consumer._scan_players_loop()
        assert read.await_args.args[0] == last_confirmed

    asyncio.run(run())
