"""Session identity must be proven before automatic report moderation."""
import os
import time
import uuid
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from rcon.models import PlayerID, PlayerSession
from rcon.report_admin import session_token


@compiles(JSONB, 'sqlite')
def sqlite_jsonb(_element, _compiler, **_kwargs):
    return 'JSON'


@pytest.fixture(params=['sqlite', 'postgres'])
def database(request):
    dsn = os.getenv('TEST_POSTGRES_DSN')
    if request.param == 'postgres' and not dsn:
        pytest.skip('requires isolated PostgreSQL')
    base = create_engine(dsn if request.param == 'postgres' else 'sqlite://')
    schema = 'report_session_' + uuid.uuid4().hex if request.param == 'postgres' else None
    if schema:
        with base.begin() as conn:
            conn.execute(CreateSchema(schema))
    engine = base.execution_options(schema_translate_map={None: schema}) if schema else base
    try:
        for model in (PlayerID, PlayerSession):
            model.__table__.create(engine)
        yield engine
    finally:
        if schema:
            with base.begin() as conn:
                conn.execute(DropSchema(schema, cascade=True))
        base.dispose()


@pytest.fixture
def berlin_time():
    if not hasattr(time, 'tzset'):
        pytest.skip('requires controllable local timezone')
    previous = os.environ.get('TZ')
    os.environ['TZ'] = 'Europe/Berlin'
    time.tzset()
    try:
        yield
    finally:
        if previous is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = previous
        time.tzset()


def test_latest_absolute_session_and_uncertain_legacy_are_safe(database, berlin_time):
    old = datetime(2026, 10, 25, 0, 59, 58, tzinfo=timezone.utc)
    now = old + timedelta(seconds=3)
    with Session(database) as sess:
        player = PlayerID(player_id='synthetic-report-player')
        sess.add(player)
        sess.flush()
        current = PlayerSession(player_id_id=player.id, server_number=3,
            start=datetime(2026, 10, 25, 2, 0, 1), created=now.replace(tzinfo=None),
            start_event_us=int(now.timestamp() * 1_000_000))
        older_delayed = PlayerSession(player_id_id=player.id, server_number=3,
            start=datetime(2026, 10, 25, 2, 59, 58),
            created=(now + timedelta(seconds=1)).replace(tzinfo=None),
            start_event_us=int(old.timestamp() * 1_000_000))
        remote = PlayerSession(player_id_id=player.id, server_number=4,
            start=now.replace(tzinfo=None), created=now.replace(tzinfo=None),
            start_event_us=int((now + timedelta(seconds=2)).timestamp() * 1_000_000))
        sess.add_all([current, older_delayed, remote])
        sess.flush()
        assert session_token(sess, 3, player.player_id, now.timestamp() + 4) == current.id
        assert session_token(sess, 3, player.player_id, now.timestamp() - 1) is None
        current.start += timedelta(seconds=1)
        sess.flush()
        assert session_token(sess, 3, player.player_id, now.timestamp() + 4) is None
        current.start -= timedelta(seconds=1)
        sess.flush()
        duplicate = PlayerSession(player_id_id=player.id, server_number=3,
            start=current.start, created=current.created, start_event_us=current.start_event_us)
        sess.add(duplicate)
        sess.flush()
        assert session_token(sess, 3, player.player_id, now.timestamp() + 4) is None
        sess.delete(duplicate)
        sess.flush()
        legacy = PlayerSession(player_id_id=player.id, server_number=3,
            start=datetime(2026, 10, 25, 2, 30),
            created=(now + timedelta(seconds=2)).replace(tzinfo=None))
        sess.add(legacy)
        sess.flush()
        assert session_token(sess, 3, player.player_id, now.timestamp() + 4) is None
        sess.delete(legacy)
        current.end_event_us = int((now.timestamp() + 2) * 1_000_000)
        sess.flush()
        assert session_token(sess, 3, player.player_id, now.timestamp() + 4) is None
