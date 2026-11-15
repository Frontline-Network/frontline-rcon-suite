"""Regressions for blocked campaign queues and interrupted sends."""
from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timedelta
import os
from threading import Event
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from rcon import campaign_delivery as cd
from rcon.models import CampaignDelivery
from rcon.user_config.auto_broadcast import AutoBroadcastMessage, AutoBroadcastUserConfig


@pytest.fixture(params=["sqlite", "postgres"])
def store(monkeypatch, request):
    root = None
    schema = None
    if request.param == "postgres":
        dsn = os.environ.get("TEST_POSTGRES_DSN")
        if not dsn:
            pytest.skip("requires disposable PostgreSQL")
        root = create_engine(dsn)
        schema = "campaign_queue_" + uuid4().hex
        with root.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine("sqlite://")
    with engine.begin() as conn:
        conn.execute(text("""CREATE TABLE campaign_deliveries (id INTEGER PRIMARY KEY, server_number INTEGER,
            campaign_id TEXT, player_id_id INTEGER, player_session_id INTEGER, player_name TEXT, message TEXT,
            status TEXT, attempt_count INTEGER, eligible_at TIMESTAMP, next_attempt_at TIMESTAMP,
            created_at TIMESTAMP, updated_at TIMESTAMP, last_attempt_at TIMESTAMP, sent_at TIMESTAMP, last_error TEXT)"""))
        conn.execute(text("""CREATE TABLE vip_lifecycle_deliveries (id INTEGER PRIMARY KEY, server_number INTEGER,
            player_session_id INTEGER, test_mode BOOLEAN, status TEXT, sent_at TIMESTAMP, last_attempt_at TIMESTAMP)"""))

    class Proxy:
        def __init__(self, session): self.session = session
        def execute(self, statement, *args, **kwargs):
            if "pg_try_advisory_xact_lock" in str(statement):
                return type("Lock", (), {"scalar": lambda _: True})()
            return self.session.execute(statement, *args, **kwargs)
        def __getattr__(self, key): return getattr(self.session, key)

    @contextmanager
    def session():
        with Session(engine) as actual, actual.begin():
            yield Proxy(actual) if request.param == "sqlite" else actual
    monkeypatch.setattr(cd, "enter_session", session)
    yield engine
    engine.dispose()
    if root is not None:
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def insert(conn, ident, campaign, status, when, *, last_attempt=None):
    conn.execute(text("""INSERT INTO campaign_deliveries (id,server_number,campaign_id,player_id_id,
        player_session_id,player_name,message,status,attempt_count,eligible_at,created_at,updated_at,last_attempt_at)
        VALUES (:id,1,:campaign,1,1,'fake','fake',:status,1,:when,:when,:when,:attempt)"""),
        {"id": ident, "campaign": campaign, "status": status,
         "when": when.strftime("%Y-%m-%d %H:%M:%S.%f"),
         "attempt": last_attempt.strftime("%Y-%m-%d %H:%M:%S.%f") if last_attempt else None})


def test_paused_pages_do_not_hide_later_active_campaign(store):
    now = datetime(2026, 1, 1, 12)
    with store.begin() as conn:
        for ident in range(1, 1002):
            insert(conn, ident, f"paused-{ident}", "queued", now)
        insert(conn, 1002, "active", "queued", now)
    campaigns = [AutoBroadcastMessage(id=f"paused-{ident}", time_sec=60, message="fake",
                                      delivery_mode="player_message", enabled=False)
                 for ident in range(1, 1002)]
    campaigns.append(AutoBroadcastMessage(id="active", time_sec=60, message="fake", delivery_mode="player_message"))
    result = cd.claim_next_delivery(config=AutoBroadcastUserConfig(enabled=True), campaigns=campaigns,
        online_players={"fake": {"player_name": "fake", "is_vip": False}},
        active_sessions={"fake": {"session_id": 1, "start": now - timedelta(hours=1)}},
        player_count=1, seeding_config=None, server_number=1, now=now)
    assert result["id"] == 1002
    with Session(store) as session:
        assert session.get(CampaignDelivery, 1).status == "queued"
        assert session.get(CampaignDelivery, 1002).status == "sending"


def test_recovered_uncertain_send_is_never_requeued_by_late_failure(store):
    now = datetime(2026, 1, 1, 12)
    with store.begin() as conn:
        insert(conn, 1, "active", "sending", now, last_attempt=now)
    cd._recover_interrupted_deliveries(1, now + timedelta(seconds=10))
    with Session(store) as session:
        assert session.get(CampaignDelivery, 1).status == "sending"
    cd._recover_interrupted_deliveries(1, now + timedelta(seconds=121))
    cd.finish_delivery(1, success=False, now=now + timedelta(seconds=122), error="late rejection")
    with Session(store) as session:
        assert session.get(CampaignDelivery, 1).status == "failed"
        assert session.get(CampaignDelivery, 1).next_attempt_at is None


def test_unknown_vip_status_preserves_targeted_queue_but_allows_public_delivery(store):
    now = datetime(2026, 1, 1, 12)
    with store.begin() as conn:
        insert(conn, 1, "vip", "queued", now)
        insert(conn, 2, "all", "queued", now)
    campaigns = [AutoBroadcastMessage(id="vip", time_sec=60, message="fake", delivery_mode="player_message", recipient_group="vip"),
                 AutoBroadcastMessage(id="all", time_sec=60, message="fake", delivery_mode="player_message", recipient_group="all")]
    players = {"fake": {"player_name": "fake", "is_vip": None}}
    sessions = {"fake": {"player_db_id": 1, "session_id": 1, "start": now - timedelta(hours=1)}}
    args = dict(config=AutoBroadcastUserConfig(enabled=True), campaigns=campaigns, online_players=players,
                active_sessions=sessions, player_count=1, seeding_config=None, server_number=1, now=now)
    assert cd.claim_next_delivery(**args)["id"] == 2
    with Session(store) as session:
        assert session.get(CampaignDelivery, 1).status == "queued"
    cd.finish_delivery(2, success=True, now=now)
    players["fake"]["is_vip"] = True
    args["now"] = now + timedelta(hours=1)
    assert cd.claim_next_delivery(**args)["id"] == 1


def test_failed_vip_lookup_is_unknown_not_non_vip():
    ctl = Mock()
    ctl.get_player_ids.return_value = [("Fake", "fake")]
    ctl.get_vip_ids.side_effect = OSError("unavailable")
    assert cd._online_players(ctl)["fake"]["is_vip"] is None
    def campaign(group):
        return AutoBroadcastMessage(time_sec=60, message="fake", recipient_group=group)
    assert cd.recipient_is_eligible(campaign("vip"), None) is None
    assert cd.recipient_is_eligible(campaign("non_vip"), None) is None
    assert cd.recipient_is_eligible(campaign("all"), None) is True


def test_unknown_vip_status_does_not_enqueue_targeted_messages(monkeypatch):
    now = datetime(2026, 1, 1, 12)
    campaigns = [AutoBroadcastMessage(id=group, time_sec=60, message="fake", delivery_mode="player_message", recipient_group=group)
                 for group in ("vip", "non_vip")]
    monkeypatch.setattr(cd, "enter_session", Mock(side_effect=AssertionError("no eligible candidates")))
    assert cd.enqueue_eligible_deliveries(campaigns=campaigns,
        online_players={"fake": {"player_name": "fake", "is_vip": None}},
        active_sessions={"fake": {"player_db_id": 1, "session_id": 1, "start": now - timedelta(hours=1)}},
        server_number=1, player_count=1, seeding_config=None, now=now) == 0


def test_worker_recovers_again_even_when_campaigns_are_disabled(monkeypatch):
    start = datetime(2026, 1, 1, 12)
    class Clock(datetime):
        current = start
        @classmethod
        def utcnow(cls): return cls.current
    calls = []
    monkeypatch.setattr(cd, "datetime", Clock)
    monkeypatch.setattr(cd, "get_server_number", lambda: 1)
    monkeypatch.setattr(cd, "_recover_interrupted_deliveries", lambda server, now: calls.append(now))
    monkeypatch.setattr(cd, "expire_old_deliveries", Mock())
    monkeypatch.setattr(cd.AutoBroadcastUserConfig, "load_from_db", lambda: AutoBroadcastUserConfig(enabled=False))
    monkeypatch.setattr("rcon.rcon.get_rcon", lambda: Mock())
    monkeypatch.setattr("rcon.vip_lifecycle.feature_enabled", lambda: False)
    def wait(_event, _seconds):
        Clock.current += timedelta(seconds=31)
        return len(calls) >= 3
    monkeypatch.setattr(cd, "wait", wait)
    cd.run()
    assert calls == [start, start + timedelta(seconds=31), start + timedelta(seconds=62)]


def test_late_rejection_waits_for_concurrent_recovery_and_does_not_requeue(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "campaign_recovery_" + uuid4().hex
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.begin() as conn:
            conn.execute(text("""CREATE TABLE campaign_deliveries (id INTEGER PRIMARY KEY, server_number INTEGER,
                campaign_id TEXT, player_id_id INTEGER, player_session_id INTEGER, player_name TEXT, message TEXT,
                status TEXT, attempt_count INTEGER, eligible_at TIMESTAMP, next_attempt_at TIMESTAMP,
                created_at TIMESTAMP, updated_at TIMESTAMP, last_attempt_at TIMESTAMP, sent_at TIMESTAMP, last_error TEXT)"""))
            insert(conn, 1, "active", "sending", datetime(2026, 1, 1, 12))
        @contextmanager
        def session():
            with Session(engine) as actual, actual.begin():
                yield actual
        monkeypatch.setattr(cd, "enter_session", session)
        started = Event()
        def finish():
            started.set()
            cd.finish_delivery(1, success=False, now=datetime(2026, 1, 1, 12, 3), error="late rejection")
        with engine.connect() as connection, ThreadPoolExecutor(max_workers=1) as pool:
            tx = connection.begin()
            try:
                connection.execute(text("UPDATE campaign_deliveries SET status='failed' WHERE id=1"))
                future = pool.submit(finish)
                assert started.wait(3)
                with pytest.raises(FutureTimeout):
                    future.result(timeout=0.3)
                tx.commit()
            finally:
                if tx.is_active:
                    tx.rollback()
            future.result(timeout=5)
        with Session(engine) as session:
            row = session.get(CampaignDelivery, 1)
            assert row.status == "failed"
            assert row.next_attempt_at is None
    finally:
        engine.dispose()
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()
