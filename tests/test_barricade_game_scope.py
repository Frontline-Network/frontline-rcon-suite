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
