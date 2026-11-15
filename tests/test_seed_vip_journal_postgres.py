"""Seed-cycle durability against a disposable PostgreSQL schema."""

import os
import importlib.util
from concurrent.futures import ThreadPoolExecutor
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from threading import Barrier, Event
from uuid import uuid4
from unittest.mock import Mock
from pathlib import Path

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker
from alembic.migration import MigrationContext
from alembic.operations import Operations

from rcon.models import SeedVipCycle, SeedVipGrant, VipRewardGrant
from rcon.seed_vip import journal


@pytest.fixture
def database(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires a disposable PostgreSQL test database")
    root = create_engine(dsn)
    schema = "seed_journal_" + uuid4().hex
    with root.begin() as conn:
        conn.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    SeedVipCycle.__table__.create(engine)
    SeedVipGrant.__table__.create(engine)
    VipRewardGrant.__table__.create(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(journal, "get_session_maker", lambda: maker)
    try:
        yield maker
    finally:
        engine.dispose()
        with root.begin() as conn:
            conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def call(**overrides):
    args = dict(server_number=3, preview=False, seeded=False, player_count=4,
                eligible={"fake-id-a": "Alpha"}, online_when_seeded=False,
                buffer=timedelta(minutes=5), reward_seconds=3600,
                cumulative=True, reward_name=lambda name: "Seed " + name,
                now=datetime(2026, 1, 1, tzinfo=timezone.utc))
    args.update(overrides)
    return journal.observe(**args)


def grants(maker):
    with maker() as session:
        return list(session.scalars(select(SeedVipGrant).order_by(SeedVipGrant.player_id, SeedVipGrant.id)))


def cycle(result):
    return result.completed, result.generation


def test_restart_keeps_eligible_players_and_completion_is_idempotent(database):
    assert cycle(call()) == (False, 1)
    assert cycle(call(eligible={"fake-id-b": "Bravo"})) == (False, 1)
    assert cycle(call(seeded=True, eligible={"fake-id-b": "Bravo"})) == (True, 1)
    assert cycle(call(seeded=True, eligible={"fake-id-b": "Bravo"})) == (False, 1)
    rows = grants(database)
    assert [(row.player_id, row.player_name, row.status) for row in rows] == [
        ("fake-id-a", "Seed Alpha", "queued"), ("fake-id-b", "Seed Bravo", "queued")
    ]


def test_online_only_uses_final_observation(database):
    call(online_when_seeded=True)
    call(seeded=True, online_when_seeded=True, eligible={"fake-id-b": "Bravo"})
    assert [row.player_id for row in grants(database)] == ["fake-id-b"]


def test_initially_full_server_does_not_fabricate_a_seed(database):
    assert cycle(call(seeded=True)) == (False, 0)
    assert grants(database) == []


def test_failed_grant_creation_rolls_back_entire_transition(database):
    call()
    def fail(_name):
        raise ValueError("invalid name template")
    with pytest.raises(ValueError):
        call(seeded=True, reward_name=fail)
    with database() as session:
        saved_cycle = session.get(SeedVipCycle, (3, False))
        assert saved_cycle.phase == "seeding"
        assert saved_cycle.eligible == {"fake-id-a": "Alpha"}
    assert grants(database) == []
    assert cycle(call(seeded=True)) == (True, 1)


def test_concurrent_completion_creates_one_grant(database):
    call()
    barrier = Barrier(3)
    def worker():
        barrier.wait()
        return cycle(call(seeded=True))
    with ThreadPoolExecutor(max_workers=2) as pool:
        tasks = [pool.submit(worker) for _ in range(2)]
        barrier.wait()
        results = [task.result() for task in tasks]
    assert sorted(results) == [(False, 1), (True, 1)]
    assert len(grants(database)) == 1


def test_buffer_and_preview_are_isolated(database):
    now = datetime(2026, 1, 1, tzinfo=timezone.utc)
    call(now=now)
    call(seeded=True, now=now)
    assert cycle(call(now=now + timedelta(minutes=2))) == (False, 1)
    assert cycle(call(now=now + timedelta(minutes=6))) == (False, 2)
    assert cycle(call(preview=True, now=now)) == (False, 1)
    assert cycle(call(preview=True, seeded=True, now=now)) == (True, 1)
    assert {row.status for row in grants(database)} == {"queued", "preview"}


@pytest.fixture
def fake_vip(monkeypatch):
    import rcon.utils
    monkeypatch.setattr(rcon.utils, "get_server_number", lambda: "3")
    monkeypatch.setattr(journal, "vip_lock", lambda _pid: nullcontext())
    store = {}
    monkeypatch.setattr(journal, "current_vip", lambda _api, pid: store.get(pid))
    api = Mock()
    def add_vip(*, player_id, description, expiration):
        store[player_id] = {"name": description, "vip_expiration": expiration}
        return True
    api.add_vip.side_effect = add_vip
    return api, store


def create_grant(database, **kwargs):
    call(**kwargs)
    call(seeded=True, **kwargs)
    return grants(database)[0].id


def test_successful_grant_is_not_repeated(database, fake_vip):
    api, store = fake_vip
    grant_id = create_grant(database)
    assert journal.deliver(api, server_number=3, grant_id=grant_id) == "confirmed"
    assert journal.deliver(api, server_number=3, grant_id=grant_id) == "already_confirmed"
    assert store["fake-id-a"]["vip_expiration"] == "2026-01-01T01:00:00+00:00"
    api.add_vip.assert_called_once()


def test_concurrent_workers_use_real_advisory_lock(database, fake_vip, monkeypatch):
    import rcon.models
    from rcon.vip_rewards.locking import vip_lock

    monkeypatch.setattr(rcon.models, "get_engine", lambda: database.kw["bind"])
    monkeypatch.setattr(journal, "vip_lock", vip_lock)
    api, _store = fake_vip
    grant_id = create_grant(database)
    entered, release = Event(), Event()
    original = api.add_vip.side_effect

    def delayed_add(**kwargs):
        entered.set()
        assert release.wait(10)
        return original(**kwargs)

    api.add_vip.side_effect = delayed_add
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(journal.deliver, api, server_number=3, grant_id=grant_id)
        assert entered.wait(10)
        second = executor.submit(journal.deliver, api, server_number=3, grant_id=grant_id)
        try:
            assert not second.done()
        finally:
            release.set()
        assert {first.result(timeout=15), second.result(timeout=15)} == {"confirmed", "already_confirmed"}
    api.add_vip.assert_called_once()


@pytest.mark.parametrize("server_applied", [False, True])
def test_lost_reply_is_reconciled_without_a_second_write(database, fake_vip, server_applied):
    api, store = fake_vip
    grant_id = create_grant(database)
    def lost(*, player_id, description, expiration):
        if server_applied:
            store[player_id] = {"name": description, "vip_expiration": expiration}
        raise TimeoutError("lost response")
    api.add_vip.side_effect = lost
    with pytest.raises(TimeoutError):
        journal.deliver(api, server_number=3, grant_id=grant_id)
    assert grants(database)[0].status == "prepared"
    assert journal.deliver(api, server_number=3, grant_id=grant_id) == ("confirmed" if server_applied else "review")
    api.add_vip.assert_called_once()


def test_rejected_grant_does_not_stop_next_player_or_retry(database, fake_vip):
    api, _ = fake_vip
    call(eligible={"fake-id-a": "Alpha", "fake-id-b": "Bravo"})
    call(seeded=True, eligible={"fake-id-a": "Alpha", "fake-id-b": "Bravo"})
    first, second = grants(database)
    success = api.add_vip.side_effect
    def reject_first(**kwargs):
        return False if kwargs["player_id"] == "fake-id-a" else success(**kwargs)
    api.add_vip.side_effect = reject_first
    assert journal.deliver(api, server_number=3, grant_id=first.id) == "rejected"
    assert journal.deliver(api, server_number=3, grant_id=second.id) == "confirmed"
    assert journal.deliver(api, server_number=3, grant_id=first.id) == "rejected"
    assert api.add_vip.call_count == 2


def test_prepared_unresolved_grant_blocks_later_seed_for_same_player(database, fake_vip):
    api, _ = fake_vip
    grant_id = create_grant(database)
    api.add_vip.side_effect = TimeoutError("lost response")
    with pytest.raises(TimeoutError):
        journal.deliver(api, server_number=3, grant_id=grant_id)
    api.add_vip.reset_mock()
    now = datetime(2026, 1, 1, 1, tzinfo=timezone.utc)
    call(now=now)
    call(seeded=True, now=now)
    later = grants(database)[-1]
    assert journal.deliver(api, server_number=3, grant_id=later.id) == "blocked"
    assert grants(database)[-1].status == "queued"
    api.add_vip.assert_not_called()
    assert journal.deliver(api, server_number=3, grant_id=grant_id) == "review"
    assert journal.acknowledge_review(3, grant_id, "Operator")
    def success(**kwargs):
        fake_vip[1][kwargs["player_id"]] = {"name": kwargs["description"], "vip_expiration": kwargs["expiration"]}
        return True
    api.add_vip.side_effect = success
    assert journal.deliver(api, server_number=3, grant_id=later.id) == "confirmed"
    api.add_vip.assert_called_once()


def test_unresolved_other_vip_grant_blocks_seed_write(database, fake_vip):
    api, _ = fake_vip
    grant_id = create_grant(database)
    with database.begin() as session:
        session.add(VipRewardGrant(server_number=3, preview=False, player_id="fake-id-a",
                                   rule="test", trigger="one", occurred=0,
                                   requested_seconds=3600, credited_seconds=0,
                                   limit=0, status="prepared", reason="", description=""))
    assert journal.deliver(api, server_number=3, grant_id=grant_id) == "blocked"
    assert grants(database)[0].reason == "blocked_by_unresolved_vip_write"
    assert grants(database)[0].status == "queued"
    api.add_vip.assert_not_called()


def test_review_is_server_scoped_and_acknowledgement_never_replays(database, fake_vip):
    api, _ = fake_vip
    grant_id = create_grant(database)
    api.add_vip.side_effect = TimeoutError("response lost")
    with pytest.raises(TimeoutError):
        journal.deliver(api, server_number=3, grant_id=grant_id)
    assert journal.deliver(api, server_number=3, grant_id=grant_id) == "review"
    assert journal.list_grants(4)["total"] == 0
    history = journal.list_grants(3)
    assert history["total"] == 1 and history["results"][0]["status"] == "review"
    assert journal.list_grants(3, status="review")["total"] == 1
    with pytest.raises(ValueError):
        journal.list_grants(3, status="unknown")
    assert not journal.acknowledge_review(4, grant_id, "Operator")
    assert journal.acknowledge_review(3, grant_id, "Operator")
    assert not journal.acknowledge_review(3, grant_id, "Operator")
    assert grants(database)[0].status == "reviewed"
    assert journal.list_grants(3, status="review")["total"] == 0
    assert journal.deliver(api, server_number=3, grant_id=grant_id) == "reviewed"
    api.add_vip.assert_called_once()


def test_reviewed_seed_does_not_block_a_later_seed(database, fake_vip):
    api, store = fake_vip
    old = create_grant(database)
    original_write = api.add_vip.side_effect
    api.add_vip.side_effect = TimeoutError("response lost")
    with pytest.raises(TimeoutError):
        journal.deliver(api, server_number=3, grant_id=old)
    assert journal.deliver(api, server_number=3, grant_id=old) == "review"
    assert journal.acknowledge_review(3, old, "Operator")
    now = datetime(2026, 1, 1, 1, tzinfo=timezone.utc)
    call(now=now)
    call(seeded=True, now=now)
    api.add_vip.side_effect = original_write
    assert journal.deliver(api, server_number=3, grant_id=grants(database)[-1].id) == "confirmed"
    assert store["fake-id-a"]["vip_expiration"] == "2026-01-01T02:00:00+00:00"


def test_service_resumes_seed_after_restart_without_duplicate_grants(database, fake_vip, monkeypatch):
    from rcon.seed_vip import service
    from rcon.seed_vip.models import Player, ServerPopulation
    from rcon.user_config.seed_vip import SeedVIPUserConfig

    api, _ = fake_vip
    config = SeedVIPUserConfig(enabled=True, dry_run=False, language=None)
    disabled = config.model_copy(update={"enabled": False})
    players = ServerPopulation(players={
        "fake-id-a": Player(name="Alpha", player_id="fake-id-a", current_playtime_seconds=600),
    })
    low = {"num_allied_players": 1, "num_axis_players": 1}
    full = {"num_allied_players": 22, "num_axis_players": 22}
    monkeypatch.setattr(service, "get_rcon_api", lambda: api)
    monkeypatch.setattr(service, "get_server_number", lambda: "3")
    monkeypatch.setattr(service, "NotificationOutbox", lambda: Mock(flush=Mock(return_value=False)))
    monkeypatch.setattr(service, "get_vips", lambda rcon: {})
    monkeypatch.setattr(service, "message_players", Mock())
    monkeypatch.setattr(service, "wait", lambda *_: False)

    def run_once(snapshot):
        configs = iter([config, config, disabled])
        monkeypatch.setattr(service.SeedVIPUserConfig, "load_from_db", lambda: next(configs))
        monkeypatch.setattr(service, "get_server_snapshot", lambda _api: (players, snapshot))
        service.run()

    run_once(low)
    assert grants(database) == []
    run_once(full)
    assert [row.status for row in grants(database)] == ["confirmed"]
    api.add_vip.assert_called_once()
    run_once(full)
    api.add_vip.assert_called_once()


def test_service_continues_after_one_uncertain_grant(database, fake_vip, monkeypatch):
    from rcon.seed_vip import service
    from rcon.seed_vip.models import Player, ServerPopulation
    from rcon.user_config.seed_vip import SeedVIPUserConfig

    api, store = fake_vip
    config = SeedVIPUserConfig(enabled=True, dry_run=False, language=None)
    disabled = config.model_copy(update={"enabled": False})
    players = ServerPopulation(players={
        pid: Player(name=pid, player_id=pid, current_playtime_seconds=600)
        for pid in ("fake-id-a", "fake-id-b", "fake-id-c")
    })
    success = api.add_vip.side_effect
    def maybe_timeout(**kwargs):
        if kwargs["player_id"] == "fake-id-b":
            raise TimeoutError("response lost")
        return success(**kwargs)
    api.add_vip.side_effect = maybe_timeout
    monkeypatch.setattr(service, "get_rcon_api", lambda: api)
    monkeypatch.setattr(service, "get_server_number", lambda: "3")
    monkeypatch.setattr(service, "NotificationOutbox", lambda: Mock(flush=Mock(return_value=False)))
    monkeypatch.setattr(service, "get_vips", lambda rcon: {})
    monkeypatch.setattr(service, "message_players", Mock())
    monkeypatch.setattr(service, "wait", lambda *_: False)

    def run_once(snapshot):
        configs = iter([config, config, disabled])
        monkeypatch.setattr(service.SeedVIPUserConfig, "load_from_db", lambda: next(configs))
        monkeypatch.setattr(service, "get_server_snapshot", lambda _api: (players, snapshot))
        service.run()

    run_once({"num_allied_players": 1, "num_axis_players": 1})
    run_once({"num_allied_players": 22, "num_axis_players": 22})
    assert [row.status for row in grants(database)] == ["confirmed", "prepared", "confirmed"]
    assert set(store) == {"fake-id-a", "fake-id-c"}
    run_once({"num_allied_players": 22, "num_axis_players": 22})
    assert [row.status for row in grants(database)] == ["confirmed", "review", "confirmed"]
    assert api.add_vip.call_count == 3


def test_staged_migration_is_repeatable_and_rejects_incomplete_schema(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires a disposable PostgreSQL test database")
    db = create_engine(dsn)
    schema = "seed_migration_" + uuid4().hex
    path = Path(__file__).resolve().parents[1] / "alembic/versions/e3150a1b2c3d_seed_vip_journal.py"
    spec = importlib.util.spec_from_file_location("seed_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    try:
        with db.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
            conn.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
            migration.upgrade()
            migration.upgrade()
            migration.downgrade()
            conn.execute(text("CREATE TABLE seed_vip_cycle (server_number INTEGER)"))
            with pytest.raises(RuntimeError, match="Incomplete staged"):
                migration.upgrade()
    finally:
        with db.begin() as conn:
            conn.execute(text(f'DROP SCHEMA IF EXISTS "{schema}" CASCADE'))
        db.dispose()
