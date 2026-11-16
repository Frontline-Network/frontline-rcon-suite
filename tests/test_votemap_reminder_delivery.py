"""Reservation state machine uses fake players and no game server."""
import pytest
import os
import uuid
from concurrent.futures import ThreadPoolExecutor
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.schema import CreateSchema, DropSchema

from rcon.vote_map import reminder_delivery as journal


@pytest.fixture
def database(monkeypatch, tmp_path):
    engine = create_engine("sqlite:///" + (tmp_path / "reminders.sqlite").as_posix())
    journal.metadata.create_all(engine)
    sessions = sessionmaker(engine)
    monkeypatch.setattr(journal, "get_session_maker", lambda: sessions)
    yield sessions
    engine.dispose()


@pytest.mark.parametrize("outcome", ["sent", "unknown"])
def test_confirmed_or_uncertain_delivery_is_never_retried(database, outcome):
    batch = journal.open_batch(3, "periodic", "signature", "message", ["fake-player"], now=100)
    token = journal.reserve(3, batch, "fake-player", now=100)
    assert token and journal.finish(3, batch, "fake-player", token, outcome, now=101)
    assert journal.reserve(3, batch, "fake-player", now=1000) is None


def test_inflight_after_process_failure_is_not_replayed(database):
    batch = journal.open_batch(3, "periodic", "signature", "message", ["fake-player"], now=100)
    assert journal.reserve(3, batch, "fake-player", now=100)
    assert journal.reserve(3, batch, "fake-player", now=1000) is None


def test_only_definite_rejection_retries_with_delay_and_limit(database):
    batch = journal.open_batch(3, "periodic", "signature", "message", ["fake-player"], now=100)
    first = journal.reserve(3, batch, "fake-player", now=100)
    assert journal.finish(3, batch, "fake-player", first, "rejected", now=101)
    assert journal.reserve(3, batch, "fake-player", now=130) is None
    second = journal.reserve(3, batch, "fake-player", now=131)
    assert second and second != first
    assert not journal.finish(3, batch, "fake-player", first, "sent", now=132)
    assert journal.finish(3, batch, "fake-player", second, "rejected", now=132)
    third = journal.reserve(3, batch, "fake-player", now=162)
    assert third and journal.finish(3, batch, "fake-player", third, "rejected", now=163)
    assert journal.reserve(3, batch, "fake-player", now=1000) is None
    with database() as session:
        assert session.execute(select(journal.reminder_delivery.c.attempts)).scalar_one() == 3


def test_reservations_are_separate_per_server_batch_and_player(database):
    first = journal.open_batch(3, "one", "signature", "message", ["a", "b"], now=100)
    second = journal.open_batch(3, "two", "signature", "message", ["a"], now=100)
    other = journal.open_batch(4, "one", "signature", "message", ["a"], now=100)
    for server, batch, player in [(3, first, "a"), (3, first, "b"), (3, second, "a"), (4, other, "a")]:
        assert journal.reserve(server, batch, player, now=100)


def test_batch_snapshot_is_atomic_and_resume_does_not_add_new_players(database):
    first = journal.open_batch(3, "periodic", "signature", "message", ["a", "b"], now=100)
    assert journal.open_batch(3, "periodic", "signature", "message", ["c"], now=101) == first
    assert journal.reserve(3, first, "c", now=102) is None
    assert journal.reserve(3, first, "a", now=102)
    second = journal.open_batch(3, "periodic", "new-signature", "new message", ["c"], now=103)
    assert second != first
    assert journal.reserve(3, first, "b", now=104) is None
    with database() as session:
        old = session.execute(select(journal.reminder_delivery.c.player_id, journal.reminder_delivery.c.status).where(
            journal.reminder_delivery.c.batch_id == first)).all()
    assert dict(old) == {"a": "unknown", "b": "skipped"}
    assert journal.reserve(3, second, "c", now=104)


def test_batch_cannot_complete_before_all_snapshot_outcomes_and_keeps_cooldown(database):
    batch = journal.open_batch(3, "periodic", "sig", "original", ["a", "b"], now=100)
    assert not journal.complete_batch(3, batch, now=101)
    first = journal.reserve(3, batch, "a", now=102)
    assert first and journal.finish(3, batch, "a", first, "sent", now=103)
    assert not journal.complete_batch(3, batch, now=104)
    second = journal.reserve(3, batch, "b", now=105)
    assert second and journal.finish(3, batch, "b", second, "unknown", now=106)
    assert journal.complete_batch(3, batch, now=107)
    result = journal.batch_state(3, batch)
    assert result["batch"]["message"] == "original"
    assert {r["status"] for r in result["recipients"]} == {"sent", "unknown"}
    assert journal.open_batch(3, "periodic", "sig", "new", ["a"], now=110, min_interval=60) is None
    assert journal.open_batch(3, "periodic", "sig", "new", ["a"], now=110, min_interval=60, force=True)


def test_skipping_ineligible_recipient_cannot_overwrite_inflight_delivery(database):
    batch = journal.open_batch(3, "periodic", "sig", "message", ["a", "b"], now=100)
    token = journal.reserve(3, batch, "a", now=101)
    assert not journal.skip(3, batch, "a", now=102)
    assert journal.skip(3, batch, "b", now=102)
    assert journal.finish(3, batch, "a", token, "sent", now=103)
    assert journal.complete_batch(3, batch, now=104)


def test_interrupted_send_becomes_unknown_without_retry_or_late_overwrite(database):
    batch = journal.open_batch(3, "periodic", "sig", "message", ["a"], now=100)
    token = journal.reserve(3, batch, "a", now=101)
    assert journal.recover_uncertain(3, batch, now=400) == 0
    assert journal.recover_uncertain(3, batch, now=401) == 1
    assert not journal.finish(3, batch, "a", token, "sent", now=402)
    assert journal.reserve(3, batch, "a", now=403) is None
    assert journal.complete_batch(3, batch, now=404)


def test_event_completion_updates_durable_global_cooldown_and_is_idempotent(database):
    batch = journal.open_batch(3, "event:abc", "round", "message", ["a"], now=100, force=True, once=True)
    token = journal.reserve(3, batch, "a", now=101)
    assert journal.finish(3, batch, "a", token, "sent", now=102)
    assert journal.complete_batch(3, batch, now=103)
    assert journal.open_batch(3, "event:abc", "round", "message", ["a"], now=104, force=True, once=True) is None
    assert journal.open_batch(3, "periodic", "round", "message", ["a"], now=104, min_interval=300) is None
    assert journal.open_batch(3, "periodic", "round", "message", ["a"], now=403, min_interval=300)


def test_partial_dispatch_retries_only_rejected_recipient(database):
    batch = journal.open_batch(3, "periodic", "round", "message", ["a", "b", "c"], now=100)
    attempts = []
    def send(pid, _message):
        attempts.append(pid)
        if pid == "c":
            raise TimeoutError("lost response")
        return pid != "b"
    first = journal.dispatch(3, batch, ["a", "b", "c"], send, lambda: True, now=100)
    assert not first["complete"]
    assert first["counts"] == {"sent": 1, "rejected": 1, "unknown": 1}
    attempts.clear()
    second = journal.dispatch(3, batch, ["a", "b", "c"], lambda pid, _: attempts.append(pid) or True, lambda: True, now=130)
    assert second["complete"] and second["counts"] == {"sent": 2, "unknown": 1}
    assert attempts == ["b"]


def test_round_change_after_reservation_prevents_message(database):
    batch = journal.open_batch(3, "periodic", "round", "message", ["a"], now=100)
    checks = iter([True, False])
    sent = []
    result = journal.dispatch(3, batch, ["a"], lambda *args: sent.append(args), lambda: next(checks), now=101)
    assert result["stale"] and not sent
    assert journal.batch_state(3, batch)["recipients"][0]["status"] == "skipped"


def test_old_round_is_retired_without_releasing_inflight_sends(database):
    batch = journal.open_batch(3, "event:start", "old-round", "old", ["a", "b"], now=100)
    token = journal.reserve(3, batch, "a", now=101)
    assert [row["batch_id"] for row in journal.open_batches(3)] == [batch]
    assert journal.abandon_batch(3, batch, now=102)
    assert not journal.open_batches(3)
    states = {row["player_id"]: row["status"] for row in journal.batch_state(3, batch)["recipients"]}
    assert states == {"a": "unknown", "b": "skipped"}
    assert journal.reserve(3, batch, "a", now=103) is None
    assert not journal.finish(3, batch, "a", token, "sent", now=104)


def test_stale_worker_cannot_replace_or_retire_new_round_batch(database):
    new = journal.open_batch(3, "periodic", "new-round", "new", ["a"], now=100)
    assert journal.open_batch(3, "periodic", "old-round", "old", ["a"], now=101,
                              is_current=lambda: False) is None
    assert not journal.abandon_batch(3, new, now=102, is_current=lambda: False)
    assert journal.batch_state(3, new)["batch"]["status"] == "open"
    assert journal.reserve(3, new, "a", now=103)


@pytest.mark.parametrize("server,batch,player", [(0, "batch", "a"), (33, "batch", "a"), (3, "", "a"), (3, "batch", "")])
def test_invalid_identity_is_rejected(database, server, batch, player):
    with pytest.raises(ValueError):
        journal.reserve(server, batch, player)


@pytest.mark.skipif(not os.environ.get("RCON_VOTEMAP_TEST_DATABASE"), reason="requires isolated PostgreSQL")
def test_competing_postgres_consumers_reserve_one_message(monkeypatch):
    base = create_engine(os.environ["RCON_VOTEMAP_TEST_DATABASE"])
    schema = "votemap_test_" + uuid.uuid4().hex
    with base.begin() as connection:
        connection.execute(CreateSchema(schema))
    engine = base.execution_options(schema_translate_map={None: schema})
    try:
        journal.metadata.create_all(engine)
        sessions = sessionmaker(engine)
        monkeypatch.setattr(journal, "get_session_maker", lambda: sessions)
        with ThreadPoolExecutor(max_workers=8) as pool:
            batches = list(pool.map(lambda _: journal.open_batch(3, "periodic", "signature", "message", ["fake-player"], now=100), range(16)))
        assert len(set(batches)) == 1
        with ThreadPoolExecutor(max_workers=8) as pool:
            tokens = list(pool.map(lambda _: journal.reserve(3, batches[0], "fake-player", now=100), range(16)))
        assert sum(token is not None for token in tokens) == 1
    finally:
        with base.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        base.dispose()
