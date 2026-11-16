"""Exercise the legacy fallback using actual PostgreSQL timestamp columns."""
import os
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from uuid import uuid4
import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker
from rcon import campaign_delivery, vip_lifecycle
from rcon.models import PlayerID, PlayerSession
from rcon.user_config.auto_broadcast import AutoBroadcastMessage, VipLifecycleCampaign


def test_legacy_and_absolute_times_with_real_postgres(monkeypatch):
    dsn = os.environ.get('TEST_POSTGRES_DSN')
    if not dsn:
        pytest.skip('requires disposable PostgreSQL')
    root = create_engine(dsn)
    schema = 'session_time_' + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={'options': f'-csearch_path={schema}'})
    PlayerID.__table__.create(engine)
    PlayerSession.__table__.create(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    try:
        creation = datetime(2026, 1, 1, 12)
        with maker.begin() as session:
            player = PlayerID(player_id='synthetic')
            session.add(player)
            session.flush()
            session.add(PlayerSession(player=player, server_number=3, server_name='test',
                start=datetime(2026, 1, 1, 13), start_event_us=None, created=creation))
        @contextmanager
        def fake_enter():
            with maker() as session:
                yield session
        for module in (campaign_delivery, vip_lifecycle):
            monkeypatch.setattr(module, 'enter_session', fake_enter)
            actual = module._active_sessions({'synthetic'}, 3)['synthetic']['start']
            assert actual == creation
        campaign = AutoBroadcastMessage(id='test', message='test', time_sec=60, min_session_minutes=5)
        vip = VipLifecycleCampaign(message='test', min_session_minutes=5)
        assert not campaign_delivery.session_is_eligible(campaign, creation, creation + timedelta(minutes=4))
        assert campaign_delivery.session_is_eligible(campaign, creation, creation + timedelta(minutes=5))
        assert vip_lifecycle._session_is_eligible(vip, creation, (creation + timedelta(minutes=5)).replace(tzinfo=timezone.utc))
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()
