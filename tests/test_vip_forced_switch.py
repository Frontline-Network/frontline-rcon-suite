"""Forced-switch marker behavior without contacting a game server."""
from types import SimpleNamespace
from unittest.mock import Mock
from contextlib import nullcontext
import os
import uuid

import fakeredis
import pytest
from redis import Redis

from rcon.commands import ServerCtl
from rcon.rcon import Rcon
from rcon.leadership_vote import storage
from rcon.vip_rewards import hooks


@pytest.fixture
def environment(monkeypatch):
    url = os.environ.get("RCON_FORCED_TEST_REDIS_URL")
    redis = Redis.from_url(url, decode_responses=True) if url else fakeredis.FakeStrictRedis(decode_responses=True)
    namespace = uuid.uuid4().hex
    events = []
    monkeypatch.setattr(hooks, "get_redis_client", lambda: redis)
    monkeypatch.setattr(hooks, "get_server_number", lambda: namespace)
    monkeypatch.setattr(hooks, "switch_state_lock", nullcontext)
    monkeypatch.setattr(hooks, "enqueue", events.append)
    monkeypatch.setattr(hooks.VipRewardsUserConfig, "load_from_db", lambda: SimpleNamespace(enabled=True, balance=SimpleNamespace(enabled=True)))
    monkeypatch.setattr(storage, "before_manual_action", Mock())
    return redis, events


def switch_log():
    return {"timestamp_ms": 1000, "player_id_1": "a", "sub_content": "allies > axis", "raw": "simulated"}


@pytest.mark.parametrize("on_death", [False, True])
def test_rejected_command_does_not_cancel_later_volunteer(environment, monkeypatch, on_death):
    redis, events = environment
    name = "switch_player_on_death" if on_death else "switch_player_now"
    monkeypatch.setattr(ServerCtl, name, Mock(return_value=False))
    rcon = object.__new__(Rcon)
    result = rcon.switch_player_on_death("a", "test") if on_death else rcon.switch_player_now("a")
    assert result is False
    assert redis.zcard(hooks.forced_pending_key("a")) == 0
    assert events == []
    hooks.switch(None, switch_log())
    assert events[-1]["forced"] is False


def test_rejecting_one_of_two_concurrent_markers_preserves_the_other(environment):
    redis, events = environment
    first = hooks.mark_forced("a", on_death=True)
    second = hooks.mark_forced("a")
    hooks.finish_forced("a", first, rejected=True)
    assert redis.zrange(hooks.forced_pending_key("a"), 0, -1) == [second[0]]
    hooks.switch(None, switch_log())
    assert events[-1]["forced"] is True


def test_uncertain_command_retains_marker_and_cancels_balance(environment, monkeypatch):
    redis, events = environment
    monkeypatch.setattr(ServerCtl, "switch_player_now", Mock(side_effect=TimeoutError("uncertain")))
    with pytest.raises(TimeoutError):
        object.__new__(Rcon).switch_player_now("a")
    assert redis.zcard(hooks.forced_pending_key("a")) == 1
    assert events[-1]["kind"] == "forced"


def test_success_records_forced_event_and_marks_the_next_team_change(environment, monkeypatch):
    redis, events = environment
    monkeypatch.setattr(ServerCtl, "switch_player_now", Mock(return_value=True))
    assert object.__new__(Rcon).switch_player_now("a") is True
    assert events[-1]["kind"] == "forced"
    hooks.switch(None, switch_log())
    assert events[-1]["forced"] is True
    assert redis.zcard(hooks.forced_pending_key("a")) == 0


def test_slow_command_event_is_fresh_but_keeps_its_original_start(environment, monkeypatch):
    _, events = environment
    marker = hooks.mark_forced("a")
    monkeypatch.setattr(hooks.time, "time", lambda: marker[1] + 90)
    hooks.finish_forced("a", marker)
    assert events[-1]["time"] == marker[1] + 90
    assert events[-1]["switch_started"] == marker[1]


def test_legacy_marker_is_honored_during_rolling_update(environment):
    redis, events = environment
    redis.setex(hooks.forced_key("a"), 120, "1")
    hooks.switch(None, switch_log())
    assert events[-1]["forced"] is True
    assert redis.get(hooks.forced_key("a")) is None


def test_bookkeeping_failure_does_not_hide_completed_command(environment, monkeypatch):
    monkeypatch.setattr(ServerCtl, "switch_player_now", Mock(return_value=True))
    monkeypatch.setattr(hooks, "finish_forced", Mock(side_effect=RuntimeError("unavailable")))
    assert object.__new__(Rcon).switch_player_now("a") is True


def test_ambiguous_concurrent_switch_logs_keep_both_markers(environment):
    redis, events = environment
    hooks.mark_forced("a")
    hooks.mark_forced("a")
    hooks.switch(None, switch_log())
    assert events[-1]["forced"] is True
    assert redis.zcard(hooks.forced_pending_key("a")) == 2


def test_log_arrives_before_command_response_keeps_inflight_protection(environment):
    redis, events = environment
    marker = hooks.mark_forced("a")
    hooks.switch(None, switch_log())
    assert redis.zcard(hooks.forced_pending_key("a")) == 0
    assert "a" in hooks.players_with_forced_switch(["a"], hooks.time.time())
    hooks.finish_forced("a", marker, rejected=True)
    assert not hooks.players_with_forced_switch(["a"], hooks.time.time())
    assert events[-1]["forced"] is True


def test_pending_forced_command_blocks_balance_claim(environment):
    from rcon.user_config.vip_rewards import VipRewardsUserConfig
    from rcon.vip_rewards.engine import Engine
    now = 1762700000
    counts, thresholds = {"allies": 24, "axis": 20}, {"allies": 20, "axis": 20}
    players = {"a": {"name": "Alice", "team": "allies"}, "b": {"name": "Bob", "team": "axis"}}
    cfg = VipRewardsUserConfig(enabled=True, pause_during_seeding=False, balance={"enabled": True, "minutes": 1})
    rewards = Engine({}, cfg)
    rewards.snapshot(now, players, counts, thresholds)
    rewards.event({"kind": "signup", "player_id": "a", "time": now + 1, "key": "signup", "allowed": True}, now + 1)
    change = {"kind": "switch", "player_id": "a", "source": "allies", "target": "axis", "time": now + 2, "key": "switch", "allowed": True}
    rewards.event(change, now + 2)
    players["a"] = {**players["a"], "team": "axis"}
    rewards.snapshot(now + 30, players, counts, thresholds)
    rewards.snapshot(now + 60, players, counts, thresholds)
    assert rewards.player("a").get("balance", {}).get("switched")
    hooks.mark_forced("a")
    blocked = hooks.players_with_forced_switch(["a"], now + 90)
    rewards.snapshot(now + 90, players, counts, thresholds, blocked_balances=blocked)
    assert not rewards.claims
