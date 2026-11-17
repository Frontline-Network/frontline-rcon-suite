import os
import uuid
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")

from rcon import campaign_delivery, vip_lifecycle
from rcon.models import PlayerID, PlayerSession
from rcon.user_config.auto_broadcast import AutoBroadcastMessage, VipLifecycleCampaign


@compiles(JSONB, 'sqlite')
def sqlite_jsonb(_element, _compiler, **_kwargs):
    return 'JSON'


@pytest.mark.parametrize("module", [campaign_delivery, vip_lifecycle])
@pytest.mark.parametrize("start_seconds", [1711846200, 1729990200])
def test_active_session_uses_absolute_start_across_dst(monkeypatch, module, start_seconds):
    # These instants are shortly before Berlin's spring and autumn DST changes.
    start = datetime.fromtimestamp(start_seconds, timezone.utc)
    player = SimpleNamespace(id=7, player_id="player-1")
    session = SimpleNamespace(
        id=11,
        start=datetime(2024, 3, 31, 1, 30),  # legacy wall time is not UTC
        start_event_us=start_seconds * 1_000_000,
        created=datetime(2024, 3, 31),
    )

    class Query:
        def join(self, *args): return self
        def filter(self, *args): return self
        def order_by(self, *args): return self
        def all(self): return [(player, session)]

    @contextmanager
    def fake_session():
        yield SimpleNamespace(query=lambda *args: Query())

    monkeypatch.setattr(module, "enter_session", fake_session)
    monkeypatch.setattr(module, "latest_open_sessions", lambda *_: [(player, session)])
    result = module._active_sessions({"player-1"}, 1)["player-1"]
    if module is campaign_delivery:
        item = AutoBroadcastMessage(id="dst", message="hello", time_sec=60, min_session_minutes=30)
        eligible = module.session_is_eligible
        utc_start = start.replace(tzinfo=None)
    else:
        item = VipLifecycleCampaign(message="hello", min_session_minutes=30)
        eligible = module._session_is_eligible
        utc_start = start
    assert result["start"] == utc_start
    assert not eligible(item, result["start"], utc_start + timedelta(minutes=29, seconds=59))
    assert eligible(item, result["start"], utc_start + timedelta(minutes=30))


@pytest.mark.parametrize("module", [campaign_delivery, vip_lifecycle])
def test_legacy_session_uses_utc_creation_as_conservative_start(monkeypatch, module):
    player = SimpleNamespace(id=7, player_id="player-1")
    legacy_start = datetime(2024, 10, 27, 2, 30)
    created_utc = datetime(2024, 10, 27, 1, 31)
    session = SimpleNamespace(id=11, start=legacy_start, start_event_us=None, created=created_utc)

    class Query:
        def join(self, *args): return self
        def filter(self, *args): return self
        def order_by(self, *args): return self
        def all(self): return [(player, session)]

    @contextmanager
    def fake_session():
        yield SimpleNamespace(query=lambda *args: Query())

    monkeypatch.setattr(module, "enter_session", fake_session)
    monkeypatch.setattr(module, "latest_open_sessions", lambda *_: [(player, session)])
    start = module._active_sessions({"player-1"}, 1)["player-1"]["start"]
    assert start == created_utc
    if module is campaign_delivery:
        item = AutoBroadcastMessage(id="legacy", message="hello", time_sec=60, min_session_minutes=5)
        eligible = module.session_is_eligible
    else:
        item = VipLifecycleCampaign(message="hello", min_session_minutes=5)
        eligible = module._session_is_eligible
    assert not eligible(item, start, created_utc + timedelta(minutes=4, seconds=59))
    assert eligible(item, start, created_utc + timedelta(minutes=5))
    assert not eligible(item, None, created_utc + timedelta(days=1))


@pytest.mark.parametrize('module', [campaign_delivery, vip_lifecycle])
def test_delayed_older_session_cannot_override_current_connection(monkeypatch, module):
    player = SimpleNamespace(id=7, player_id='player-1')
    earlier = datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)
    later = earlier + timedelta(minutes=20)
    older_replayed = SimpleNamespace(id=12, start=earlier.replace(tzinfo=None),
        start_event_us=int(earlier.timestamp() * 1_000_000), created=datetime(2026, 1, 1, 12, 25))
    current = SimpleNamespace(id=11, start=later.replace(tzinfo=None),
        start_event_us=int(later.timestamp() * 1_000_000), created=datetime(2026, 1, 1, 12, 20))

    class Query:
        def join(self, *args): return self
        def filter(self, *args): return self
        def order_by(self, *args): return self
        def all(self): return [(player, older_replayed), (player, current)]

    @contextmanager
    def fake_session():
        yield SimpleNamespace(query=lambda *args: Query())

    monkeypatch.setattr(module, 'enter_session', fake_session)
    monkeypatch.setattr(module, 'latest_open_sessions', lambda *_: [(player, older_replayed), (player, current)])
    selected = module._active_sessions({'player-1'}, 1)['player-1']
    assert selected['session_id'] == 11
    assert selected['start'] == (later.replace(tzinfo=None) if module is campaign_delivery else later)


@pytest.mark.parametrize('module', [campaign_delivery, vip_lifecycle])
@pytest.mark.parametrize('database', ['sqlite', 'postgres'])
@pytest.mark.parametrize('end_style', ['absolute', 'legacy', 'both'])
def test_real_database_never_uses_stale_open_session_after_newer_local_end(monkeypatch, module, database, end_style):
    if database == 'postgres' and not os.getenv('RCON_SEARCH_TEST_DATABASE'):
        pytest.skip('requires isolated PostgreSQL')
    base = create_engine(os.environ['RCON_SEARCH_TEST_DATABASE'] if database == 'postgres' else 'sqlite://')
    schema = 'campaign_session_' + uuid.uuid4().hex if database == 'postgres' else None
    if schema:
        with base.begin() as conn:
            conn.execute(CreateSchema(schema))
    engine = base.execution_options(schema_translate_map={None: schema}) if schema else base
    try:
        for model in (PlayerID, PlayerSession):
            model.__table__.create(engine)
        older = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
        current = older + timedelta(minutes=20)
        with Session(engine) as sess:
            player = PlayerID(player_id='synthetic-player', created=older.replace(tzinfo=None))
            sess.add(player)
            sess.flush()
            player_db_id = player.id
            def add_session(start, created, server=3, ended=False):
                entry = PlayerSession(player_id_id=player.id, server_number=server,
                    start=start.replace(tzinfo=None), created=created.replace(tzinfo=None),
                    start_event_us=int(start.timestamp() * 1_000_000),
                    end_event_us=int((start + timedelta(seconds=1)).timestamp() * 1_000_000) if ended else None)
                sess.add(entry)
                sess.flush()
                return entry.id
            current_id = add_session(current, current)
            add_session(older, current + timedelta(minutes=5))
            add_session(current + timedelta(minutes=10), current + timedelta(minutes=10), server=4)
            sess.commit()

        @contextmanager
        def session_scope():
            with Session(engine) as sess:
                yield sess
        monkeypatch.setattr(module, 'enter_session', session_scope)
        selected = module._active_sessions({'synthetic-player'}, 3)['synthetic-player']
        assert selected['session_id'] == current_id
        assert selected['start'] == (current.replace(tzinfo=None) if module is campaign_delivery else current)
        with Session(engine) as sess:
            later = current + timedelta(minutes=15)
            sess.add(PlayerSession(player_id_id=player_db_id, server_number=3,
                start=later.replace(tzinfo=None), created=later.replace(tzinfo=None),
                start_event_us=int(later.timestamp() * 1_000_000),
                end=(later + timedelta(seconds=1)).replace(tzinfo=None) if end_style in ('legacy', 'both') else None,
                end_event_us=int((later + timedelta(seconds=1)).timestamp() * 1_000_000) if end_style in ('absolute', 'both') else None))
            sess.commit()
        assert module._active_sessions({'synthetic-player'}, 3) == {}
    finally:
        if schema:
            with base.begin() as conn:
                conn.execute(DropSchema(schema, cascade=True))
        base.dispose()


@pytest.mark.parametrize('module', [campaign_delivery, vip_lifecycle])
@pytest.mark.parametrize('database', ['sqlite', 'postgres'])
@pytest.mark.parametrize('older_us,newer_us', [(100000, 900000), (999999, 1000000)])
def test_legacy_sessions_within_same_second_use_precise_creation_order(monkeypatch, module, database, older_us, newer_us):
    if database == 'postgres' and not os.getenv('RCON_SEARCH_TEST_DATABASE'):
        pytest.skip('requires isolated PostgreSQL')
    base = create_engine(os.environ['RCON_SEARCH_TEST_DATABASE'] if database == 'postgres' else 'sqlite://')
    schema = 'campaign_same_second_' + uuid.uuid4().hex if database == 'postgres' else None
    if schema:
        with base.begin() as conn:
            conn.execute(CreateSchema(schema))
    engine = base.execution_options(schema_translate_map={None: schema}) if schema else base
    try:
        for model in (PlayerID, PlayerSession):
            model.__table__.create(engine)
        with Session(engine) as sess:
            player = PlayerID(player_id='synthetic-player')
            sess.add(player)
            sess.flush()
            # The older open row deliberately has the higher ID.
            base_time = datetime(2026, 1, 1, 12, 0, 0)
            newer = base_time + timedelta(microseconds=newer_us)
            older = base_time + timedelta(microseconds=older_us)
            sess.add_all([
                PlayerSession(player_id_id=player.id, server_number=3, start=newer,
                              created=newer, end=newer + timedelta(seconds=1)),
                PlayerSession(player_id_id=player.id, server_number=3, start=older, created=older),
            ])
            sess.commit()
        @contextmanager
        def session_scope():
            with Session(engine) as sess:
                yield sess
        monkeypatch.setattr(module, 'enter_session', session_scope)
        assert module._active_sessions({'synthetic-player'}, 3) == {}
    finally:
        if schema:
            with base.begin() as conn:
                conn.execute(DropSchema(schema, cascade=True))
        base.dispose()
