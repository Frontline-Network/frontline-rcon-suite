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
