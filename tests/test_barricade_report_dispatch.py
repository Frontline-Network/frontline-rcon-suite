"""Report-triggered scans stay on the current server and authenticated connection."""
import asyncio
from contextlib import nullcontext
from threading import Event
from unittest.mock import AsyncMock, Mock

import pytest

from rcon import barricade_scan_dispatch as dispatch


@pytest.fixture
def report(monkeypatch):
    monkeypatch.setenv('SERVER_NUMBER', '8')
    monkeypatch.setattr(dispatch.journal, 'registration_boundary', lambda *args: 1)
    monkeypatch.setattr(dispatch.journal, 'delivery_scope', lambda *args: nullcontext())
    monkeypatch.setattr(dispatch.journal, 'credential_is_registered', lambda *args: True)
    monkeypatch.setattr(dispatch, 'key_is_live', lambda key: True)
    rcon = Mock()
    rcon.without_retries.return_value = nullcontext()
    rcon.get_player_ids.return_value = [('same name', 'online-a'), ('same name', 'online-b')]
    monkeypatch.setattr('rcon.rcon.get_rcon', lambda: rcon)
    return rcon


def test_report_sends_only_distinct_online_ids_and_accepts_immediate_reply(report):
    sender = AsyncMock()
    asyncio.run(dispatch.dispatch_report_scan(8, 'integration:example', 32,
        ['online-b', 'offline', 'online-a', 'online-a'], sender))
    sender.assert_awaited_once_with(['online-a', 'online-b'])


@pytest.mark.parametrize('failure', ['server', 'unregistered', 'revoked', 'rotated', 'offline'])
def test_report_does_not_send_without_current_scope_and_presence(report, monkeypatch, failure):
    if failure == 'unregistered':
        monkeypatch.setattr(dispatch.journal, 'registration_boundary', lambda *args: None)
    elif failure == 'revoked':
        monkeypatch.setattr(dispatch, 'key_is_live', Mock(side_effect=[True, False]))
    elif failure == 'rotated':
        monkeypatch.setattr(dispatch.journal, 'credential_is_registered', lambda *args: False)
    sender = AsyncMock()
    asyncio.run(dispatch.dispatch_report_scan(7 if failure == 'server' else 8,
        'integration:example', 32, ['absent' if failure == 'offline' else 'online-a'], sender))
    sender.assert_not_awaited()
    if failure in ('server', 'unregistered'):
        report.get_player_ids.assert_not_called()


def test_disconnected_report_does_not_send_after_roster_read(report):
    reading = Event()
    release = Event()
    def roster():
        reading.set()
        assert release.wait(3)
        return [('name', 'online-a')]
    report.get_player_ids.side_effect = roster
    sender = AsyncMock()
    async def disconnect():
        task = asyncio.create_task(dispatch.dispatch_report_scan(8, 'integration:example', 32, ['online-a'], sender))
        try:
            assert await asyncio.to_thread(reading.wait, 3)
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        finally:
            release.set()
    asyncio.run(disconnect())
    sender.assert_not_awaited()


def test_lost_report_reply_is_not_retried(report):
    sender = AsyncMock(side_effect=OSError('lost reply'))
    with pytest.raises(OSError, match='lost reply'):
        asyncio.run(dispatch.dispatch_report_scan(8, 'integration:example', 32, ['online-b'], sender))
    sender.assert_awaited_once_with(['online-b'])
