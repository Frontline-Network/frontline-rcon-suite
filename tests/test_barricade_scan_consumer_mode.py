"""The experimental consumer route is opt-in and needs an authenticated binding."""
import asyncio
import os
from unittest.mock import AsyncMock

import django
import pytest

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api.barricade import BarricadeConsumer


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
