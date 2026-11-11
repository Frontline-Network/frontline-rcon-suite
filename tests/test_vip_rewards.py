"""Offline policy and durable delivery tests. No game server is contacted."""

import copy
from contextlib import contextmanager
from datetime import datetime, timezone
from unittest.mock import Mock

import pytest
from pydantic import ValidationError

from rcon.user_config.vip_rewards import VipRewardsUserConfig
from rcon.vip_rewards.engine import Engine, budget, day_segments, gate, periods

NOW = datetime(2026, 11, 9, 12, tzinfo=timezone.utc).timestamp()
PLAYERS = {
    "a": {"name": "Alice", "team": "allies"},
    "b": {"name": "Bob", "team": "axis"},
}
COUNTS = {"allies": 24, "axis": 20}
THRESHOLDS = {"allies": 20, "axis": 20}


def config(**kwargs):
    return VipRewardsUserConfig(enabled=True, pause_during_seeding=False, **kwargs)


def engine(cfg=None):
    e = Engine({}, cfg or config())
    e.snapshot(NOW, PLAYERS, COUNTS, THRESHOLDS)
    return e


def event(kind="kill", **kwargs):
    return dict(
        kind=kind,
        player_id="a",
        victim="b",
        weapon="M3 KNIFE",
        time=NOW + 1,
        key="event-1",
        allowed=True,
        **kwargs
    )


def test_safe_defaults_and_validation():
    cfg = VipRewardsUserConfig()
    assert not cfg.enabled and cfg.dry_run and cfg.pause_during_seeding
    assert not any(
        getattr(cfg, k).enabled
        for k in ("melee", "round", "weekly", "balance", "milestones")
    )
    for values in (
        {"daily_hours": 0},
        {"timezone": "No/SuchZone"},
        {"unknown": True},
        {"challenges": [{"id": "x", "name": "X", "weapons": [""], "period": "fixed"}]},
    ):
        with pytest.raises(ValidationError):
            VipRewardsUserConfig(**values)


def test_seeding_gate_requires_continuous_five_minutes_and_blocks_on_drop():
    e = engine(VipRewardsUserConfig(enabled=True))
    for seconds in range(30, 300, 30):
        e.snapshot(NOW + seconds, PLAYERS, COUNTS, THRESHOLDS)
        assert gate(e.s, e.c, NOW + seconds) == "seeding"
    e.snapshot(NOW + 300, PLAYERS, COUNTS, THRESHOLDS)
    assert gate(e.s, e.c, NOW + 300) == "active"
    e.snapshot(NOW + 330, PLAYERS, {"allies": 19, "axis": 20}, THRESHOLDS)
    assert gate(e.s, e.c, NOW + 330) == "seeding"
    e.snapshot(NOW + 360, PLAYERS, COUNTS, THRESHOLDS)
    assert gate(e.s, e.c, NOW + 360) == "seeding"


def test_stale_status_and_snapshot_failure_fail_closed_even_without_seeding_gate():
    e = engine()
    assert gate(e.s, e.c, NOW + 61) == "unknown"
    e.snapshot(NOW + 90, PLAYERS, COUNTS, THRESHOLDS, healthy=False)
    assert gate(e.s, e.c, NOW + 90) == "unknown"


def test_paused_kills_and_time_never_accumulate():
    cfg = VipRewardsUserConfig(
        enabled=True, melee={"enabled": True}, milestones={"enabled": True}
    )
    e = engine(cfg)
    e.event(event(), NOW + 1)
    e.snapshot(NOW + 30, PLAYERS, COUNTS, THRESHOLDS)
    assert not e.claims
    assert not e.s["players"]


@pytest.mark.parametrize(
    "name",
    ["M3 KNIFE", "FELDSPATEN", "Fairbairn–Sykes", "Fairbairn_Sykes", "MPL-50 SPADE"],
)
def test_melee_aliases(name):
    e = engine(config(melee={"enabled": True}))
    kill = event()
    kill["weapon"] = name
    e.event(kill, NOW + 1)
    assert len(e.claims) == 1


def test_opponent_guard_shared_between_melee_and_challenges():
    e = engine(
        config(
            melee={"enabled": True},
            challenges=[
                dict(
                    id="knife",
                    name="Knife",
                    enabled=True,
                    weapons=["M3 KNIFE"],
                    kills=1,
                )
            ],
        )
    )
    e.event(event(), NOW + 1)
    assert len(e.claims) == 2
    second = event()
    second.update(key="event-2", time=NOW + 2)
    e.event(second, NOW + 2)
    assert len(e.claims) == 2


def test_selfkill_exclusion_and_stale_event():
    for changes in (
        {"victim": "a"},
        {"victim": None},
        {"allowed": False},
        {"time": NOW - 120},
    ):
        e = engine(config(melee={"enabled": True}))
        kill = event()
        kill.update(changes)
        e.event(kill, NOW + 1)
        assert not e.claims
    cfg = config(melee={"enabled": True})
    cfg.excluded_player_ids = ["a"]
    e = engine(cfg)
    e.event(event(), NOW + 1)
    assert not e.claims


def test_time_requires_two_confirmed_snapshots_no_outage_credit():
    e = engine(config(milestones={"enabled": True}))
    e.snapshot(NOW + 30, PLAYERS, COUNTS, THRESHOLDS)
    assert e.player("a")["total"] == 30
    e.snapshot(NOW + 200, PLAYERS, COUNTS, THRESHOLDS)
    assert e.player("a")["total"] == 30
    e.snapshot(NOW + 230, PLAYERS, COUNTS, THRESHOLDS)
    assert e.player("a")["total"] == 60


def test_config_change_does_not_credit_previous_interval():
    e = engine(config(milestones={"enabled": False}))
    e = Engine(e.s, config(milestones={"enabled": True}))
    e.snapshot(NOW + 30, PLAYERS, COUNTS, THRESHOLDS)
    assert e.player("a")["total"] == 0


def test_round_presence_fraction_and_idempotency():
    e = engine(config(round={"enabled": True, "minutes": 1}))
    for seconds in (30, 60):
        e.snapshot(NOW + seconds, PLAYERS, COUNTS, THRESHOLDS)
    end = event("round_end")
    end["time"] = NOW + 61
    e.event(end, NOW + 61)
    assert {c["player_id"] for c in e.claims} == {"a", "b"}
    e.event(end, NOW + 61)
    assert len(e.claims) == 2


def test_round_ending_while_paused_does_not_award():
    e = engine(config(round={"enabled": True, "minutes": 1}))
    e.player("a")["round"] = 1800
    e.s["round_seconds"] = 1800
    e.s["healthy"] = False
    e.event(event("round_end"), NOW + 1)
    assert not e.claims and e.player("a")["round"] == 0


def test_weekly_and_milestone_once_after_restart():
    cfg = config(
        weekly={"enabled": True, "days": 1, "minutes": 1},
        milestones={"enabled": True, "milestones": [{"play_hours": 1, "hours": 4}]},
    )
    e = engine(cfg)
    e.player("a")["total"] = 3570
    for seconds in (30, 60):
        e.snapshot(NOW + seconds, PLAYERS, COUNTS, THRESHOLDS)
    assert len([c for c in e.claims if c["player_id"] == "a"]) == 2
    e = Engine(copy.deepcopy(e.s), cfg)
    e.snapshot(NOW + 90, PLAYERS, COUNTS, THRESHOLDS)
    assert not e.claims


def test_event_window_only_counts_overlap():
    cfg = config(
        events=[
            dict(
                id="event",
                name="Event",
                enabled=True,
                start=datetime.fromtimestamp(NOW + 15, timezone.utc),
                end=datetime.fromtimestamp(NOW + 600, timezone.utc),
                minutes=1,
            )
        ]
    )
    e = engine(cfg)
    for seconds in (30, 60, 90):
        e.snapshot(NOW + seconds, PLAYERS, COUNTS, THRESHOLDS)
    assert e.player("a")["events"]["event"] == 75
    assert len(e.claims) == 2


def test_balance_requires_signup_switch_and_stay():
    e = engine(config(balance={"enabled": True, "minutes": 1}))
    e.event(event("signup"), NOW + 1)
    switch = event("switch")
    switch.update(source="allies", target="axis", time=NOW + 2)
    e.event(switch, NOW + 2)
    changed = copy.deepcopy(PLAYERS)
    changed["a"]["team"] = "axis"
    for seconds in (30, 60, 90):
        e.snapshot(NOW + seconds, changed, COUNTS, THRESHOLDS)
    assert len(e.claims) == 1 and e.claims[0]["rule"] == "balance"


@pytest.mark.parametrize("kind", ["forced", "disconnect"])
def test_balance_cancelled_by_forced_switch_or_disconnect(kind):
    e = engine(config(balance={"enabled": True}))
    e.event(event("signup"), NOW + 1)
    assert e.player("a").get("balance")
    e.event(event(kind), NOW + 2)
    assert not e.player("a").get("balance")


def test_snapshot_only_switch_is_not_rewarded():
    e = engine(config(balance={"enabled": True}))
    e.event(event("signup"), NOW + 1)
    changed = copy.deepcopy(PLAYERS)
    changed["a"]["team"] = "axis"
    e.snapshot(NOW + 30, changed, COUNTS, THRESHOLDS)
    assert not e.player("a").get("balance")


def test_dst_midnight_split_and_monday_week():
    start = datetime(2026, 10, 24, 22, tzinfo=timezone.utc).timestamp()
    end = datetime(2026, 10, 25, 23, tzinfo=timezone.utc).timestamp()
    assert list(day_segments(start, end, "Europe/Berlin")) == [
        ("2026-10-25", 25 * 3600)
    ]
    assert periods(NOW, "Europe/Berlin") == ("2026-11-09", "2026-11-09")


def test_budget_partial_and_exhausted():
    assert budget(7200, 23 * 3600, 24 * 3600) == 3600
    assert budget(7200, 24 * 3600, 24 * 3600) == 0


@pytest.fixture
def delivery(monkeypatch):
    """Real SQLAlchemy journal transactions with an offline SQLite database."""
    from sqlalchemy import create_engine
    from sqlalchemy.orm import sessionmaker
    from sqlalchemy.ext.compiler import compiles
    from sqlalchemy.dialects.postgresql import JSONB
    from rcon.models import VipRewardGrant, VipRewardState, VipRewardEvent
    from rcon.vip_rewards import service

    @compiles(JSONB, "sqlite")
    def jsonb_sqlite(type_, compiler, **kwargs):
        return "JSON"

    db = create_engine("sqlite://")
    for table in (
        VipRewardGrant.__table__,
        VipRewardState.__table__,
        VipRewardEvent.__table__,
    ):
        table.create(db)
    factory = sessionmaker(db)

    @contextmanager
    def session():
        with factory.begin() as s:
            yield s

    @contextmanager
    def no_lock(*args):
        yield

    cfg = config(dry_run=False, melee={"enabled": True, "limit": 3})
    e = engine(cfg)
    monkeypatch.setattr(service, "enter_session", session)
    monkeypatch.setattr(service, "vip_lock", no_lock)
    monkeypatch.setattr(service, "lock", no_lock)
    monkeypatch.setattr(service, "server", lambda: 1)
    monkeypatch.setattr(service.VipRewardsUserConfig, "load_from_db", lambda: cfg)
    monkeypatch.setattr(service.time, "time", lambda: NOW)
    monkeypatch.setattr(
        service, "_test_read_gate", service.read_gate_state, raising=False
    )
    monkeypatch.setattr(service, "read_state", lambda _: e.s)
    monkeypatch.setattr(service, "read_gate_state", lambda _: e.s)
    remote = {"vip": None}
    monkeypatch.setattr(service, "current_vip", lambda rcon, pid: remote["vip"])
    rcon = Mock()

    def write(**kwargs):
        remote["vip"] = dict(
            player_id=kwargs["player_id"],
            name=kwargs["description"],
            vip_expiration=kwargs["expiration"],
        )
        return True

    rcon.add_vip.side_effect = write

    def add(key="one", hours=2, preview=False, occurred=NOW):
        with session() as s:
            row = VipRewardGrant(
                server_number=1,
                preview=preview,
                player_id="a",
                rule="melee",
                trigger=key,
                occurred=occurred,
                requested_seconds=hours * 3600,
                credited_seconds=0,
                limit=3,
                status="queued",
                reason="",
                description="",
            )
            s.add(row)
            s.flush()
            return row.id

    def read_row(id_):
        with session() as s:
            return s.get(VipRewardGrant, id_).to_dict()

    yield service, cfg, rcon, remote, add, read_row
    db.dispose()


def test_delivery_exactly_once_and_preserves_description(delivery):
    service, cfg, rcon, remote, add, read = delivery
    remote["vip"] = dict(
        player_id="a",
        name="Existing name",
        vip_expiration=datetime.fromtimestamp(NOW + 86400, timezone.utc),
    )
    id_ = add()
    service.deliver(rcon, id_)
    service.deliver(rcon, id_)
    assert rcon.add_vip.call_count == 1
    assert read(id_)["status"] == "awarded"
    assert rcon.add_vip.call_args.kwargs["description"] == "Existing name"
    assert datetime.fromisoformat(read(id_)["target"]).timestamp() == NOW + 86400 + 7200


def test_timeout_after_success_reconciles_without_second_write(delivery):
    service, cfg, rcon, remote, add, read = delivery
    write = rcon.add_vip.side_effect

    def timeout(**kwargs):
        write(**kwargs)
        raise TimeoutError()

    rcon.add_vip.side_effect = timeout
    id_ = add()
    service.deliver(rcon, id_)
    assert read(id_)["status"] == "prepared"
    service.deliver(rcon, id_)
    assert read(id_)["status"] == "awarded" and rcon.add_vip.call_count == 1


def test_uncertain_write_blocks_further_rewards(delivery):
    service, cfg, rcon, remote, add, read = delivery
    rcon.add_vip.side_effect = TimeoutError()
    id_ = add()
    service.deliver(rcon, id_)
    service.deliver(rcon, id_)
    assert read(id_)["status"] == "review"
    second = add("two")
    service.deliver(rcon, second)
    assert read(second)["reason"] == "previous_write_needs_review"
    assert rcon.add_vip.call_count == 1


def test_shared_budget_partial_and_exhaustion(delivery):
    service, cfg, rcon, remote, add, read = delivery
    first = add(hours=23)
    second = add("two")
    third = add("three")
    for id_ in (first, second, third):
        service.deliver(rcon, id_)
    assert read(second)["credited_seconds"] == 3600
    assert read(second)["reason"] == "partial_budget"
    assert read(third)["status"] == "skipped" and rcon.add_vip.call_count == 2


def test_preview_and_permanent_vip_do_not_write(delivery):
    service, cfg, rcon, remote, add, read = delivery
    cfg.dry_run = True
    service.read_gate_state(True)["config"] = cfg.model_dump_json()
    id_ = add(preview=True)
    service.deliver(rcon, id_)
    assert read(id_)["status"] == "preview"
    assert not rcon.add_vip.called and not rcon.message_player.called
    cfg.dry_run = False
    service.read_gate_state(False)["config"] = cfg.model_dump_json()
    remote["vip"] = dict(player_id="a", name="Permanent", vip_expiration=None)
    second = add("two")
    service.deliver(rcon, second)
    assert read(second)["reason"] == "permanent_vip" and not rcon.add_vip.called


def test_message_failure_does_not_repeat_vip(delivery):
    service, cfg, rcon, remote, add, read = delivery
    rcon.message_player.side_effect = TimeoutError()
    id_ = add()
    service.deliver(rcon, id_)
    service.deliver(rcon, id_)
    assert rcon.add_vip.call_count == 1 and read(id_)["status"] == "awarded"


def test_durable_queue_tick_duplicate_and_restart(delivery, monkeypatch):
    from rcon.models import VipRewardEvent, VipRewardGrant
    from rcon.user_config.seed_vip import SeedVIPUserConfig

    service, cfg, rcon, remote, add, read = delivery
    monkeypatch.setattr(service, "read_gate_state", service._test_read_gate)
    monkeypatch.setattr(service, "observe", lambda *_: (PLAYERS, COUNTS, True))
    monkeypatch.setattr(
        service.SeedVIPUserConfig, "load_from_db", lambda: SeedVIPUserConfig()
    )
    service.tick(rcon)
    payload = event()
    payload["time"] = NOW
    service.enqueue(payload)
    service.enqueue(payload)
    service.tick(rcon)
    service.tick(rcon)
    with service.enter_session() as session:
        assert session.query(VipRewardEvent).count() == 1
        assert session.query(VipRewardGrant).count() == 1
        assert session.query(VipRewardGrant).one().status == "awarded"
    assert rcon.add_vip.call_count == 1


def test_expired_budget_and_rule_limit(delivery, monkeypatch):
    service, cfg, rcon, remote, add, read = delivery
    first = add(hours=24)
    service.deliver(rcon, first)
    monkeypatch.setattr(service.time, "time", lambda: NOW + 86401)
    monkeypatch.setattr(
        service, "read_gate_state", lambda _: {"observed": NOW + 86401, "healthy": True}
    )
    second = add("two")
    service.deliver(rcon, second)
    assert read(second)["credited_seconds"] == 7200


def test_unknown_readback_keeps_budget_reserved(delivery):
    service, cfg, rcon, remote, add, read = delivery
    rcon.add_vip.side_effect = None
    rcon.add_vip.return_value = False
    id_ = add()
    service.deliver(rcon, id_)
    assert read(id_)["status"] == "review"
    assert read(id_)["credited_seconds"] == 7200


def test_event_dates_save_as_json_and_validation_does_not_write(monkeypatch):
    import json
    from rcon.user_config import vip_rewards

    save = Mock()
    monkeypatch.setattr(vip_rewards, "set_user_config", save)
    monkeypatch.setattr(vip_rewards.VipRewardsUserConfig, "KEY", lambda: "test")
    data = dict(
        events=[
            dict(
                id="e",
                name="Event",
                start="2026-11-09T12:00:00Z",
                end="2026-11-10T12:00:00Z",
            )
        ]
    )
    VipRewardsUserConfig.save_to_db(data, dry_run=True)
    assert not save.called
    VipRewardsUserConfig.save_to_db(data)
    assert "2026-11-09" in json.dumps(save.call_args.args[1])


def test_shared_lock_is_reentrant_and_always_released(monkeypatch):
    from rcon.vip_rewards.locking import lock
    from rcon import models

    connection = Mock()
    context = Mock()
    context.__enter__ = Mock(return_value=connection)
    context.__exit__ = Mock(return_value=False)
    db = Mock()
    db.connect.return_value = context
    monkeypatch.setattr(models, "get_engine", lambda: db)
    with pytest.raises(RuntimeError):
        with lock("test"):
            with lock("test"):
                raise RuntimeError("failure")
    assert db.connect.call_count == 1
    assert "pg_try_advisory_lock" in str(connection.execute.call_args_list[0].args[0])
    assert "pg_advisory_unlock" in str(connection.execute.call_args_list[1].args[0])


@pytest.mark.parametrize("cumulative", [True, False])
def test_seed_vip_refreshes_expiration_under_shared_lock(monkeypatch, cumulative):
    from collections import defaultdict
    from rcon.seed_vip.utils import reward_players
    from rcon.user_config.seed_vip import SeedVIPUserConfig
    from rcon.vip_rewards import locking, service

    held = []

    @contextmanager
    def player_lock(pid):
        held.append(pid)
        try:
            yield
        finally:
            held.pop()

    current = datetime.fromtimestamp(NOW + 3 * 86400, timezone.utc)

    def current_vip(*args):
        assert held == ["a"]
        return dict(player_id="a", name="Existing", vip_expiration=current)

    monkeypatch.setattr(locking, "vip_lock", player_lock)
    monkeypatch.setattr(service, "current_vip", current_vip)
    cfg = SeedVIPUserConfig(
        dry_run=False, reward={"cumulative": cumulative, "timeframe": {"days": 1}}
    )
    rcon = Mock()

    def write(**kwargs):
        assert held == ["a"]
        expected = current.timestamp() + (86400 if cumulative else 0)
        assert datetime.fromisoformat(kwargs["expiration"]).timestamp() == expected
        return True

    rcon.add_vip.side_effect = write
    times = defaultdict(lambda: datetime.fromtimestamp(NOW + 86400, timezone.utc))
    reward_players(
        rcon,
        cfg,
        {"a"},
        {},
        {"a": "Alice"},
        times,
        reward_time=datetime.fromtimestamp(NOW, timezone.utc),
    )
    assert rcon.add_vip.call_count == 1


def test_review_acknowledgement_does_not_replay_or_refund(delivery):
    service, cfg, rcon, remote, add, read = delivery
    rcon.add_vip.side_effect = TimeoutError()
    id_ = add()
    service.deliver(rcon, id_)
    service.deliver(rcon, id_)
    assert service.acknowledge_review(id_, "Test admin") is True
    assert read(id_)["status"] == "reviewed" and read(id_)["credited_seconds"] == 7200
    assert "Test admin" in read(id_)["reason"]
    assert service.acknowledge_review(id_, "Test admin") is False
    assert rcon.add_vip.call_count == 1


def test_config_api_reports_success_and_validation_never_saves(monkeypatch):
    from rcon.api_commands import RconAPI
    from rcon import api_commands

    save, audit = Mock(), Mock()
    monkeypatch.setattr(
        VipRewardsUserConfig, "load_from_db", lambda: VipRewardsUserConfig()
    )
    monkeypatch.setattr(VipRewardsUserConfig, "save_to_db", save)
    monkeypatch.setattr(api_commands, "audit_user_config_differences", audit)
    assert (
        RconAPI.validate_vip_rewards_config(None, "admin", reset_to_default=True)
        is True
    )
    assert not save.called and not audit.called
    assert (
        RconAPI.set_vip_rewards_config(None, "admin", config={"enabled": True}) is True
    )
    assert save.call_count == 1 and audit.call_count == 1
    with pytest.raises(ValidationError):
        RconAPI.validate_vip_rewards_config(
            None, "admin", config={"weekly": {"hours": -2}}
        )


def test_revision_change_blocks_gate_until_fresh_observation():
    e = engine(config())
    e.c.revision = "another-activation"
    assert gate(e.s, e.c, NOW + 1) == "unknown"
    e = Engine(e.s, e.c)
    e.snapshot(NOW + 30, PLAYERS, COUNTS, THRESHOLDS)
    assert gate(e.s, e.c, NOW + 30) == "active"
    assert e.s["round_seconds"] == 0


def test_unknown_round_identity_blocks_round_rewards():
    e = engine(config(round={"enabled": True, "minutes": 1}))
    e.s["round_known"] = False
    e.player("a")["round"] = 1800
    e.s["round_seconds"] = 1800
    e.event(event("round_end"), NOW + 1)
    assert not e.claims


def test_migration_matches_model_tables(delivery, monkeypatch):
    import importlib.util
    from pathlib import Path
    from sqlalchemy import create_engine, inspect
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from rcon.models import VipRewardEvent, VipRewardGrant, VipRewardState

    path = Path(__file__).parents[1] / "alembic/versions/c8e2a4f61009_vip_rewards.py"
    spec = importlib.util.spec_from_file_location("vip_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    db = create_engine("sqlite://")
    with db.begin() as connection:
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        schema = inspect(connection)
        for model in (VipRewardEvent, VipRewardGrant, VipRewardState):
            assert {c["name"] for c in schema.get_columns(model.__tablename__)} == set(
                model.__table__.columns.keys()
            )
        migration.downgrade()
        assert not inspect(connection).get_table_names()
    db.dispose()

@pytest.mark.parametrize('message,command,accepted', [
    (' !BALANCE ', '!balance', True), ('!balancevip', '!balance', False),
    ('!balance extra', '!balance', False), ('!helfen', '!helfen', True),
    ('!balance', '!helfen', False),
])
def test_rewards_share_balance_command(monkeypatch, message, command, accepted):
    from rcon.vip_rewards import hooks
    from types import SimpleNamespace
    monkeypatch.setattr(hooks.AutobalancerUserConfig, 'load_from_db', lambda: SimpleNamespace(volunteer_command=command))
    enqueue = Mock()
    monkeypatch.setattr(hooks, 'enqueue', enqueue)
    hooks.signup(None, dict(sub_content=message, player_id_1='a', timestamp_ms=1000, raw=message))
    assert enqueue.call_count == int(accepted)
    if accepted:
        assert enqueue.call_args.args[0]['kind'] == 'signup'

def test_disabled_challenge_can_be_saved_before_weapon_selection():
    cfg = config(challenges=[dict(id='draft', name='Draft', weapons=[])])
    assert cfg.challenges[0].weapons == []
    with pytest.raises(ValidationError):
        config(challenges=[dict(id='draft', name='Draft', enabled=True, weapons=[])])


def test_volunteer_switch_does_not_mark_as_forced(monkeypatch):
    from rcon.rcon import Rcon, ServerCtl
    from rcon.vip_rewards import hooks
    from rcon.leadership_vote import storage
    forced = Mock()
    switch = Mock(return_value=True)
    monkeypatch.setattr(hooks, 'mark_forced', forced)
    monkeypatch.setattr(storage, 'before_manual_action', Mock())
    monkeypatch.setattr(ServerCtl, 'switch_player_now', switch)
    rcon = object.__new__(Rcon)
    assert rcon.switch_volunteer_now('a') is True
    forced.assert_not_called()
    switch.assert_called_once_with('a')
    assert rcon.switch_player_now('b') is True
    forced.assert_called_once_with('b')

@pytest.mark.parametrize("period, expected", [("day", "2026-11-09T23:00:00+00:00"), ("week", "2026-11-08T23:00:00+00:00"), ("month", "2026-10-31T23:00:00+00:00")])
def test_award_calendar_boundaries(period, expected):
    from rcon.vip_rewards.service import award_period_start
    now = datetime(2026, 11, 10, 12, tzinfo=timezone.utc).timestamp()
    assert award_period_start(now, period, "Europe/Berlin") == datetime.fromisoformat(expected).timestamp()

@pytest.mark.parametrize("period", ["week", "month"])
def test_award_limit_survives_daily_budget_reset(delivery, monkeypatch, period):
    service, cfg, rcon, remote, add, read = delivery
    cfg.melee.limit_period = period
    service.read_gate_state(False)["config"] = cfg.model_dump_json()
    for key in ("one", "two", "three"):
        service.deliver(rcon, add(key))
    monkeypatch.setattr(service.time, "time", lambda: NOW + 86401)
    monkeypatch.setattr(service, "read_gate_state", lambda _: {"observed": NOW + 86401, "healthy": True})
    fourth = add("four")
    service.deliver(rcon, fourth)
    assert read(fourth)["reason"] == "rule_limit"
    assert rcon.add_vip.call_count == 3
