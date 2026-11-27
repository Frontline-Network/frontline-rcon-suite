"""Durable admission, fenced delivery, legacy cutover and retained review data."""
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import importlib.util
import os
from pathlib import Path
from threading import Event
import traceback
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, event, select, text
from sqlalchemy.exc import StatementError
from sqlalchemy.orm import sessionmaker

from rcon import webhook_outbox as outbox

NOW = datetime(2026, 11, 27, 12, 0, tzinfo=timezone.utc)
QUEUE = "whs:3:discord:admin:synthetic"


@pytest.fixture(params=("sqlite", "postgresql"))
def database(request, monkeypatch, tmp_path):
    root = None
    schema = None
    if request.param == "postgresql":
        dsn = os.getenv("TEST_POSTGRES_DSN")
        if not dsn:
            pytest.skip("requires disposable PostgreSQL")
        root = create_engine(dsn)
        schema = "webhook_outbox_" + uuid4().hex
        with root.begin() as conn:
            conn.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"}, pool_size=8)
    else:
        engine = create_engine("sqlite:///" + str(tmp_path / "outbox.sqlite"),
                               connect_args={"timeout": 10, "check_same_thread": False})
    outbox.WebhookOutboxQueue.__table__.create(engine)
    outbox.WebhookOutboxDelivery.__table__.create(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(outbox, "get_session_maker", lambda: maker)
    try:
        yield maker, engine, request.param
    finally:
        engine.dispose()
        if root is not None:
            with root.begin() as conn:
                conn.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            root.dispose()


def row(database, public_id):
    with database[0]() as session:
        return session.scalar(select(outbox.WebhookOutboxDelivery).where(
            outbox.WebhookOutboxDelivery.message_id == public_id))


def send(public_id, claim, *, now=NOW):
    assert claim.id == public_id
    assert outbox.mark_sending(claim.id, claim.token, now=now)
    assert outbox.finish(claim.id, claim.token, status="sent", now=now)


def test_retrying_head_keeps_fifo_without_blocking_other_queues(database):
    first = outbox.enqueue(QUEUE, b"first", 3, now=NOW)
    second = outbox.enqueue(QUEUE, b"second", 3, now=NOW)
    other = outbox.enqueue(QUEUE + "-other", b"other", 3, now=NOW)
    claimed = outbox.claim(QUEUE, now=NOW)
    assert outbox.pending_queues(now=NOW) == [QUEUE + "-other"]
    assert outbox.claim(QUEUE, now=NOW) is None
    assert outbox.mark_sending(first, claimed.token, now=NOW)
    assert outbox.finish(first, claimed.token, status="retry", reason="http_429", retry_after_seconds=30, now=NOW)
    assert outbox.claim(QUEUE, now=NOW + timedelta(seconds=29)) is None
    send(other, outbox.claim(QUEUE + "-other", now=NOW))
    send(first, outbox.claim(QUEUE, now=NOW + timedelta(seconds=30)), now=NOW + timedelta(seconds=30))
    send(second, outbox.claim(QUEUE, now=NOW + timedelta(seconds=30)), now=NOW + timedelta(seconds=30))
    assert outbox.summary() == {"sent": 3}
    assert outbox.pending_queues(now=NOW + timedelta(days=1)) == []


def test_old_claim_fenced_and_only_started_http_can_be_acknowledged(database):
    public_id = outbox.enqueue(QUEUE, b"secret-token-payload", now=NOW)
    old = outbox.claim(QUEUE, lease_seconds=2, now=NOW)
    assert "secret-token" not in repr(old)
    assert not outbox.finish(public_id, old.token, status="sent", now=NOW)
    new = outbox.claim(QUEUE, now=NOW + timedelta(seconds=3))
    assert new.id == public_id and new.token != old.token
    assert new.attempts == 0
    assert not outbox.mark_sending(public_id, old.token, now=NOW + timedelta(seconds=3))
    assert not outbox.finish(public_id, old.token, status="review", now=NOW + timedelta(seconds=3))
    send(public_id, new, now=NOW + timedelta(seconds=3))
    assert row(database, public_id).payload is None
    assert not outbox.finish(public_id, new.token, status="retry", now=NOW)


def test_interrupted_http_is_retained_for_review_not_replayed(database):
    public_id = outbox.enqueue(QUEUE, b"important", now=NOW)
    claim = outbox.claim(QUEUE, lease_seconds=1, now=NOW)
    assert outbox.mark_sending(public_id, claim.token, lease_seconds=1, now=NOW)
    assert outbox.recover_expired(now=NOW + timedelta(seconds=2)) == 1
    assert outbox.claim(QUEUE, now=NOW + timedelta(seconds=2)) is None
    assert row(database, public_id).payload == b"important"
    assert outbox.count_review() == 1
    metadata = outbox.list_review()[0]
    assert metadata["id"] == public_id and metadata["reason"] == "delivery_interrupted"
    assert "payload" not in metadata and "queue_id" not in metadata
    assert outbox.retry_review(public_id, now=NOW + timedelta(seconds=2))
    assert not outbox.retry_review(public_id, now=NOW + timedelta(seconds=2))
    send(public_id, outbox.claim(QUEUE, now=NOW + timedelta(seconds=2)), now=NOW + timedelta(seconds=2))


def test_duplicate_occurrences_remain_distinct_but_retry_is_idempotent(database):
    a = outbox.enqueue(QUEUE, b"identical", dedupe_key="occurrence-a", now=NOW)
    b = outbox.enqueue(QUEUE, b"identical", dedupe_key="occurrence-b", now=NOW)
    assert a != b
    assert outbox.enqueue(QUEUE, b"identical", dedupe_key="occurrence-a", now=NOW) == a
    with pytest.raises(ValueError, match="different content"):
        outbox.enqueue(QUEUE, b"different", dedupe_key="occurrence-a", now=NOW)
    assert outbox.queue_lengths() == {QUEUE: 2}
    send(a, outbox.claim(QUEUE, now=NOW))
    assert outbox.enqueue(QUEUE, b"identical", dedupe_key="occurrence-a", now=NOW) == a
    assert outbox.queue_lengths() == {QUEUE: 1}


def test_server_number_uses_positive_sql_integer_range_not_blacklist_mask_limit(database):
    for number in (33, 65535, 2**31 - 1):
        public_id = outbox.enqueue(QUEUE, b"x", number, now=NOW)
        assert outbox.lookup(public_id)["server_number"] == number
    for invalid in (0, -1, True, 2**31):
        with pytest.raises(ValueError, match="server number"):
            outbox.enqueue(QUEUE, b"x", invalid, now=NOW)


def test_legacy_priority_preserves_cutover_fifo(database):
    native = outbox.enqueue(QUEUE, b"native", now=NOW)
    old_a = outbox.enqueue(QUEUE, b"old-a", legacy=True, now=NOW)
    old_b = outbox.enqueue(QUEUE, b"old-b", legacy=True, now=NOW)
    for expected in (old_a, old_b, native):
        send(expected, outbox.claim(QUEUE, now=NOW))


def test_coalescing_only_supersedes_queued_snapshots(database):
    current = outbox.enqueue(QUEUE, b"current", now=NOW)
    claimed = outbox.claim(QUEUE, now=NOW)
    old = outbox.enqueue(QUEUE, b"old", coalesce=True, now=NOW)
    latest = outbox.enqueue(QUEUE, b"latest", coalesce=True, now=NOW)
    assert row(database, old).status == "superseded" and row(database, old).payload is None
    assert row(database, current).payload == b"current"
    assert outbox.claim(QUEUE, now=NOW) is None
    send(current, claimed)
    send(latest, outbox.claim(QUEUE, now=NOW))
    assert outbox.summary() == {"sent": 2, "superseded": 1}


def test_delayed_legacy_snapshot_cannot_supersede_native_queued_state(database):
    native = outbox.enqueue(QUEUE, b"native-new", coalesce=True, now=NOW)
    legacy = outbox.enqueue(QUEUE, b"legacy-old", coalesce=True, legacy=True,
        created_at=NOW - timedelta(days=1), now=NOW)
    assert row(database, native).status == "queued"
    assert row(database, native).payload == b"native-new"
    assert row(database, legacy).status == "superseded"
    assert row(database, legacy).payload is None
    send(native, outbox.claim(QUEUE, now=NOW))
    assert outbox.pending_queues(now=NOW) == []


def test_native_snapshot_barrier_survives_success_and_tombstone_cleanup(database):
    native = outbox.enqueue(QUEUE, b"native-new", coalesce=True, now=NOW)
    send(native, outbox.claim(QUEUE, now=NOW))
    later = NOW + timedelta(days=31)
    assert outbox.cleanup_sent(now=later) == 1
    legacy = outbox.enqueue(QUEUE, b"legacy-old", coalesce=True, legacy=True,
        created_at=NOW - timedelta(days=1), now=later)
    assert row(database, legacy).status == "superseded"
    assert row(database, legacy).payload is None
    # The marker applies only to replaceable snapshots, never normal reports.
    ordinary = outbox.enqueue(QUEUE, b"ordinary-report", legacy=True, now=later)
    assert row(database, ordinary).payload == b"ordinary-report"
    assert outbox.claim(QUEUE, now=later).id == ordinary


def test_reset_barrier_retains_legacy_occurrences_imported_after_the_reset(database):
    assert outbox.review_queue(QUEUE, now=NOW) == 0
    for index in range(3):
        message = outbox.enqueue(QUEUE, f"old-{index}".encode(), legacy=True, now=NOW)
        assert row(database, message).status == "review"
        assert row(database, message).reason == "operator_reset"
        assert row(database, message).payload == f"old-{index}".encode()
    assert outbox.pending_queues(now=NOW) == []
    # A reset applies to the outstanding legacy generation, not future native messages.
    native = outbox.enqueue(QUEUE, b"new-report", now=NOW)
    send(native, outbox.claim(QUEUE, now=NOW))
    generation = outbox.get_legacy_review_generation(QUEUE)
    assert outbox.clear_legacy_review(QUEUE, expected_generation=generation)
    after = outbox.enqueue(QUEUE, b"later-legacy", legacy=True, now=NOW)
    assert outbox.claim(QUEUE, now=NOW).id == after
    assert not outbox.clear_legacy_review(QUEUE + "-missing", expected_generation=generation)


def test_stale_importer_cannot_clear_a_newer_reset_generation(database):
    assert outbox.review_queue(QUEUE, now=NOW) == 0
    first = outbox.get_legacy_review_generation(QUEUE)
    assert first is not None
    # Importer A has observed Redis empty, but another reset happens before its ACK.
    assert outbox.review_queue(QUEUE, now=NOW) == 0
    second = outbox.get_legacy_review_generation(QUEUE)
    assert second is not None and second != first
    assert not outbox.clear_legacy_review(QUEUE, expected_generation=first)
    assert not outbox.clear_legacy_review(QUEUE, expected_generation=None)
    assert not outbox.clear_legacy_review(QUEUE)
    assert outbox.get_legacy_review_generation(QUEUE) == second
    late = outbox.enqueue(QUEUE, b"late-before-new-source-proof", legacy=True, now=NOW)
    assert row(database, late).status == "review"
    # Only B's matching empty-source proof can clear B's barrier.
    assert outbox.clear_legacy_review(QUEUE, expected_generation=second)
    assert outbox.get_legacy_review_generation(QUEUE) is None
    assert not outbox.clear_legacy_review(QUEUE, expected_generation=second)
    later = outbox.enqueue(QUEUE, b"after-matching-proof", legacy=True, now=NOW)
    assert row(database, later).status == "queued"


def test_operator_retry_authorizes_age_bypass_without_changing_payload(database):
    public_id = outbox.enqueue(QUEUE, b"old-report", created_at=NOW - timedelta(days=7), now=NOW)
    first = outbox.claim(QUEUE, now=NOW)
    assert first.allow_expired is False
    assert outbox.finish(public_id, first.token, status="review", reason="message_expired", now=NOW)
    assert outbox.retry_review(public_id, now=NOW)
    retry = outbox.claim(QUEUE, now=NOW)
    assert retry.allow_expired is True and retry.payload == b"old-report"
    assert outbox.finish(public_id, retry.token, status="retry", reason="local_rate_limit", now=NOW)
    assert outbox.claim(QUEUE, now=NOW).allow_expired is True


def test_reset_fences_unsent_claim_without_cancelling_started_http(database):
    a = outbox.enqueue(QUEUE, b"a", now=NOW)
    b = outbox.enqueue(QUEUE, b"b", now=NOW)
    first = outbox.claim(QUEUE, now=NOW)
    assert outbox.review_queue(QUEUE, now=NOW) == 2
    assert not outbox.mark_sending(a, first.token, now=NOW)
    assert row(database, a).payload == b"a" and row(database, b).payload == b"b"
    assert outbox.retry_review(a, now=NOW)
    first = outbox.claim(QUEUE, now=NOW)
    assert outbox.mark_sending(a, first.token, now=NOW)
    assert outbox.review_queue(QUEUE, now=NOW) == 0
    assert outbox.finish(a, first.token, status="sent", now=NOW)


def test_review_import_retains_public_id_date_and_even_invalid_empty_payload(database):
    old = NOW - timedelta(days=90)
    public_id = "old-archive-public-id"
    assert outbox.enqueue(QUEUE, b"", public_id=public_id, initial_status="review", legacy=True,
        initial_attempts=5, reason="invalid_payload", created_at=old, now=NOW) == public_id
    assert outbox.list_review()[0]["failed_at"] == old
    assert outbox.list_review()[0]["retry_attempts"] == 5
    assert row(database, public_id).payload == b""
    with pytest.raises(ValueError):
        outbox.enqueue(QUEUE, b"", now=NOW)
    assert outbox.cleanup_sent(now=NOW + timedelta(days=365)) == 0


def test_retention_only_removes_scrubbed_acknowledged_terminal_rows(database):
    native = outbox.enqueue(QUEUE, b"native", now=NOW)
    send(native, outbox.claim(QUEUE, now=NOW))
    legacy = outbox.enqueue(QUEUE, b"legacy", legacy=True, dedupe_key="legacy:once", now=NOW)
    send(legacy, outbox.claim(QUEUE, now=NOW))
    pending = outbox.enqueue(QUEUE, b"pending", now=NOW)
    review = outbox.enqueue(QUEUE + "-review", b"review", initial_status="review", now=NOW)
    later = NOW + timedelta(days=31)
    assert outbox.cleanup_sent(now=later) == 1
    assert row(database, native) is None
    assert row(database, legacy) is not None
    assert outbox.enqueue(QUEUE, b"legacy", legacy=True, dedupe_key="legacy:once", now=later) == legacy
    assert outbox.acknowledge_source(legacy)
    assert outbox.cleanup_sent(now=later) == 1
    assert row(database, pending).payload == b"pending"
    assert row(database, review).payload == b"review"


def test_lease_renewal_and_owner_checks(database):
    public_id = outbox.enqueue(QUEUE, b"x", now=NOW)
    claim = outbox.claim(QUEUE, lease_seconds=2, now=NOW)
    assert not outbox.renew(public_id, "wrong", now=NOW)
    assert outbox.renew(public_id, claim.token, lease_seconds=10, now=NOW + timedelta(seconds=1))
    assert outbox.recover_expired(now=NOW + timedelta(seconds=3)) == 0
    assert not outbox.renew(public_id, claim.token, now=NOW + timedelta(seconds=12))
    assert outbox.recover_expired(now=NOW + timedelta(seconds=12)) == 1


def test_explicit_operator_retry_refreshes_attempt_budget(database):
    public_id = outbox.enqueue(QUEUE, b"x", initial_status="review", now=NOW)
    with database[0]() as session, session.begin():
        record = session.scalar(select(outbox.WebhookOutboxDelivery).where(
            outbox.WebhookOutboxDelivery.message_id == public_id))
        record.attempts = 100
    assert outbox.retry_review(public_id, now=NOW)
    assert outbox.claim(QUEUE, now=NOW).attempts == 0


def test_send_refreshes_lease_and_only_http_reservations_consume_attempt_budget(database):
    public_id = outbox.enqueue(QUEUE, b"x", now=NOW)
    claim = outbox.claim(QUEUE, lease_seconds=10, now=NOW)
    assert claim.attempts == 0
    assert outbox.mark_sending(public_id, claim.token, lease_seconds=30, now=NOW + timedelta(seconds=9))
    assert outbox.recover_expired(now=NOW + timedelta(seconds=11)) == 0
    assert row(database, public_id).attempts == 1
    assert outbox.finish(public_id, claim.token, status="retry", now=NOW + timedelta(seconds=12))
    again = outbox.claim(QUEUE, now=NOW + timedelta(seconds=13))
    assert again.attempts == 1
    assert outbox.finish(public_id, again.token, status="retry", reason="local_rate_limit", now=NOW + timedelta(seconds=13))
    assert row(database, public_id).attempts == 1


def test_imported_attempt_counter_is_bounded_and_cannot_overflow_on_send(database):
    for invalid in (-1, True, 2**31, 1.5):
        with pytest.raises(ValueError, match="attempt count"):
            outbox.enqueue(QUEUE, b"x", initial_attempts=invalid, now=NOW)
    public_id = outbox.enqueue(QUEUE, b"x", initial_attempts=2**31 - 1, now=NOW)
    claimed = outbox.claim(QUEUE, now=NOW)
    assert claimed.attempts == 2**31 - 1
    send(public_id, claimed)
    assert row(database, public_id).attempts == 2**31 - 1


def test_storage_error_does_not_expose_sql_bound_payload(database):
    token = "PRIVATE-WEBHOOK-TOKEN-SENTINEL"
    def fail(_session):
        raise StatementError("write failed", "INSERT ...", {"payload": token}, RuntimeError(token))
    maker = database[0]
    event.listen(maker, "before_commit", fail)
    try:
        with pytest.raises(outbox.OutboxStorageError) as exc:
            outbox.enqueue(QUEUE, token.encode(), now=NOW)
        assert token not in "".join(traceback.format_exception(exc.type, exc.value, exc.tb))
    finally:
        event.remove(maker, "before_commit", fail)


def test_concurrent_consumers_claim_only_one_head(database):
    if database[2] != "postgresql":
        pytest.skip("PostgreSQL row lock concurrency")
    outbox.enqueue(QUEUE, b"one", now=NOW)
    with ThreadPoolExecutor(max_workers=2) as pool:
        claims = list(pool.map(lambda _: outbox.claim(QUEUE, now=NOW), range(2)))
    assert sum(c is not None for c in claims) == 1


def test_postgres_commit_order_is_serialized_per_queue(database):
    if database[2] != "postgresql":
        pytest.skip("PostgreSQL producer lock concurrency")
    first_at_commit = Event()
    release_first = Event()
    second_started = Event()
    first_marker = {"armed": True}
    def pause_first(session):
        if first_marker["armed"]:
            first_marker["armed"] = False
            first_at_commit.set()
            assert release_first.wait(5)
    event.listen(database[0], "before_commit", pause_first)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            first = pool.submit(outbox.enqueue, QUEUE, b"first", now=NOW)
            assert first_at_commit.wait(5)
            def enqueue_second():
                second_started.set()
                return outbox.enqueue(QUEUE, b"second", now=NOW)
            second = pool.submit(enqueue_second)
            assert second_started.wait(5)
            assert not second.done()
            release_first.set()
            a, b = first.result(5), second.result(5)
        send(a, outbox.claim(QUEUE, now=NOW))
        send(b, outbox.claim(QUEUE, now=NOW))
    finally:
        release_first.set()
        event.remove(database[0], "before_commit", pause_first)


def test_migration_roundtrip_refuses_to_drop_retained_payloads(tmp_path, monkeypatch):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations
    from sqlalchemy import inspect

    path = Path(__file__).parents[1] / "alembic/versions/c261127wh001_webhook_outbox.py"
    spec = importlib.util.spec_from_file_location("webhook_outbox_migration", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite:///" + str(tmp_path / "migration.sqlite"))
    maker = sessionmaker(engine, expire_on_commit=False)
    monkeypatch.setattr(outbox, "get_session_maker", lambda: maker)
    try:
        with engine.begin() as conn:
            monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
            migration.upgrade()
        for model in (outbox.WebhookOutboxQueue, outbox.WebhookOutboxDelivery):
            assert {c["name"] for c in inspect(engine).get_columns(model.__tablename__)} == set(model.__table__.c.keys())
        public_id = outbox.enqueue(QUEUE, b"important", now=NOW)
        with pytest.raises(RuntimeError, match="Resolve or export"):
            with engine.begin() as conn:
                monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
                migration.downgrade()
        assert row((maker,), public_id).payload == b"important"
        send(public_id, outbox.claim(QUEUE, now=NOW))
        legacy = outbox.enqueue(QUEUE, b"legacy", legacy=True, now=NOW)
        send(legacy, outbox.claim(QUEUE, now=NOW))
        with pytest.raises(RuntimeError, match="Resolve or export"):
            with engine.begin() as conn:
                monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
                migration.downgrade()
        assert outbox.acknowledge_source(legacy)
        with engine.begin() as conn:
            monkeypatch.setattr(migration, "op", Operations(MigrationContext.configure(conn)))
            migration.downgrade()
        assert not inspect(engine).has_table("webhook_outbox_delivery")
        assert not inspect(engine).has_table("webhook_outbox_queue")
    finally:
        engine.dispose()


def test_concurrent_downgrade_cannot_drop_a_message_accepted_after_its_guard(database):
    from alembic.migration import MigrationContext
    from alembic.operations import Operations

    path = Path(__file__).parents[1] / "alembic/versions/c261127wh001_webhook_outbox.py"
    spec = importlib.util.spec_from_file_location("webhook_outbox_migration_concurrent", path)
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    guard_started, release_guard, producer_started = Event(), Event(), Event()
    engine = database[1]

    def before_execute(_conn, _cursor, statement, _parameters, _context, _many):
        if statement.startswith("SELECT count(*) FROM webhook_outbox_delivery"):
            guard_started.set()
            assert release_guard.wait(10)
        if statement.startswith("INSERT INTO webhook_outbox_queue"):
            producer_started.set()

    def downgrade():
        with engine.begin() as conn:
            migration.op = Operations(MigrationContext.configure(conn))
            migration.downgrade()

    event.listen(engine, "before_cursor_execute", before_execute)
    try:
        with ThreadPoolExecutor(max_workers=2) as pool:
            migration_task = pool.submit(downgrade)
            assert guard_started.wait(5)
            producer = pool.submit(outbox.enqueue, QUEUE, b"must-not-be-accepted-and-dropped", now=NOW)
            assert producer_started.wait(5)
            assert not producer.done()
            release_guard.set()
            migration_task.result(10)
            with pytest.raises(outbox.OutboxStorageError):
                producer.result(10)
    finally:
        release_guard.set()
        event.remove(engine, "before_cursor_execute", before_execute)
