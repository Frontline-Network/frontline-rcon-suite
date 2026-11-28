"""Exercise the adaptive lifecycle through its normal worker and preview entry points."""
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

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")

from rcon import vip_activity_messages as messages, vip_lifecycle as vip
from rcon.models import CampaignDelivery, LogLine, PlayerID, PlayerSession, PlayerVIP, VipLifecycleDelivery
from rcon.user_config.auto_broadcast import VipLifecycleConfig


BASE = datetime(2026, 10, 24, 17, tzinfo=timezone.utc)
PLAYER = "0002000000000000000000000000abcd"


@pytest.fixture(params=["sqlite", "postgres"])
def pilot(request, monkeypatch):
    pg = request.param == "postgres"
    url = os.getenv("RCON_SEARCH_TEST_DATABASE") if pg else "sqlite://"
    if not url:
        pytest.skip("requires isolated PostgreSQL")
    base = create_engine(url)
    schema = "vip_activity_" + uuid.uuid4().hex
    if pg:
        with base.begin() as conn:
            conn.execute(CreateSchema(schema))
    db = base.execution_options(schema_translate_map={None: schema}) if pg else base

    @contextmanager
    def session():
        with Session(db) as sess, sess.begin():
            yield sess

    try:
        for model in (PlayerID, PlayerSession, LogLine, PlayerVIP, CampaignDelivery, VipLifecycleDelivery):
            model.__table__.create(db)
        monkeypatch.setattr(vip, "enter_session", session)
        monkeypatch.setattr(vip, "_blocked_player_ids", lambda *_: set())
        monkeypatch.setattr(messages, "activity_window_open", lambda *_a, **_kw: True)
        monkeypatch.setattr(messages, "activity_message_allowed", lambda *_a, **_kw: True)
        monkeypatch.setattr(messages, "render_activity_message",
                            lambda **kw: "Reminder" if kw["reminder"] else "Invitation")
        monkeypatch.setattr(vip, "format_message", lambda _ctl, msg, **_: msg)
        monkeypatch.setenv("FRONTLINE_VIP_LIFECYCLE_ENABLED", "true")
        monkeypatch.setenv("HLL_GAME", "hllv")
        config = VipLifecycleConfig(enabled=True, activity_model=True)
        ctl = Mock()
        ctl.get_player_ids.return_value = [("Test", PLAYER)]
        ctl._native_vip_member_ids.return_value = set()
        ctl.message_player_info.return_value = True
        state = {"verified": False, "has_purchased_vip": False, "grant_source": "none",
                 "status_known": True, "vip_active": False}
        monkeypatch.setattr(vip, "fetch_statuses", lambda *_a, **_kw: {PLAYER: state.copy()})
        with session() as sess:
            player = PlayerID(player_id=PLAYER)
            sess.add(player)
            sess.flush()
            dbid = player.id
        yield Pilot(session, monkeypatch, ctl, config, dbid, state, pg)
    finally:
        if pg:
            with base.begin() as conn:
                conn.execute(DropSchema(schema, cascade=True))
        base.dispose()


class Pilot:
    def __init__(self, session, monkeypatch, ctl, config, dbid, state, pg):
        self.session, self.ctl, self.config, self.dbid = session, ctl, config, dbid
        self.state, self.pg = state, pg
        self.server, self.now = 3, BASE
        monkeypatch.setattr(vip, "get_server_number", lambda: self.server)
        monkeypatch.setattr(vip, "utc_now", lambda: self.now)

    def visit(self, when, minutes, *, server=3, game=2, exact=True, closed=False):
        if when > self.now:
            with self.session() as sess:
                for old in sess.query(PlayerSession).filter(PlayerSession.end.is_(None)):
                    old.end = self.now.replace(tzinfo=None)
                    old.end_event_us = int(self.now.timestamp() * 1_000_000)
        self.server = server
        self.now = when + timedelta(minutes=minutes)
        with self.session() as sess:
            start = when.replace(tzinfo=None)
            row = PlayerSession(player_id_id=self.dbid, server_number=server, created=start, start=start,
                                start_event_us=int(when.timestamp()*1_000_000) if exact else None)
            if closed:
                row.end = self.now.replace(tzinfo=None)
                row.end_event_us = int(self.now.timestamp()*1_000_000) if exact else None
            sess.add(row)
            sess.add(LogLine(player1_player_id=self.dbid, server=str(server), game=game,
                             event_time=start, type="CONNECTED", raw=f"{server}:{when}",
                             content="", weapon=""))
            sess.flush()
            return row.id

    def tick(self):
        return vip.process_once(self.ctl, self.config, player_message_gap_sec=0,
                                player_message_interval_sec=0, now=self.now)

    def preview(self):
        return vip.preview(self.ctl, self.config)["players"][0]


def test_first_repeat_backoff_and_dry_run(pilot):
    p = pilot
    p.visit(BASE, 44)
    assert not p.preview()["eligible"]
    p.now += timedelta(minutes=1)
    assert p.preview()["eligible"]
    p.config.test_mode = True
    assert p.tick()["simulated"] == 1
    p.config.test_mode = False
    assert p.tick()["sent"] == 1
    assert p.tick()["sent"] == 0
    p.visit(BASE + timedelta(days=14), 45, server=4)
    assert p.tick()["sent"] == 0   # only one distinct later play day
    p.visit(BASE + timedelta(days=15), 15)
    assert p.preview()["eligible"]
    assert p.tick()["sent"] == 1
    assert [c.args[1] for c in p.ctl.message_player_info.call_args_list] == ["Invitation", "Reminder"]
    p.visit(BASE + timedelta(days=31), 15)
    assert p.tick()["sent"] == 0
    p.visit(BASE + timedelta(days=75), 14)
    assert p.tick()["sent"] == 0
    p.now += timedelta(minutes=2)
    assert p.tick()["sent"] == 1
    with p.session() as sess:
        assert [r.message for r in sess.query(VipLifecycleDelivery)
                .filter_by(test_mode=False).order_by(VipLifecycleDelivery.id)] == ["Invitation", "Reminder", "Reminder"]


def test_legacy_dates_family_and_failed_protect(pilot):
    p = pilot
    p.visit(BASE, 15, exact=False, game=1, closed=True)
    p.visit(BASE + timedelta(days=1), 15)
    assert p.tick()["sent"] == 0   # wrong game history
    p.visit(BASE + timedelta(days=2), 15, exact=False)
    p.ctl.message_player_info.side_effect = TimeoutError("unknown")
    assert p.tick()["sent"] == 0
    p.ctl.message_player_info.side_effect = None
    p.visit(BASE + timedelta(days=3), 45, server=4)
    assert p.tick()["sent"] == 0
    with p.session() as sess:
        assert sess.query(VipLifecycleDelivery).one().status == "failed"


def test_native_vip_credit_stale_status_and_uncertain_roster(pilot, monkeypatch):
    p = pilot
    p.visit(BASE, 45)
    p.ctl._native_vip_member_ids.side_effect = TimeoutError()
    assert not p.preview()["eligible"]
    assert p.tick()["sent"] == 0
    p.ctl._native_vip_member_ids.side_effect = None
    p.ctl._native_vip_member_ids.return_value = {PLAYER.upper()}
    assert p.tick()["sent"] == 0
    p.ctl._native_vip_member_ids.return_value = set()
    with p.session() as sess:
        sess.add(PlayerVIP(player_id_id=p.dbid, server_number=3, expiration=p.now+timedelta(days=2)))
    assert not p.preview()["eligible"]
    p.visit(BASE + timedelta(days=3), 45)
    paid = dict(p.state, verified=True, grant_source="paid", vip_active=True, has_purchased_vip=True)
    monkeypatch.setattr(vip, "fetch_statuses", lambda *_a, **kw: {PLAYER: paid if kw.get("force") else p.state})
    assert p.tick()["sent"] == 0
    p.ctl.message_player_info.assert_not_called()


def test_trial_cap_and_legacy_grants(pilot):
    p = pilot
    p.visit(BASE, 45)
    assert p.tick()["sent"] == 1
    p.state.update(verified=True, grant_source="trial", vip_active=True, trial_id="grant",
                   expires_at=(p.now+timedelta(days=7)).isoformat())
    assert not p.preview()["eligible"]    # no generic active-trial notice
    p.visit(BASE + timedelta(days=6), 25)
    assert p.tick()["sent"] == 1
    p.state.update(trial_id="next", expires_at=(p.now+timedelta(hours=10)).isoformat())
    p.visit(BASE + timedelta(days=6, hours=2), 25, server=4)
    assert p.tick()["sent"] == 0           # two promotional contacts in 28 days
    p.state.update(trial_id="grant", vip_active=False)
    p.visit(BASE + timedelta(days=35), 25)
    assert p.tick()["sent"] == 0           # no second expiry notice for same grant


def test_parallel_claim_on_separate_servers(pilot):
    p = pilot
    if not p.pg:
        pytest.skip("requires PostgreSQL row locks")
    sessions = {server: p.visit(BASE, 45, server=server) for server in (3, 4)}
    barrier = Barrier(2)
    def claim(server):
        barrier.wait(timeout=10)
        return vip._prepare_delivery(player_db_id=p.dbid, player_session_id=sessions[server],
            player_name="Test", decision=vip.LifecycleDecision("unverified", "invitation"),
            campaign=p.config.campaigns.unverified, config=p.config, server_number=server,
            player_message_interval_sec=0, player_message_gap_sec=0, now=p.now,
            player_id=PLAYER, status=p.state, native=set(), rendered_message="Invite")
    with ThreadPoolExecutor(2) as executor:
        claimed = list(executor.map(claim, sessions))
    assert sum(key is not None for key in claimed) == 1


def test_quick_switches_do_not_reset_same_visit_across_rule_changes(pilot):
    p = pilot
    p.visit(BASE, 45)
    assert p.tick()["sent"] == 1
    p.state.update(verified=True, grant_source="trial", vip_active=True, trial_id="grant",
                   expires_at=(p.now+timedelta(days=1)).isoformat())
    p.visit(p.now + timedelta(minutes=1), 180, server=4)
    assert not p.preview()["eligible"]
    p.visit(p.now + timedelta(minutes=1), 60)
    assert p.tick()["sent"] == 0
    p.visit(p.now + timedelta(minutes=30), 15)
    assert p.tick()["sent"] == 1


def test_old_simulation_is_not_an_invitation_in_the_activity_pilot(pilot):
    p = pilot
    prior = p.visit(BASE, 15, closed=True)
    with p.session() as sess:
        sess.add(VipLifecycleDelivery(server_number=3, server_family="hll_vietnam", rule="unverified",
            player_id_id=p.dbid, player_session_id=prior, player_name="Test",
            status_fingerprint="v2:test:invitation", message="old test", status="simulated",
            test_mode=True, status_checked_at=p.now, created_at=p.now, updated_at=p.now))
    p.config.test_mode = True
    p.visit(BASE+timedelta(days=1), 15)
    assert p.preview()["eligible"]
    assert p.tick()["simulated"] == 1
    assert not p.preview()["eligible"]
    p.config.test_mode = False
    assert p.preview()["eligible"]
