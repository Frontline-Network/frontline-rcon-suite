"""Offline player journeys through the real queue, worker, policy and journal.

SQLite replaces PostgreSQL; process locks and the game/Redis boundaries are local
fakes. These tests do not claim to verify network protocol or concurrent workers.
"""

from contextlib import contextmanager, nullcontext
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
import json
import socket

import fakeredis
import pytest
from sqlalchemy import create_engine
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles
from sqlalchemy.orm import sessionmaker

from rcon.models import SeedVipGrant, VipRewardEvent, VipRewardGrant, VipRewardNotice, VipRewardState
from rcon.user_config.autobalancer import AutobalancerUserConfig
from rcon.user_config.seed_vip import SeedVIPUserConfig
from rcon.user_config.vip_rewards import VipRewardsUserConfig
from rcon.vip_rewards import hooks, service


@compiles(JSONB, "sqlite")
def jsonb_for_sqlite(type_, compiler, **kwargs):
    return "JSON"


START = datetime(2026, 11, 11, 12, tzinfo=timezone.utc).timestamp()


class TestServer:
    __test__ = False

    def __init__(self, game):
        self.config = SimpleNamespace(game=game)
        self.now = START
        self.round_id = "round-1"
        self.cfg = VipRewardsUserConfig(enabled=True, dry_run=False)
        self.players, self.vips, self.messages, self.writes = {}, {}, [], []
        self.healthy = True
        self.sequence = 0

    def player(self, name, team="allies", support=0):
        number = len(self.players) + 1
        pid = str(76561198000000000 + number) if self.config.game == "hll" else f"{number:032x}"
        self.players[pid] = dict(name=name, team=team, support=support)
        return pid

    def get_gamestate(self):
        return {
            "num_allied_players": sum(p["team"] == "allies" for p in self.players.values()),
            "num_axis_players": sum(p["team"] == "axis" for p in self.players.values()),
        }

    def get_detailed_players(self):
        return {"players": deepcopy(self.players), "fail_count": 0 if self.healthy else 1}

    def add_vip(self, **data):
        self.writes.append(deepcopy(data))
        self.vips[data["player_id"]] = {
            "player_id": data["player_id"], "name": data["description"],
            "vip_expiration": data["expiration"],
        }
        return True

    def message_player(self, **data):
        self.messages.append(deepcopy(data))
        return True

    def without_retries(self):
        return nullcontext()

    def tick(self, seconds=0):
        self.now += seconds
        service.tick(self)

    def advance(self, seconds):
        assert seconds % 30 == 0
        for _ in range(seconds // 30):
            self.tick(30)

    def event(self, kind, pid=None, **data):
        self.sequence += 1
        payload = dict(kind=kind, player_id=pid, time=self.now,
                       key=f"scenario:{self.sequence}", **data)
        service.enqueue(payload)
        return payload

    def rows(self):
        return service.journal(limit=100)["results"]

    def support(self, pid):
        return service.progress(pid).get("weekly_support", {}).get("points", 0)


@pytest.fixture(params=["hll", "hllv"])
def world(request, monkeypatch, tmp_path):
    def deny_network(*args, **kwargs):
        raise AssertionError("Offline VIP simulation attempted network access")

    monkeypatch.setattr(socket, "create_connection", deny_network)
    monkeypatch.setattr(socket.socket, "connect", deny_network)
    monkeypatch.setenv("SERVER_NUMBER", "99")
    db = create_engine("sqlite:///" + (tmp_path / "vip-simulation.sqlite").as_posix())
    for model in (VipRewardEvent, VipRewardGrant, VipRewardNotice, VipRewardState, SeedVipGrant):
        model.__table__.create(db)
    sessions = sessionmaker(db)

    @contextmanager
    def session():
        with sessions.begin() as value:
            yield value

    @contextmanager
    def local_lock(*args):
        yield

    server = TestServer(request.param)
    monkeypatch.setattr(service, "enter_session", session)
    monkeypatch.setattr(service, "get_session_maker", lambda: sessions)
    monkeypatch.setattr(service, "lock", local_lock)
    monkeypatch.setattr(service, "switch_state_lock", local_lock)
    monkeypatch.setattr(service, "vip_lock", local_lock)
    monkeypatch.setattr(hooks, "switch_state_lock", local_lock)
    monkeypatch.setattr(service, "server", lambda: 99)
    monkeypatch.setattr(service.time, "time", lambda: server.now)
    monkeypatch.setattr(service, "current_round", lambda: server.round_id)
    monkeypatch.setattr(service, "current_vip", lambda _, pid: deepcopy(server.vips.get(pid)))
    monkeypatch.setattr(VipRewardsUserConfig, "load_from_db", lambda: server.cfg)
    seed = SeedVIPUserConfig(enabled=False)
    seed.requirements.max_allies = seed.requirements.max_axis = 2
    monkeypatch.setattr(SeedVIPUserConfig, "load_from_db", lambda: seed)
    monkeypatch.setattr(AutobalancerUserConfig, "load_from_db", lambda: AutobalancerUserConfig())
    monkeypatch.setattr(service, "status_command_conflict", lambda _: False)
    redis = fakeredis.FakeStrictRedis(decode_responses=True)
    monkeypatch.setattr(hooks, "get_redis_client", lambda: redis)
    try:
        yield server
    finally:
        evidence = {
            "scenario": request.node.name,
            "game": server.config.game,
            "config": server.cfg.model_dump(mode="json"),
            "players": server.players,
            "journal": server.rows(),
            "vip_records": server.vips,
            "vip_writes": server.writes,
            "private_messages": server.messages,
        }
        (tmp_path / "evidence.json").write_text(
            json.dumps(evidence, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
        )
        db.dispose()


def test_support_across_rounds_reconnect_outage_and_next_week(world):
    w = world
    alice = w.player("Test-Alice", support=8000)
    excluded = w.player("Test-Excluded", "axis", 8000)
    w.cfg = VipRewardsUserConfig(enabled=True, dry_run=False,
        weekly_support={"enabled": True, "points": 5000, "hours": 6},
        excluded_player_ids=[excluded], status_command="!teamvip")
    w.tick()
    w.players[alice]["support"] = 12000
    w.advance(300)
    assert service.status()["status"] == "seeding"
    assert w.support(alice) == 0 and not w.writes
    w.player("Test-Ally")
    w.player("Test-Opponent", "axis")
    w.tick()
    w.advance(300)
    assert service.status()["status"] == "active"
    w.players[alice]["support"] += 2000
    w.players[excluded]["support"] += 20000
    w.tick(30)
    assert w.support(alice) == 2000 and w.support(excluded) == 0

    # A real persisted worker state survives the next round and next tick.
    w.event("round_end")
    w.tick()
    w.round_id = "round-2"
    w.players[alice]["support"] = 0
    w.tick(30)
    w.players[alice]["support"] = 1000
    w.tick(30)
    assert w.support(alice) == 3000
    player = w.players.pop(alice)
    w.event("disconnect", alice)
    w.tick()
    player["support"] = 2000
    w.players[alice] = player
    w.tick(30)
    w.advance(300)  # The population drop must be observed and released again.
    assert w.support(alice) == 3000
    w.healthy = False
    w.players[alice]["support"] = 3000
    w.tick(30)
    w.healthy = True
    w.players[alice]["support"] = 4000
    w.tick(30)
    w.advance(300)
    assert w.support(alice) == 3000

    hooks.reward_status(w, dict(sub_content="!teamvip", player_id_1=alice,
                               timestamp_ms=w.now * 1000))
    assert w.messages[-1]["player_id"] == alice
    assert "3000 / 5000" in w.messages[-1]["message"]
    w.messages.clear()
    w.vips[alice] = dict(player_id=alice, name="Existing member",
                        vip_expiration=datetime.fromtimestamp(w.now + 86400, timezone.utc))
    previous_expiry = w.vips[alice]["vip_expiration"].timestamp()
    w.players[alice]["support"] += 2000
    w.tick(30)
    assert len(w.writes) == len(w.messages) == 1
    assert w.messages[0]["player_id"] == alice and "+6 Stunden" in w.messages[0]["message"]
    assert service.expiration(w.vips[alice]["vip_expiration"]).timestamp() == previous_expiry + 6 * 3600
    assert w.vips[alice]["name"] == "Existing member"
    assert w.rows()[0]["status"] == "awarded"
    w.players[alice]["support"] += 5000
    w.tick(30)
    assert len(w.writes) == 1

    w.now = datetime(2026, 11, 16, 12, tzinfo=timezone.utc).timestamp()
    w.tick()
    w.advance(300)
    assert w.support(alice) == 0
    w.players[alice]["support"] += 5000
    w.tick(30)
    assert len(w.writes) == len(w.messages) == 2
    assert {row["trigger"] for row in w.rows()} == {"2026-11-09", "2026-11-16"}
    assert all(row["player_id"] == alice for row in w.rows())


def test_balance_requires_chat_signup_voluntary_switch_and_full_stay(world):
    w = world
    alice = w.player("Test-Volunteer")
    forced = w.player("Test-Forced")
    quitter = w.player("Test-Disconnect")
    unsigned = w.player("Test-No-Signup")
    for n in range(8):
        w.player(f"Test-Ally-{n}")
    for n in range(4):
        w.player(f"Test-Opponent-{n}", "axis")
    w.cfg = VipRewardsUserConfig(enabled=True, dry_run=False, pause_during_seeding=False,
        balance={"enabled": True, "minutes": 15, "difference": 2, "hours": 2})
    w.tick()
    for pid in (alice, forced, quitter):
        hooks.signup(w, dict(sub_content="!balance", player_id_1=pid,
            timestamp_ms=w.now * 1000, line_without_time=f"signup:{pid}"))
    w.tick()
    for pid in (alice, forced, quitter, unsigned):
        w.event("switch", pid, source="allies", target="axis", forced=(pid == forced))
        w.players[pid]["team"] = "axis"
    w.tick()
    w.advance(30)
    w.players.pop(quitter)
    w.event("disconnect", quitter)
    w.tick()
    w.advance(840)
    assert not w.writes
    w.tick(30)
    assert len(w.writes) == len(w.messages) == 1
    assert w.writes[0]["player_id"] == alice
    assert w.rows()[0]["rule"] == "balance"
    w.advance(60)
    assert len(w.writes) == 1


def test_pending_rejected_forced_switch_pauses_then_resumes_balance_reward(world):
    w = world
    alice = w.player("Test-Volunteer")
    for n in range(8):
        w.player(f"Test-Ally-{n}")
    for n in range(4):
        w.player(f"Test-Opponent-{n}", "axis")
    w.cfg = VipRewardsUserConfig(enabled=True, dry_run=False, pause_during_seeding=False,
        balance={"enabled": True, "minutes": 1, "difference": 2, "hours": 2})
    w.tick()
    w.event("signup", alice)
    w.tick()
    w.event("switch", alice, source="allies", target="axis", forced=False)
    w.players[alice]["team"] = "axis"
    w.tick()
    w.advance(30)
    marker = hooks.mark_forced(alice)
    w.advance(90)
    assert not w.writes
    hooks.finish_forced(alice, marker, rejected=True)
    w.advance(60)
    assert len(w.writes) == 1 and w.writes[0]["player_id"] == alice


def test_unavailable_marker_store_cannot_credit_balance(world, monkeypatch):
    w = world
    alice = w.player("Test-Volunteer")
    for n in range(8):
        w.player(f"Test-Ally-{n}")
    for n in range(4):
        w.player(f"Test-Opponent-{n}", "axis")
    w.cfg = VipRewardsUserConfig(enabled=True, dry_run=False, pause_during_seeding=False,
        balance={"enabled": True, "minutes": 1, "difference": 2, "hours": 2})
    w.tick()
    w.event("signup", alice)
    w.tick()
    w.event("switch", alice, source="allies", target="axis", forced=False)
    w.players[alice]["team"] = "axis"
    w.tick()
    w.advance(30)
    with monkeypatch.context() as isolated:
        def unavailable():
            raise ConnectionError("marker store unavailable")
        isolated.setattr(hooks, "get_redis_client", unavailable)
        with pytest.raises(ConnectionError, match="marker store unavailable"):
            w.tick(30)
    assert not w.writes
    w.advance(60)
    assert len(w.writes) == 1 and w.writes[0]["player_id"] == alice


def test_backlogged_forced_event_blocks_premature_balance_reward(world):
    w = world
    alice = w.player("Test-Volunteer")
    for n in range(8):
        w.player(f"Test-Ally-{n}")
    for n in range(4):
        w.player(f"Test-Opponent-{n}", "axis")
    w.cfg = VipRewardsUserConfig(enabled=True, dry_run=False, pause_during_seeding=False,
        balance={"enabled": True, "minutes": 1, "difference": 2, "hours": 2})
    w.tick()
    w.event("signup", alice)
    w.tick()
    w.event("switch", alice, source="allies", target="axis", forced=False)
    w.players[alice]["team"] = "axis"
    w.tick()
    w.advance(30)
    assert not w.writes
    with service.enter_session() as session:
        session.add_all([VipRewardEvent(server_number=99, preview=False, key=f"backlog-{n}", processed=False,
            payload={"kind": "kill", "player_id": alice, "time": w.now, "key": f"backlog-{n}", "allowed": False})
            for n in range(5000)])
    w.event("forced", alice)
    w.tick(30)
    assert not w.writes
    w.tick(30)
    assert not w.writes


@pytest.mark.parametrize("preview", [False, True])
def test_full_hour_all_activity_rules_journal_and_preview(world, preview):
    w = world
    alice = w.player("Test-Regular")
    victim = w.player("Test-Opponent", "axis")
    excluded = w.player("Test-Excluded")
    w.cfg = VipRewardsUserConfig(enabled=True, dry_run=preview, pause_during_seeding=False,
        excluded_player_ids=[excluded],
        melee={"enabled": True, "hours": 2, "limit": 1},
        round={"enabled": True, "minutes": 30, "fraction": 0.7, "hours": 2},
        weekly={"enabled": True, "days": 1, "minutes": 30, "hours": 6},
        milestones={"enabled": True, "milestones": [{"play_hours": 1, "hours": 4}]},
        events=[dict(id="community", name="Community", enabled=True, minutes=30, hours=4,
            start=datetime.fromtimestamp(START, timezone.utc),
            end=datetime.fromtimestamp(START + 7200, timezone.utc))],
        challenges=[dict(id="knife", name="Knife", enabled=True, weapons=["M3 KNIFE"], kills=2, hours=2)])
    w.tick()
    first = w.event("kill", alice, victim=victim, weapon="M3 KNIFE")
    service.enqueue(first)  # Duplicate log delivery must not produce extra VIP.
    w.event("kill", excluded, victim=victim, weapon="M3 KNIFE")
    w.tick()
    w.advance(1800)
    w.event("kill", alice, victim=victim, weapon="M3 KNIFE")
    w.tick()
    w.advance(1500)
    late = w.player("Test-Late-Joiner")
    w.tick()
    w.advance(300)
    w.event("round_end")
    w.tick()
    rows = [r for r in w.rows() if r["player_id"] == alice]
    credited = [r for r in rows if r["status"] == ("preview" if preview else "awarded")]
    assert {r["rule"] for r in credited} == {"melee", "round", "weekly", "milestones", "event:community", "challenge:knife"}
    assert sum(r["credited_seconds"] for r in credited) == 20 * 3600
    assert any(r["reason"] == "rule_limit" for r in rows)
    assert not any(r["player_id"] in (excluded, late) for r in w.rows())
    writes_before = len(w.writes)
    w.tick()
    assert len(w.writes) == writes_before
    if preview:
        assert not w.writes and not w.messages
    else:
        alice_writes = [r for r in w.writes if r["player_id"] == alice]
        alice_messages = [r for r in w.messages if r["player_id"] == alice]
        assert len(alice_writes) == len(alice_messages) == 6
        assert service.expiration(w.vips[alice]["vip_expiration"]).timestamp() == START + 20 * 3600
