"""Reservations must survive Redis expiry, crashes and concurrent workers."""
import os
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from threading import Barrier
from unittest.mock import Mock
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from rcon.automods import action_guard, automod
from rcon.automods.legacy_guard_bootstrap import bootstrap
from rcon.automods.models import ActionMethod, PunishDetails, PunishPlayer, PunishStepState, PunitionsToApply, WatchStatus
from rcon.automods.no_leader import NoLeaderAutomod
from rcon.user_config.auto_mod_no_leader import AutoModNoLeaderUserConfig


@pytest.fixture
def database(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "automod_guard_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"}, pool_size=8)
    action_guard.metadata.create_all(engine)
    action_guard.event_guard.metadata.create_all(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(action_guard, "get_session_maker", lambda: maker)
    monkeypatch.setattr(action_guard.event_guard, "get_session_maker", lambda: maker)
    try:
        yield maker
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def test_uncertain_result_blocks_same_rule_across_actions_and_restart(database):
    token = action_guard.reserve(3, "fake-console", ["no-leader"], "message")
    assert token
    # A new worker has no Redis watch but the committed reservation remains.
    assert action_guard.reserve(3, "fake-console", ["no-leader"], "message") is None
    assert action_guard.reserve(3, "fake-console", ["no-leader"], "punish") is None
    assert action_guard.reserve(4, "fake-console", ["no-leader"], "message")
    assert action_guard.reserve(3, "other-console", ["no-leader"], "message")
    assert action_guard.reserve(3, "fake-console", ["other-rule"], "message")


@pytest.mark.parametrize("result", ["confirmed", "rejected"])
def test_only_explicit_result_releases_reservation(database, result):
    token = action_guard.reserve(3, "fake-console", ["no-leader"], "message")
    assert action_guard.finish(4, "fake-console", token, result) == 0
    assert action_guard.finish(3, "fake-console", "wrong-token", result) == 0
    assert action_guard.reserve(3, "fake-console", ["no-leader"], "message") is None
    assert action_guard.finish(3, "fake-console", token, result) == 1
    assert action_guard.reserve(3, "fake-console", ["no-leader"], "message")


def test_operator_review_requires_reason_and_records_actor(database):
    token = action_guard.reserve(3, "fake-console", ["no-leader"], "message")
    with pytest.raises(ValueError):
        action_guard.review(3, "fake-console", token, "operator", " ")
    assert action_guard.review(4, "fake-console", token, "operator", "checked") == 0
    assert action_guard.review(3, "fake-console", token, " operator ", " checked logs ") == 1
    with database() as session:
        row = session.execute(select(action_guard.action_guard)).mappings().one()
        assert (row["state"], row["reviewed_by"], row["review_reason"]) == ("reviewed", "operator", "checked logs")
    assert action_guard.reserve(3, "fake-console", ["no-leader"], "message")
    with database() as session:
        audit = session.execute(select(action_guard.action_guard_history).where(
            action_guard.action_guard_history.c.token == token,
            action_guard.action_guard_history.c.event == "reviewed")).mappings().one()
        assert (audit["actor"], audit["reason"]) == ("operator", "checked logs")


def test_merged_rule_reservation_is_atomic(database):
    assert action_guard.reserve(3, "fake-console", ["rule-a"], "punish")
    assert action_guard.reserve(3, "fake-console", ["rule-a", "rule-b"], "punish") is None
    with database() as session:
        assert [row[0] for row in session.execute(select(action_guard.action_guard.c.rule))] == ["rule-a"]


def test_incomplete_group_confirmation_rolls_back_every_rule(database):
    token = action_guard.reserve(3, "fake-console", ["rule-a", "rule-b"], "punish")
    with pytest.raises(RuntimeError):
        action_guard.finish(3, "fake-console", token, "confirmed", expected=3)
    assert action_guard.reserve(3, "fake-console", ["rule-a"], "punish") is None
    assert action_guard.reserve(3, "fake-console", ["rule-b"], "punish") is None
    with database() as session:
        states = session.execute(select(action_guard.action_guard.c.state)).scalars().all()
        assert states == ["pending", "pending"]


def test_review_listing_keeps_merged_rules_together_and_is_server_scoped(database):
    first = action_guard.reserve(3, "fake-console", ["rule-a", "rule-b"], "punish")
    assert action_guard.reserve(3, "other-console", ["rule-c"], "message")
    assert action_guard.reserve(4, "fake-console", ["private-rule"], "message")
    listing = action_guard.list_pending(3, limit=1)
    assert listing["more"] is True
    assert listing["results"][0]["token"] == first
    assert {item["rule"] for item in listing["results"][0]["actions"]} == {"rule-a", "rule-b"}
    assert {item["actions"][0]["rule"] for item in action_guard.list_pending(4)["results"]} == {"private-rule"}


def test_legacy_global_hold_blocks_only_its_rule_and_server_until_reviewed(database):
    with pytest.raises(ValueError):
        action_guard.reserve(3, "*", ["no-leader"], "punish")
    token = action_guard.reserve(3, "*", ["no-leader"], "punish", legacy_global=True)
    assert token
    assert action_guard.reserve(3, "fake-console", ["no-leader"], "message") is None
    assert action_guard.reserve(3, "other-console", ["no-leader"], "kick") is None
    assert action_guard.reserve(3, "fake-console", ["seeding"], "message")
    assert action_guard.reserve(4, "fake-console", ["no-leader"], "message")
    assert action_guard.review(3, "*", token, "operator", "legacy watch examined") == 1
    assert action_guard.reserve(3, "fake-console", ["no-leader"], "message")


def test_bootstrap_is_idempotent_and_skips_simulation_rules(database):
    mods = [SimpleNamespace(action_author="no-leader", config=SimpleNamespace(dry_run=False)),
            SimpleNamespace(action_author="seeding", config=SimpleNamespace(dry_run=False)),
            SimpleNamespace(action_author="test-rule", config=SimpleNamespace(dry_run=True))]
    assert bootstrap(3, mods) == {"enabled_live_rules": 2, "new_holds": 2}
    assert bootstrap(3, mods) == {"enabled_live_rules": 2, "new_holds": 0}
    assert action_guard.reserve(3, "fake-console", ["no-leader"], "message") is None
    assert action_guard.reserve(3, "fake-console", ["seeding"], "punish") is None
    assert action_guard.reserve(3, "fake-console", ["test-rule"], "message")


@pytest.mark.parametrize("iteration", range(10))
def test_parallel_workers_can_reserve_only_once(database, iteration):
    barrier = Barrier(2)
    def invoke():
        barrier.wait(timeout=10)
        return action_guard.reserve(3, f"fake-console-{iteration}", ["no-leader"], "message")
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(invoke) for _ in range(2)]
        results = [future.result(timeout=20) for future in futures]
    assert sum(result is not None for result in results) == 1


def test_real_automod_path_blocks_repeat_after_redis_watch_expires(database, monkeypatch):
    state = [WatchStatus()]
    mod = NoLeaderAutomod(AutoModNoLeaderUserConfig(number_of_warnings=1, warning_interval_seconds=0), Mock())
    @contextmanager
    def watch(*_args):
        yield state[0]
    mod.watch_state = watch
    player = PunishPlayer(player_id="fake-console", name="Fake", team="allies", squad="Able", lvl=100,
                          role="rifleman", details=PunishDetails(author=mod.action_author, message="warning"))
    api = Mock()
    api.message_player.side_effect = TimeoutError("response lost")
    monkeypatch.setattr(automod, "get_server_number", lambda: "3")
    monkeypatch.setattr(automod, "audit", Mock())
    assert mod.should_warn_player(state[0], "Able", player) == PunishStepState.APPLY
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [mod])
    state[0] = WatchStatus()  # Redis key expired, but the database reservation survives.
    assert mod.should_warn_player(state[0], "Able", player) == PunishStepState.APPLY
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [mod])
    automod._do_punitions(api, ActionMethod.PUNISH, [player], [mod])
    api.message_player.assert_called_once()
    api.punish.assert_not_called()
    assert len(action_guard.list_pending(3)["results"]) == 1


@pytest.mark.parametrize("method,method_name", [(ActionMethod.MESSAGE, "message_player"),
                                                 (ActionMethod.PUNISH, "punish"),
                                                 (ActionMethod.KICK, "kick")])
@pytest.mark.parametrize("response", [True, False, None, "timeout"])
def test_real_automod_outcome_controls_durable_reservation(database, monkeypatch, method, method_name, response):
    player = PunishPlayer(player_id="fake-console", name="Fake", team="allies", squad="Able",
                          details=PunishDetails(author="rule", message="reason"))
    moderator = Mock()
    moderator.action_author = "rule"
    api = Mock()
    send = getattr(api, method_name)
    if response == "timeout":
        send.side_effect = TimeoutError("response lost")
    else:
        send.return_value = response
    monkeypatch.setattr(automod, "get_server_number", lambda: "3")
    monkeypatch.setattr(automod, "audit", Mock())
    automod._do_punitions(api, method, [player], [moderator])
    send.assert_called_once()
    pending = action_guard.list_pending(3)["results"]
    assert bool(pending) is (response is None or response == "timeout")
    assert (action_guard.reserve(3, "fake-console", ["rule"], method.name.lower()) is None) is bool(pending)


def test_real_automod_watch_failure_after_delivery_retains_reservation(database, monkeypatch):
    player = PunishPlayer(player_id="fake-console", name="Fake", team="allies", squad="Able",
                          details=PunishDetails(author="rule", message="warning"))
    moderator = Mock()
    moderator.action_author = "rule"
    moderator.player_warning_succeeded.side_effect = OSError("watch unavailable")
    api = Mock()
    api.message_player.return_value = True
    monkeypatch.setattr(automod, "get_server_number", lambda: "3")
    monkeypatch.setattr(automod, "audit", Mock())
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [moderator])
    assert action_guard.reserve(3, "fake-console", ["rule"], "message") is None
    api.message_player.assert_called_once()


def test_real_automod_path_fails_closed_when_database_is_unavailable(monkeypatch):
    api = Mock()
    player = PunishPlayer(player_id="fake-console", name="Fake", team="allies", squad="Able",
                          details=PunishDetails(author="rule", message="warning"))
    monkeypatch.setattr(automod, "get_server_number", lambda: "3")
    monkeypatch.setattr(action_guard, "reserve", Mock(side_effect=OSError("database unavailable")))
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [])
    api.message_player.assert_not_called()


def test_real_automod_retries_only_after_explicit_rejection(database, monkeypatch):
    state = WatchStatus()
    mod = NoLeaderAutomod(AutoModNoLeaderUserConfig(number_of_warnings=1, warning_interval_seconds=0), Mock())
    @contextmanager
    def watch(*_args):
        yield state
    mod.watch_state = watch
    player = PunishPlayer(player_id="fake-console", name="Fake", team="allies", squad="Able", lvl=100,
                          role="rifleman", details=PunishDetails(author=mod.action_author, message="warning"))
    api = Mock()
    api.message_player.side_effect = [False, True]
    monkeypatch.setattr(automod, "get_server_number", lambda: "3")
    monkeypatch.setattr(automod, "audit", Mock())
    assert mod.should_warn_player(state, "Able", player) == PunishStepState.APPLY
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [mod])
    assert mod.should_warn_player(state, "Able", player) == PunishStepState.APPLY
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [mod])
    assert api.message_player.call_count == 2
    assert mod.should_warn_player(state, "Able", player) == PunishStepState.GO_TO_NEXT_STEP
    assert action_guard.list_pending(3)["results"] == []


def test_real_automod_dry_run_does_not_depend_on_guard_database(monkeypatch):
    api = Mock()
    player = PunishPlayer(player_id="fake-console", name="Fake", team="allies", squad="Able",
                          details=PunishDetails(author="rule-DryRun", message="warning", dry_run=True))
    guard = Mock(side_effect=OSError("database unavailable"))
    monkeypatch.setattr(action_guard, "reserve", guard)
    monkeypatch.setattr(automod, "audit", Mock())
    automod._do_punitions(api, ActionMethod.MESSAGE, [player], [])
    guard.assert_not_called()
    api.message_player.assert_not_called()


@pytest.mark.parametrize("response", [True, False, None, "timeout"])
def test_connect_warning_preserves_uncertain_result_across_reconnect(database, monkeypatch, response):
    player = PunishPlayer(player_id="fake-console", name="Fake", team="allies", squad="Able",
                          details=PunishDetails(author="rule", message="warning"))
    api = Mock()
    if response == "timeout":
        api.message_player.side_effect = TimeoutError("response lost")
    else:
        api.message_player.return_value = response
    monkeypatch.setattr(automod, "get_server_number", lambda: "3")
    automod._send_connect_warning(api, player)
    automod._send_connect_warning(api, player)
    uncertain = response is None or response == "timeout"
    assert api.message_player.call_count == (1 if uncertain else 2)
    assert bool(action_guard.list_pending(3)["results"]) is uncertain


def test_connect_warning_fails_closed_when_database_unavailable(monkeypatch):
    player = PunishPlayer(player_id="fake-console", name="Fake", team="allies", squad="Able",
                          details=PunishDetails(author="rule", message="warning"))
    api = Mock()
    monkeypatch.setattr(automod, "get_server_number", lambda: "3")
    monkeypatch.setattr(action_guard, "reserve", Mock(side_effect=OSError("database unavailable")))
    automod._send_connect_warning(api, player)
    api.message_player.assert_not_called()


def test_connect_timer_reconnect_does_not_resend_uncertain_warning(database, monkeypatch):
    timers = []
    class FakeTimer:
        def __init__(self, _delay, callback):
            self.callback = callback
            timers.append(self)
        def start(self):
            pass
        def cancel(self):
            pass
    player = PunishPlayer(player_id="fake-console", name="Fake", team="allies", squad="Able",
                          details=PunishDetails(author="rule", message="warning"))
    mod = SimpleNamespace(on_connected=lambda *_: PunitionsToApply(warning=[player]))
    api = Mock()
    api.message_player.side_effect = TimeoutError("response lost")
    monkeypatch.setattr(automod, "Timer", FakeTimer)
    monkeypatch.setattr(automod, "get_server_number", lambda: "3")
    monkeypatch.setattr(automod, "get_redis_client", lambda: None)
    monkeypatch.setattr(automod, "is_first_run_done", lambda _: True)
    monkeypatch.setattr(automod, "enabled_moderators", lambda: [mod])
    try:
        for _ in range(2):
            automod.on_connected(api, {"player_name_1": "Fake", "player_id_1": "fake-console"})
            timers[-1].callback()
        api.message_player.assert_called_once()
        assert len(action_guard.list_pending(3)["results"]) == 1
    finally:
        automod.pendingTimers.pop("fake-console", None)
