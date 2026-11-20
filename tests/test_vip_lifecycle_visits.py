"""Exercise invitation and expiry claims through the real campaign entry points."""
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timedelta, timezone
from threading import Barrier
from unittest.mock import Mock

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.schema import CreateSchema, DropSchema

from rcon import vip_lifecycle as vip
from rcon.models import CampaignDelivery, LogLine, PlayerID, PlayerSession, VipLifecycleDelivery
from rcon.user_config.auto_broadcast import VipLifecycleConfig


@pytest.fixture
def campaign_db(monkeypatch):
    url = os.environ.get("RCON_SEARCH_TEST_DATABASE")
    if not url:
        pytest.skip("requires isolated PostgreSQL")
    base = create_engine(url)
    schema = "vip_visit_" + uuid.uuid4().hex
    with base.begin() as conn:
        conn.execute(CreateSchema(schema))
    db = base.execution_options(schema_translate_map={None: schema})
    @contextmanager
    def session():
        with Session(db) as sess, sess.begin():
            yield sess
    try:
        for model in (PlayerID, PlayerSession, LogLine, CampaignDelivery, VipLifecycleDelivery):
            model.__table__.create(db)
        monkeypatch.setattr(vip, "enter_session", session)
        yield session
    finally:
        with base.begin() as conn:
            conn.execute(DropSchema(schema, cascade=True))
        base.dispose()


def test_family_visits_and_reminders_through_worker_and_preview(campaign_db, monkeypatch):
    cfg = VipLifecycleConfig(enabled=True)
    now = datetime(2026, 11, 19, tzinfo=timezone.utc)
    pid = "synthetic"
    server = 3
    ctl = Mock()
    ctl.get_player_ids.return_value = [("Pilot", pid)]
    ctl.message_player_info.return_value = True
    state = {"verified": False, "vip_active": False, "grant_source": "none",
             "status_known": True, "has_purchased_vip": False}
    monkeypatch.setattr(vip, "get_server_number", lambda: server)
    monkeypatch.setattr(vip, "utc_now", lambda: now)
    monkeypatch.setattr(vip, "_blocked_player_ids", lambda *_: set())
    monkeypatch.setattr(vip, "fetch_statuses", lambda *a, **k: {pid: state})
    monkeypatch.setattr(vip, "format_message", lambda ctl, message, **kwargs: message)
    monkeypatch.setenv("HLL_GAME", "hllv")
    monkeypatch.setenv("FRONTLINE_VIP_LIFECYCLE_ENABLED", "true")
    with campaign_db() as sess:
        player = PlayerID(player_id=pid, created=now.replace(tzinfo=None))
        sess.add(player)
        sess.flush()
        db_id = player.id

    def visit(number, start, end=None, game=2):
        with campaign_db() as sess:
            wall = start.replace(tzinfo=None)
            row = PlayerSession(player_id_id=db_id, server_number=number, start=wall,
                                created=wall, start_event_us=int(start.timestamp()*1_000_000))
            if end is not None:
                row.end = end.replace(tzinfo=None)
                row.end_event_us = int(end.timestamp()*1_000_000)
            sess.add(row)
            sess.add(LogLine(player1_player_id=db_id, server=str(number), game=game,
                             event_time=wall, type="CONNECTED", raw=f"{number}:{wall}",
                             content="", weapon=""))
            sess.flush()
            return row.id

    def close(row_id, end):
        with campaign_db() as sess:
            row = sess.get(PlayerSession, row_id)
            row.end = end.replace(tzinfo=None)
            row.end_event_us = int(end.timestamp()*1_000_000)

    def run():
        return vip.process_once(ctl, cfg, player_message_gap_sec=0, player_message_interval_sec=0, now=now)

    visit(4, now-timedelta(days=4), now-timedelta(days=3), game=1)
    first = visit(server, now-timedelta(minutes=10))
    assert not vip.preview(ctl, cfg)["players"][0]["eligible"]
    assert run()["sent"] == 0
    close(first, now)
    server = 5
    switched = visit(server, now+timedelta(minutes=1))
    now += timedelta(minutes=10)
    assert run()["sent"] == 0
    close(switched, now)
    # A string of short breaks is still a single visit.
    early = visit(server, now+timedelta(minutes=29))
    now += timedelta(minutes=39)
    assert run()["sent"] == 0
    close(early, now)
    server = 3
    current = visit(server, now+timedelta(minutes=30))
    now += timedelta(minutes=40)
    assert vip.preview(ctl, cfg)["players"][0]["eligible"]
    cfg.test_mode = True
    assert run()["simulated"] == 1
    cfg.test_mode = False
    assert run()["sent"] == 1
    close(current, now)
    server = 5
    visit(server, now+timedelta(seconds=20))
    now += timedelta(minutes=10)
    assert not vip.preview(ctl, cfg)["players"][0]["eligible"]
    assert run()["sent"] == 0
    state.update(verified=True, vip_active=True, grant_source="trial", trial_id="grant-a",
                 expires_at=(now+timedelta(hours=2)).isoformat())
    assert run()["sent"] == 1
    state["expires_at"] = (now+timedelta(hours=5)).isoformat()
    assert run()["sent"] == 0
    now += timedelta(hours=6)
    state["vip_active"] = False
    assert run()["sent"] == 0
    # A genuinely new grant on a later session has its own allowance.
    server = 3
    visit(server, now-timedelta(minutes=6))
    state.update(vip_active=True, trial_id="grant-b", expires_at=(now+timedelta(hours=2)).isoformat())
    assert run()["sent"] == 1
    assert ctl.message_player_info.call_count == 3


def test_parallel_family_claim_and_legacy_history(campaign_db):
    cfg = VipLifecycleConfig(enabled=True)
    now = datetime.now(timezone.utc)
    with campaign_db() as sess:
        p = PlayerID(player_id="concurrent", created=now.replace(tzinfo=None))
        sess.add(p)
        sess.flush()
        player = p.id
        sessions = {}
        for server in (3, 5):
            row = PlayerSession(player_id_id=player, server_number=server, created=now.replace(tzinfo=None))
            sess.add(row)
            sess.flush()
            sessions[server] = row.id
    barrier = Barrier(2)
    def claim(server):
        barrier.wait(timeout=10)
        return vip._prepare_delivery(player_db_id=player, player_session_id=sessions[server],
            player_name="test", decision=vip.LifecycleDecision(vip.RULE_TRIAL_EXPIRING, "single"),
            campaign=cfg.campaigns.trial_expiring, config=cfg, server_number=server,
            player_message_interval_sec=0, player_message_gap_sec=0, now=now)
    with ThreadPoolExecutor(2) as executor:
        ids = list(executor.map(claim, sessions))
    assert sum(i is not None for i in ids) == 1
    with campaign_db() as sess:
        row = sess.query(VipLifecycleDelivery).one()
        row.status_fingerprint = "f"*64
        row.status = "failed"
        sess.flush()
        attempts = vip._family_attempts(sess, [player], cfg)
        assert vip._already_attempted(attempts, player, vip.LifecycleDecision(vip.RULE_TRIAL_EXPIRED, "single"), False)
