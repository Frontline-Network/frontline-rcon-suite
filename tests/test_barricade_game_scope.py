"""Game-aware Barricade contracts; only synthetic data and mocked actions."""
import asyncio
import os
from datetime import datetime, timedelta
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock, patch

import django
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from contextlib import contextmanager

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api import barricade
from rcon import blacklist
from rcon.barricade import (BanPlayersRequestPayload, BarricadeRequestError,
                            UnbanPlayersRequestPayload, NewReportRequestPayload)
from rcon.models import PlayerID, PlayerSession


@compiles(JSONB, 'sqlite')
def sqlite_jsonb(_element, _compiler, **_kwargs):
    return 'JSON'


@pytest.mark.parametrize('configured,expected', [('hll', 'HLL'), ('hllv', 'HLLV')])
def test_new_session_scan_includes_configured_game(monkeypatch, configured, expected):
    monkeypatch.setenv('HLL_GAME', configured)
    player_id = 'a' * 32 if configured == 'hllv' else '76561198000000000'
    async def run():
        consumer = barricade.BarricadeConsumer()
        now = datetime(2026, 1, 1, 12)
        consumer.send_request = AsyncMock(return_value={})
        with patch.object(barricade, 'get_most_recent_session_date', AsyncMock(return_value=now)), \
             patch.object(barricade, 'get_joined_players_since', AsyncMock(return_value=[(player_id, now + timedelta(seconds=1))])), \
             patch.object(barricade.asyncio, 'sleep', AsyncMock(side_effect=[None, asyncio.CancelledError])):
            with pytest.raises(asyncio.CancelledError):
                await consumer._scan_players_loop()
        payload = consumer.send_request.await_args.args[1]
        assert payload == {'player_ids': [player_id], 'game': expected}
    asyncio.run(run())


@pytest.mark.parametrize('configured,expected', [('hll', 'HLL'), ('hllv', 'HLLV')])
def test_online_warning_scan_includes_configured_game(monkeypatch, configured, expected):
    monkeypatch.setenv('HLL_GAME', configured)
    handler = object.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = SimpleNamespace(get_player_ids=lambda: [('Synthetic', 'synthetic')])
    send = Mock()
    monkeypatch.setattr(blacklist, 'send_to_barricade', send)
    handler.handle_barricade_warn_online(
        blacklist.BlacklistBarricadeWarnOnlineCommand(player_ids=['synthetic']))
    assert send.call_args.kwargs['payload'] == {'player_ids': ['synthetic'], 'game': expected}


@pytest.mark.parametrize('configured,wrong_game', [('hll', 'HLLV'), ('hllv', 'HLL')])
def test_online_warning_for_other_game_is_not_scanned(monkeypatch, configured, wrong_game):
    monkeypatch.setenv('HLL_GAME', configured)
    handler = object.__new__(blacklist.BlacklistCommandHandler)
    handler.rcon = SimpleNamespace(get_player_ids=Mock(return_value=[('Synthetic', 'synthetic')]))
    send = Mock()
    monkeypatch.setattr(blacklist, 'send_to_barricade', send)
    handler.handle_barricade_warn_online(
        blacklist.BlacklistBarricadeWarnOnlineCommand(player_ids=['synthetic'], game=wrong_game))
    handler.rcon.get_player_ids.assert_not_called()
    send.assert_not_called()


@pytest.mark.parametrize('operation', ['ban', 'unban', 'report'])
@pytest.mark.parametrize('configured,wrong_game', [('hll', 'HLLV'), ('hllv', 'HLL')])
def test_explicit_other_game_cannot_mutate_or_notify(monkeypatch, operation, configured, wrong_game):
    monkeypatch.setenv('HLL_GAME', configured)
    async def run():
        consumer = barricade.BarricadeConsumer()
        with patch.object(barricade, 'assert_blacklist_exists', AsyncMock()) as lookup, \
             patch.object(barricade, 'ban_player', AsyncMock()) as ban, \
             patch.object(barricade, 'unban_player', AsyncMock()) as unban, \
             patch.object(barricade.BlacklistCommandHandler, 'send') as notify:
            with pytest.raises(BarricadeRequestError):
                if operation == 'ban':
                    await consumer.ban_players(BanPlayersRequestPayload.model_validate({
                        'player_ids': {'synthetic': None}, 'config': {'game': wrong_game, 'banlist_id': '1', 'reason': 'synthetic'}}))
                elif operation == 'unban':
                    await consumer.unban_players(UnbanPlayersRequestPayload.model_validate({
                        'ban_ids': ['1'], 'config': {'game': wrong_game, 'banlist_id': '1'}}))
                else:
                    await consumer.new_report(NewReportRequestPayload.model_validate({
                        'game': wrong_game, 'created_at': '2026-01-01T00:00:00Z', 'body': '',
                        'reasons': [], 'attachment_urls': [], 'players': []}))
            lookup.assert_not_awaited()
            ban.assert_not_awaited()
            unban.assert_not_awaited()
            notify.assert_not_called()
    asyncio.run(run())


@pytest.mark.parametrize('configured,game', [('hll', 'HLL'), ('hllv', 'HLLV'), ('hll', None), ('hllv', None)])
def test_matching_or_legacy_ban_keeps_existing_behavior(monkeypatch, configured, game):
    monkeypatch.setenv('HLL_GAME', configured)
    async def run():
        consumer = barricade.BarricadeConsumer()
        payload = BanPlayersRequestPayload.model_validate({
            'player_ids': {'synthetic': None}, 'config': {'game': game, 'banlist_id': '1', 'reason': 'synthetic'}})
        with patch.object(barricade, 'assert_blacklist_exists', AsyncMock()), \
             patch.object(barricade, 'ban_player', AsyncMock(return_value=42)) as ban:
            assert await consumer.ban_players(payload) == {'ban_ids': {'synthetic': '42'}}
            ban.assert_awaited_once()
    asyncio.run(run())


def test_scan_queries_only_its_own_server(monkeypatch):
    monkeypatch.setenv('SERVER_NUMBER', '3')
    engine = create_engine('sqlite://')
    for model in (PlayerID, PlayerSession):
        model.__table__.create(engine)
    start = datetime(2026, 1, 1, 12)
    try:
        with Session(engine) as sess:
            for pid, server in [('local', 3), ('other', 4)]:
                player = PlayerID(player_id=pid)
                sess.add(player)
                sess.flush()
                sess.add(PlayerSession(player_id_id=player.id, server_number=server, start=start + timedelta(seconds=server)))
            sess.commit()
        @contextmanager
        def scope():
            with Session(engine) as sess:
                yield sess
        monkeypatch.setattr(barricade.models, 'enter_session', scope)
        assert [row[0] for row in barricade.get_joined_players_since.func(start)] == ['local']
        assert barricade.get_most_recent_session_date.func() == start + timedelta(seconds=3)
    finally:
        engine.dispose()
