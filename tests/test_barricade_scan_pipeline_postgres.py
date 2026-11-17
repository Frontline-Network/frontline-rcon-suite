"""Isolated integration of bounded evidence and synthetic scan delivery."""
import asyncio
import os
import time
from contextlib import nullcontext
from datetime import datetime
from types import SimpleNamespace
from uuid import uuid4

import pytest
import redis
from sqlalchemy import select

from rcon import barricade_scan_dispatch as adapter, barricade_scan_journal as journal
from rcon import barricade_scan_presence as presence, session_journal_observation as observations
from rcon.models import PlayerID, PlayerSession, PendingPlayerConnect, PendingPlayerDisconnect, UnidentifiedSessionEvent
from rcon.player_presence import capture_observation, redis_time, snapshot_key
from rcon.session_event_journal import SessionEventJournal
from tests.test_barricade_scan_journal_postgres import database, prepare_adapter


@pytest.mark.parametrize('backlog', [False, True])
def test_bounded_synthetic_pipeline(database, monkeypatch, tmp_path, backlog):
    url = os.environ.get('TEST_REDIS_URL')
    if not url:
        pytest.skip('requires disposable Redis')
    prepare_adapter(database, monkeypatch)
    engine = database.kw['bind']
    for model in (PlayerID, PlayerSession, PendingPlayerConnect, PendingPlayerDisconnect, UnidentifiedSessionEvent):
        model.__table__.create(engine, checkfirst=True)
    monkeypatch.setattr(presence, 'get_session_maker', lambda: database)
    start = time.time() - 60
    with database.begin() as session:
        player = PlayerID(player_id='synthetic-eos')
        session.add(player)
        session.flush()
        row = PlayerSession(player_id_id=player.id, server_number=3, start=datetime.fromtimestamp(start),
                            start_event_us=int(start * 1_000_000))
        session.add(row)
        session.flush()
        session_id = row.id
    red = redis.Redis.from_url(url, decode_responses=True)
    scope = uuid4().hex * 2
    try:
        api = SimpleNamespace(without_retries=lambda: nullcontext(),
                              get_player_ids=lambda: [('synthetic', 'synthetic-eos')])
        assert capture_observation(red, api, scope=scope, server_number=3)
        local = SessionEventJournal(tmp_path / 'session.sqlite')
        if backlog:
            local.remember(3, 'synthetic-eos', 'disconnect', int(time.time() * 1_000_000))
        poll_started = redis_time(red)
        poll_finished = redis_time(red)
        assert observations.publish(red, local, scope=scope, server_number=3,
                                    poll_started_at=poll_started, poll_finished_at=poll_finished)
        sent = []
        async def verifier(row_id, player_id):
            return await asyncio.to_thread(presence.session_has_bounded_evidence, red, scope=scope,
                                           server_number=3, session_id=row_id, player_id=player_id)
        async def sender(player_id, game):
            sent.append((player_id, game))
        async def run():
            args = (3, 'integration:01234567-89ab-4def-8012-0123456789ab', session_id,
                    'synthetic-eos', 'HLLV', sender)
            first = await adapter.dispatch(*args, credential_id=1, verify_session=verifier)
            second = await adapter.dispatch(*args, credential_id=1, verify_session=verifier)
            return first, second
        assert asyncio.run(run()) == (('deferred', 'deferred') if backlog else ('done', 'already_recorded'))
        assert sent == ([] if backlog else [('synthetic-eos', 'HLLV')])
        with database() as session:
            rows = session.scalars(select(journal.BarricadeScanDelivery)).all()
            assert len(rows) == (0 if backlog else 1)
            if rows:
                assert rows[0].status == 'done'
    finally:
        red.delete(snapshot_key(scope, 3), observations.observation_key(scope, 3))
        red.close()
