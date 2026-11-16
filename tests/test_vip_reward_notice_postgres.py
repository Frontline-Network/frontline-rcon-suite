"""Concurrent notice consumers use one durable reservation on PostgreSQL."""
import os
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from pathlib import Path
from threading import Event
from unittest.mock import Mock
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import sessionmaker

from rcon.models import VipRewardGrant, VipRewardNotice
from rcon.user_config.vip_rewards import VipRewardsUserConfig
from rcon.vip_rewards import service


def test_competing_consumers_send_only_once_on_postgres(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "vip_notice_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    VipRewardGrant.__table__.create(engine)
    VipRewardNotice.__table__.create(engine)
    factory = sessionmaker(bind=engine, expire_on_commit=False)
    cfg = VipRewardsUserConfig(enabled=True, dry_run=False, notify_player=True)
    monkeypatch.setattr(service, "get_session_maker", lambda: factory)
    monkeypatch.setattr(service, "server", lambda: 3)
    monkeypatch.setattr(service.VipRewardsUserConfig, "load_from_db", lambda: cfg)
    now = service.time.time()
    try:
        with factory.begin() as session:
            grant = VipRewardGrant(server_number=3, preview=False, player_id="synthetic",
                                  rule="melee", trigger="one", occurred=now,
                                  requested_seconds=3600, credited_seconds=3600,
                                  limit=1, status="awarded", reason="", description="")
            session.add(grant)
            session.flush()
            grant_id = grant.id
            service.queue_reward_notice(session, grant, cfg, now)
        started, release = Event(), Event()
        rcon = Mock()
        rcon.without_retries.side_effect = nullcontext
        def send(**_kwargs):
            started.set()
            assert release.wait(10)
            return True
        rcon.message_player.side_effect = send
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(service.deliver_reward_notice, rcon, grant_id)
            assert started.wait(10)
            second = pool.submit(service.deliver_reward_notice, rcon, grant_id)
            second.result(timeout=10)
            release.set()
            first.result(timeout=10)
        with factory() as session:
            notice = session.get(VipRewardNotice, grant_id)
            assert notice.status == "sent" and notice.attempts == 1
        rcon.message_player.assert_called_once()
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def test_notice_migration_creates_expected_schema_and_preserves_old_grants():
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "vip_notice_migration_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    path = Path(__file__).resolve().parents[1] / "alembic/versions/c3230a1b2c3d_vip_reward_notice.py"
    spec = importlib.util.spec_from_file_location("vip_notice_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE vip_reward_grant (id integer PRIMARY KEY)"))
            connection.execute(text("INSERT INTO vip_reward_grant VALUES (1)"))
            migration.op = Operations(MigrationContext.configure(connection))
            migration.upgrade()
            migration.upgrade()  # A staged pilot must also work during a normal later upgrade.
            assert {col["name"] for col in inspect(connection).get_columns("vip_reward_notice")} == set(VipRewardNotice.__table__.columns.keys())
            assert connection.execute(text("SELECT count(*) FROM vip_reward_notice")).scalar_one() == 0
            assert connection.execute(text("SELECT count(*) FROM vip_reward_grant")).scalar_one() == 1
            connection.execute(text("""INSERT INTO vip_reward_notice
                (grant_id, server_number, player_id, message, status, attempts, created_at, due_at, expires_at, updated_at)
                VALUES (1, 3, 'synthetic', 'test', 'review', 1, 1, 1, 2, 1)"""))
            with pytest.raises(RuntimeError, match="pending VIP notices"):
                migration.downgrade()
            assert inspect(connection).has_table("vip_reward_notice")
            connection.execute(text("DELETE FROM vip_reward_notice"))
            migration.downgrade()
            assert not inspect(connection).has_table("vip_reward_notice")
            assert connection.execute(text("SELECT count(*) FROM vip_reward_grant")).scalar_one() == 1
            connection.execute(text("CREATE TABLE vip_reward_notice (grant_id integer PRIMARY KEY)"))
            with pytest.raises(RuntimeError, match="Unexpected staged"):
                migration.upgrade()
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()
