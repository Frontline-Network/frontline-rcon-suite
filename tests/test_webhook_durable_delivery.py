"""Exercise delivery through SQL persistence, bounded Redis hints and HTTP.

All endpoints are synthetic and construct_webhook is replaced before delivery.
The opt-in case uses only disposable PostgreSQL/Redis configured by the test run.
"""
import asyncio
from datetime import datetime, timedelta, timezone
import os
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock
from uuid import uuid4

from fakeredis import FakeStrictRedis
import httpx
import orjson
import pytest
import redis
from sqlalchemy import create_engine, select, text, update
from sqlalchemy.orm import sessionmaker

from rcon import webhook_legacy, webhook_outbox as outbox
from rcon import webhook_service as service


QUEUE = "whs:1:discord:audit:123"


@pytest.fixture(params=["sqlite_fake", "postgres_redis"])
def delivery_runtime(request, monkeypatch, tmp_path):
    root = None
    schema = None
    legacy_case = "legacy" in request.node.originalname
    if request.param == "sqlite_fake" and legacy_case:
        pytest.importorskip("lupa", reason="native Lua handoff is exercised by the real Redis case")
    if request.param == "postgres_redis":
        dsn = os.environ.get("TEST_POSTGRES_DSN")
        redis_url = os.environ.get("TEST_REDIS_URL")
        if not dsn or not redis_url:
            pytest.skip("requires disposable PostgreSQL and Redis")
        configured = redis.Redis.from_url(redis_url, decode_responses=False)
        kwargs = dict(configured.connection_pool.connection_kwargs)
        kwargs["db"] = 15
        red = redis.Redis(connection_pool=redis.ConnectionPool(
            connection_class=configured.connection_pool.connection_class, **kwargs))
        configured.close()
        if red.dbsize():
            red.close()
            pytest.skip("requires empty database 15 in the disposable Redis")
        root = create_engine(dsn)
        schema = "webhook_delivery_" + uuid4().hex
        with root.begin() as connection:
            connection.execute(text(f'CREATE SCHEMA "{schema}"'))
        engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"}, pool_size=10)
        # Static production key names are exercised in an initially empty,
        # explicitly disposable logical database, not another test's DB1.
        initial_keys = set()
    else:
        engine = create_engine("sqlite:///" + str(tmp_path / "webhooks.sqlite"),
                               connect_args={"check_same_thread": False, "timeout": 10})
        red = FakeStrictRedis()
        initial_keys = set()

    outbox.WebhookOutboxQueue.__table__.create(engine)
    outbox.WebhookOutboxDelivery.__table__.create(engine)
    maker = sessionmaker(bind=engine, expire_on_commit=False)
    monkeypatch.setattr(outbox, "get_session_maker", lambda: maker)
    monkeypatch.setattr(service, "get_server_number", lambda: "1")
    monkeypatch.setattr(service, "WH_MAX_QUEUE_LENGTH", 150)
    monkeypatch.setattr(service, "WH_MAX_MESSAGE_AGE_SECS", 3600)
    monkeypatch.setattr(service, "_next_wakeup_attempt_at", 0.0)
    monkeypatch.setenv("HLL_WH_HEALTH_PATH", str(tmp_path / "webhook-service-healthy"))
    if request.param == "sqlite_fake" and not legacy_case:
        # Fakeredis Lua is optional in the locked test dependencies. These
        # cases focus on SQL/HTTP/recovery; their real-Redis variants also run
        # the actual native legacy discovery and handoff functions.
        monkeypatch.setattr(service, "_import_legacy_queue", lambda *a, **kw: 0)
        monkeypatch.setattr(service, "_import_legacy_dead_letters", lambda *a, **kw: 0)
    service._RATE_LIMIT_BUCKETS.clear()
    monkeypatch.setattr(service, "_SHARED_LOCK", None)
    try:
        yield SimpleNamespace(maker=maker, red=red, engine=engine)
    finally:
        service._RATE_LIMIT_BUCKETS.clear()
        if request.param == "postgres_redis":
            # Never FLUSHDB: delete only test-created keys, preserving existing
            # fixtures in the explicitly disposable server.
            created = set(red.scan_iter(count=100)) - initial_keys
            if created:
                red.delete(*created)
        red.close()
        engine.dispose()
        if root is not None:
            with root.begin() as connection:
                connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
            root.dispose()


def message(content="synthetic report", *, webhook_id="123", old=False):
    return service.WebhookMessage(
        server_number=1,
        webhook_type=service.WebhookType.DISCORD,
        message_type=service.WebhookMessageType.AUDIT,
        sent_at=datetime.now(timezone.utc) - timedelta(hours=2 if old else 0),
        payload={"url": f"https://discord.com/api/webhooks/{webhook_id}/fake-token",
                 "webhook_id": webhook_id, "webhook_token": "fake-token",
                 "content": content, "rate_limit_retry": False},
    )


def rows(runtime):
    with runtime.maker() as session:
        return list(session.scalars(select(outbox.WebhookOutboxDelivery).order_by(
            outbox.WebhookOutboxDelivery.id)))


def response(status=204, *, headers=True):
    values = {"x-ratelimit-bucket": "synthetic-bucket", "x-ratelimit-remaining": "4",
              "x-ratelimit-reset-after": "0"} if headers else {}
    return httpx.Response(status, headers=values, json={"retry_after": 0, "global": False})


def stub_http(monkeypatch, seen, *, result=None, execute=None):
    def construct(*, payload, webhook_type):
        async def send(**_kwargs):
            seen.append(payload["content"])
            if execute:
                return await execute(payload)
            return result if result is not None else response()
        return SimpleNamespace(webhook_id=payload["webhook_id"],
                               execute=AsyncMock(side_effect=send), edit=AsyncMock(side_effect=send))
    monkeypatch.setattr(service, "construct_webhook", construct)


async def deliver(red, queue=QUEUE):
    await service.dequeue_message(red=red, client=Mock(), queue_id=queue,
                                  bucket_data=None, lock=asyncio.Lock())


class RedisOutage:
    """A recoverable connection outage around the actual fixture Redis."""
    def __init__(self, red):
        self.red = red
        self.down = False
        self.failures = 0

    def __getattr__(self, name):
        if self.down:
            self.failures += 1
            raise redis.exceptions.ConnectionError("synthetic Redis interruption")
        return getattr(self.red, name)


def test_one_thousand_messages_survive_stopped_consumer_with_bounded_hints(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    expected = [f"synthetic-{index:04}" for index in range(1000)]
    for content in expected:
        service.enqueue_message(message(content), red=rt.red)

    assert outbox.summary() == {"queued": 1000}
    assert rt.red.llen(service.OUTBOX_WAKEUPS_KEY) <= service.WH_MAX_QUEUE_LENGTH
    # A wake-up index contains IDs, never the durable message or its token.
    assert all(b"synthetic-" not in value and b"fake-token" not in value
               for value in rt.red.lrange(service.OUTBOX_WAKEUPS_KEY, 0, -1))
    seen = []
    stub_http(monkeypatch, seen)

    async def drain():
        for _ in expected:
            await deliver(rt.red)
    asyncio.run(drain())

    assert seen == expected
    assert outbox.summary() == {"sent": 1000}
    assert all(row.payload is None for row in rows(rt))


def test_producer_accepts_into_sql_when_redis_is_down(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    fault = RedisOutage(rt.red)
    fault.down = True
    service.enqueue_message(message("accepted during outage"), red=fault)
    assert outbox.summary() == {"queued": 1}
    fault.down = False
    # No hint survived: SQL queue discovery must still find the delivery.
    assert QUEUE in outbox.pending_queues()
    seen = []
    stub_http(monkeypatch, seen)
    asyncio.run(deliver(fault))
    assert seen == ["accepted during outage"]
    assert outbox.summary() == {"sent": 1}


def test_failed_sql_persistence_is_not_reported_as_accepted(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    fail = Mock(side_effect=outbox.OutboxStorageError("synthetic storage outage"))
    monkeypatch.setattr(outbox, "enqueue", fail)
    with pytest.raises(outbox.OutboxStorageError):
        service.enqueue_message(message("not yet accepted"), red=rt.red)
    assert outbox.summary() == {}
    assert rt.red.llen(service.OUTBOX_WAKEUPS_KEY) == 0


def test_success_is_acknowledged_before_redis_metadata_and_needs_no_rate_headers(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    fault = RedisOutage(rt.red)
    service.enqueue_message(message("ack before metadata"), red=fault)
    seen = []

    async def received(_payload):
        fault.down = True
        return response(headers=False)
    stub_http(monkeypatch, seen, execute=received)
    asyncio.run(deliver(fault))
    assert outbox.summary() == {"sent": 1}
    fault.down = False
    asyncio.run(deliver(fault))
    assert seen == ["ack before metadata"]


def test_rate_limit_retains_payload_for_later_retry(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    service.enqueue_message(message("rate limited"), red=rt.red)
    seen = []
    stub_http(monkeypatch, seen, result=response(429))
    asyncio.run(deliver(rt.red))
    stored = rows(rt)
    assert len(stored) == 1 and stored[0].status == "queued" and stored[0].payload
    with rt.maker() as session, session.begin():
        session.execute(update(outbox.WebhookOutboxDelivery).values(
            available_at=datetime.now(timezone.utc) - timedelta(seconds=1)))
    stub_http(monkeypatch, seen)
    asyncio.run(deliver(rt.red))
    assert seen == ["rate limited", "rate limited"]
    assert outbox.summary() == {"sent": 1}


def test_old_durable_report_stays_reviewable_until_an_operator_explicitly_retries(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    service.enqueue_message(message("retained older report", old=True), red=rt.red)
    seen = []
    stub_http(monkeypatch, seen)
    asyncio.run(deliver(rt.red))
    assert seen == []
    assert outbox.summary() == {"review": 1}
    stored = rows(rt)
    assert stored[0].payload and stored[0].reason == "message_expired"
    assert outbox.retry_review(stored[0].message_id) is True
    asyncio.run(deliver(rt.red))
    assert seen == ["retained older report"]
    assert outbox.summary() == {"sent": 1}


@pytest.mark.parametrize("status", [400, 401, 403, 404])
def test_permanent_failure_retains_report_and_other_queued_messages(delivery_runtime, monkeypatch, status):
    rt = delivery_runtime
    service.enqueue_message(message("failed report"), red=rt.red)
    service.enqueue_message(message("later report"), red=rt.red)
    seen = []
    stub_http(monkeypatch, seen, result=response(status))
    asyncio.run(deliver(rt.red))
    stored = rows(rt)
    assert len(stored) == 2
    assert all(row.status in {"queued", "review"} and row.payload for row in stored)
    assert any(row.status == "review" for row in stored)


def test_transport_uncertainty_keeps_payload_reviewable_without_automatic_duplicate(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    service.enqueue_message(message("remote outcome unknown"), red=rt.red)
    seen = []

    async def lost_response(_payload):
        raise httpx.ReadTimeout("synthetic lost acknowledgement")
    stub_http(monkeypatch, seen, execute=lost_response)
    asyncio.run(deliver(rt.red))
    asyncio.run(deliver(rt.red))
    assert seen == ["remote outcome unknown"]
    assert outbox.summary() == {"review": 1}
    assert rows(rt)[0].payload


def test_http_acceptance_with_failed_sql_ack_is_retained_without_an_automatic_resend(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    service.enqueue_message(message("HTTP accepted but SQL acknowledgement failed"), red=rt.red)
    seen = []
    stub_http(monkeypatch, seen)
    original = outbox.finish

    def failed_ack(*args, **kwargs):
        if kwargs.get("status") == "sent":
            raise outbox.OutboxStorageError("synthetic acknowledgement outage")
        return original(*args, **kwargs)
    monkeypatch.setattr(outbox, "finish", failed_ack)
    try:
        asyncio.run(deliver(rt.red))
    except outbox.OutboxStorageError:
        pass
    assert seen == ["HTTP accepted but SQL acknowledgement failed"]
    stored = rows(rt)
    assert len(stored) == 1 and stored[0].status in {"sending", "review"} and stored[0].payload
    monkeypatch.setattr(outbox, "finish", original)
    with rt.maker() as session, session.begin():
        session.execute(update(outbox.WebhookOutboxDelivery).values(
            lease_until=datetime.now(timezone.utc) - timedelta(seconds=1)))
    outbox.recover_expired()
    asyncio.run(deliver(rt.red))
    assert seen == ["HTTP accepted but SQL acknowledgement failed"]
    assert outbox.summary() == {"review": 1}
    assert rows(rt)[0].payload


def test_claimed_crash_recovers_but_started_http_crash_requires_review(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    past = datetime.now(timezone.utc) - timedelta(minutes=10)
    first = outbox.enqueue(QUEUE, orjson.dumps(message("claim interrupted").model_dump_json()), 1, now=past)
    abandoned = outbox.claim(QUEUE, lease_seconds=1, now=past)
    assert abandoned and abandoned.id == first
    seen = []
    stub_http(monkeypatch, seen)
    asyncio.run(deliver(rt.red))
    assert seen == ["claim interrupted"]
    assert outbox.lookup(first)["status"] == "sent"

    second = outbox.enqueue(QUEUE, orjson.dumps(message("send interrupted").model_dump_json()), 1, now=past)
    sending = outbox.claim(QUEUE, lease_seconds=1, now=past)
    assert sending and outbox.mark_sending(sending.id, sending.token, now=past)
    asyncio.run(deliver(rt.red))
    assert seen == ["claim interrupted"]
    assert outbox.lookup(second)["status"] == "review"
    assert rows(rt)[1].payload


def test_slow_delivery_keeps_fifo_without_blocking_another_queue(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    service.enqueue_message(message("first"), red=rt.red)
    service.enqueue_message(message("second"), red=rt.red)
    service.enqueue_message(message("other", webhook_id="456"), red=rt.red)
    seen = []

    async def scenario():
        entered, release = asyncio.Event(), asyncio.Event()

        async def send(payload):
            if payload["content"] == "first":
                entered.set()
                await release.wait()
            return response()
        stub_http(monkeypatch, seen, execute=send)
        first = asyncio.create_task(deliver(rt.red))
        await asyncio.wait_for(entered.wait(), 5)
        try:
            await asyncio.wait_for(deliver(rt.red), 3)
            assert seen == ["first"]
            await asyncio.wait_for(deliver(rt.red, "whs:1:discord:audit:456"), 3)
            assert seen == ["first", "other"]
        finally:
            release.set()
            await asyncio.wait_for(first, 5)
        await deliver(rt.red)
    asyncio.run(scenario())
    assert seen == ["first", "other", "second"]
    assert outbox.summary() == {"sent": 3}


def test_legacy_messages_are_not_lost_if_sql_import_fails(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    rt.red.rpush(QUEUE, orjson.dumps(message("legacy pending").model_dump_json()))
    original = outbox.enqueue
    monkeypatch.setattr(outbox, "enqueue", Mock(side_effect=outbox.OutboxStorageError("synthetic import outage")))
    seen = []
    stub_http(monkeypatch, seen)
    try:
        asyncio.run(deliver(rt.red))
    except outbox.OutboxStorageError:
        pass
    assert seen == []
    monkeypatch.setattr(outbox, "enqueue", original)
    asyncio.run(deliver(rt.red))
    assert seen == ["legacy pending"]
    assert outbox.summary() == {"sent": 1}


def test_legacy_prefix_delivers_before_new_sql_messages(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    for index in range(3):
        rt.red.rpush(QUEUE, orjson.dumps(message(f"legacy-{index}").model_dump_json()))
    for index in range(2):
        service.enqueue_message(message(f"new-{index}"), red=rt.red)
    seen = []
    stub_http(monkeypatch, seen)

    async def drain():
        for _ in range(5):
            await deliver(rt.red)
    asyncio.run(drain())
    assert seen == ["legacy-0", "legacy-1", "legacy-2", "new-0", "new-1"]
    assert outbox.summary() == {"sent": 5}


def test_over_limit_legacy_queue_is_drained_without_trimming_reports(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    expected = [f"legacy-overflow-{index:03}" for index in range(200)]
    rt.red.rpush(QUEUE, *(orjson.dumps(message(content).model_dump_json()) for content in expected))
    assert rt.red.llen(QUEUE) > service.WH_MAX_QUEUE_LENGTH
    seen = []
    stub_http(monkeypatch, seen)

    async def drain():
        # Import batches may intentionally defer HTTP until the legacy prefix
        # has been committed. Allow those bounded migration-only passes.
        for _ in range(len(expected) + 25):
            await deliver(rt.red)
            if len(seen) == len(expected):
                break
    asyncio.run(drain())
    assert seen == expected
    assert rt.red.llen(QUEUE) == 0
    assert outbox.summary() == {"sent": len(expected)}


@pytest.mark.parametrize("native_already_sent", [False, True])
def test_legacy_transient_snapshot_cannot_replace_newer_native_state(delivery_runtime, monkeypatch, native_already_sent):
    rt = delivery_runtime
    queue = "whs:1:transient_identifier:discord:scoreboard:123:game"
    native = message("newer native scoreboard").model_copy(update={
        "message_type": service.WebhookMessageType.SCOREBOARD})
    native_id = service.enqueue_transient_message(native, message_group_key="game", red=rt.red)
    seen = []
    stub_http(monkeypatch, seen)
    if native_already_sent:
        asyncio.run(deliver(rt.red, queue))
        assert outbox.lookup(native_id)["status"] == "sent"

    legacy = message("older Redis scoreboard").model_copy(update={
        "message_type": service.WebhookMessageType.SCOREBOARD,
        "sent_at": datetime.now(timezone.utc) - timedelta(minutes=5)})
    rt.red.set(queue, orjson.dumps(legacy.model_dump_json()), ex=120)
    asyncio.run(deliver(rt.red, queue))

    assert seen == ["newer native scoreboard"]
    assert outbox.lookup(native_id)["status"] == "sent"
    assert outbox.summary() == {"sent": 1, "superseded": 1}
    assert rt.red.exists(queue) == 0
    with rt.maker() as session:
        state = session.scalar(select(outbox.WebhookOutboxQueue).where(
            outbox.WebhookOutboxQueue.queue_id == queue))
        assert state.native_snapshot_seen is True


def test_reset_legacy_backlog_over_one_thousand_keeps_every_later_import_review_only(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    count = 1200
    rt.red.rpush(QUEUE, *(orjson.dumps(message(f"legacy-reset-{index:04}").model_dump_json())
                         for index in range(count)))
    seen = []
    stub_http(monkeypatch, seen)
    assert service.reset_queue(QUEUE, red=rt.red) is True
    assert rt.red.llen(QUEUE) == count - service.LEGACY_IMPORT_BATCH
    assert outbox.summary() == {"review": service.LEGACY_IMPORT_BATCH}
    with rt.maker() as session:
        state = session.scalar(select(outbox.WebhookOutboxQueue).where(
            outbox.WebhookOutboxQueue.queue_id == QUEUE))
        assert state.legacy_review is True

    native_id = service.enqueue_message(message("native report accepted after reset"), red=rt.red)
    assert outbox.lookup(native_id)["status"] == "queued"

    async def drain():
        for _ in range(count // service.LEGACY_IMPORT_BATCH + 3):
            await deliver(rt.red)
            if rt.red.llen(QUEUE) == 0:
                break
            assert seen == []
    asyncio.run(drain())

    assert seen == ["native report accepted after reset"]
    assert rt.red.llen(QUEUE) == 0
    assert outbox.summary() == {"review": count, "sent": 1}
    assert sum(bool(row.payload) for row in rows(rt)) == count
    with rt.maker() as session:
        state = session.scalar(select(outbox.WebhookOutboxQueue).where(
            outbox.WebhookOutboxQueue.queue_id == QUEUE))
        assert state.legacy_review is False


def test_stale_legacy_empty_observation_cannot_clear_a_newer_operator_reset(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    outbox.review_queue(QUEUE)
    first_generation = outbox.get_legacy_review_generation(QUEUE)
    assert first_generation
    raw = orjson.dumps(message("legacy report arriving during reset cleanup").model_dump_json())
    later_generations = []

    class ConcurrentReset:
        def exists(self, key):
            observed = rt.red.exists(key)
            if key == QUEUE and not later_generations:
                assert observed == 0
                # The helper already captured generation A. Its empty Redis
                # observation is now stale: a producer and reset B intervene.
                rt.red.rpush(QUEUE, raw)
                outbox.review_queue(QUEUE)
                later_generations.append(outbox.get_legacy_review_generation(QUEUE))
            return observed

        def __getattr__(self, name):
            return getattr(rt.red, name)

    service._clear_legacy_reset_if_empty(ConcurrentReset(), QUEUE)
    assert len(later_generations) == 1 and later_generations[0] != first_generation
    assert outbox.get_legacy_review_generation(QUEUE) == later_generations[0]
    assert rt.red.lrange(QUEUE, 0, -1) == [raw]

    seen = []
    stub_http(monkeypatch, seen)
    asyncio.run(deliver(rt.red))
    assert seen == []
    assert outbox.summary() == {"review": 1}
    stored = rows(rt)
    assert len(stored) == 1 and stored[0].payload == raw
    assert rt.red.llen(QUEUE) == 0
    # Clearing B is permitted only after its own payload is safely archived.
    assert outbox.get_legacy_review_generation(QUEUE) is None


@pytest.mark.parametrize("failure_point", ["before_ack", "after_ack"])
@pytest.mark.parametrize("missing_fields", [("id",), ("failed_at",), ("id", "failed_at")])
def test_legacy_archive_without_identity_or_time_is_quarantined_once_across_ack_failure(delivery_runtime, monkeypatch, failure_point, missing_fields):
    rt = delivery_runtime
    entry = service.DeadLetterWebhookMessage(message=message("legacy archival report"),
        source_queue_id=QUEUE, reason="transport_error")
    document = entry.model_dump(mode="json")
    for field in missing_fields:
        document.pop(field)
    raw = orjson.dumps(document)
    rt.red.rpush(service.DEAD_LETTER_QUEUE, raw)
    original = webhook_legacy.ack_stage

    def interrupted_ack(*args, **kwargs):
        if failure_point == "after_ack":
            assert original(*args, **kwargs) is True
        raise redis.exceptions.ConnectionError("synthetic lost archive acknowledgement")
    monkeypatch.setattr(webhook_legacy, "ack_stage", interrupted_ack)
    with pytest.raises(redis.exceptions.ConnectionError):
        service._import_legacy_dead_letters(rt.red, limit=1)
    first = rows(rt)
    assert len(first) == 1 and first[0].payload == raw
    assert first[0].status == "review" and first[0].reason == "invalid_legacy_archive"
    stable_id = first[0].message_id
    assert rt.red.llen(service.DEAD_LETTER_QUEUE) == (1 if failure_point == "before_ack" else 0)

    monkeypatch.setattr(webhook_legacy, "ack_stage", original)
    service._import_legacy_dead_letters(rt.red, limit=1)
    service._import_legacy_dead_letters(rt.red, limit=1)
    final = rows(rt)
    assert len(final) == 1 and final[0].message_id == stable_id
    assert final[0].payload == raw and final[0].status == "review"
    assert rt.red.llen(service.DEAD_LETTER_QUEUE) == 0
    assert outbox.summary() == {"review": 1}


def test_malformed_legacy_message_is_retained_for_review(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    malformed = b"synthetic malformed report payload"
    rt.red.rpush(QUEUE, malformed)
    seen = []
    stub_http(monkeypatch, seen)
    asyncio.run(deliver(rt.red))
    assert seen == []
    stored = rows(rt)
    assert len(stored) == 1 and stored[0].status == "review"
    assert stored[0].payload == malformed


def test_main_reconnects_and_sql_poll_recovers_a_missing_wakeup(delivery_runtime, monkeypatch):
    rt = delivery_runtime
    fault = RedisOutage(rt.red)
    fault.down = True
    service.enqueue_message(message("queued without Redis"), red=fault)
    assert rt.red.llen(service.OUTBOX_WAKEUPS_KEY) == 0
    monkeypatch.setattr(service, "get_redis_client", lambda *a, **kw: fault)
    monkeypatch.setattr(service, "construct_redis_url", lambda *a, **kw: "redis://synthetic.invalid/15")
    seen = []

    async def scenario():
        stopped = asyncio.Event()

        async def accepted(_payload):
            # main must drain an already accepted response before exiting,
            # rather than canceling the SQL acknowledgement on shutdown.
            stopped.set()
            return response()
        stub_http(monkeypatch, seen, execute=accepted)
        fault.failures = 0
        worker = asyncio.create_task(service.main(stop_event=stopped))
        try:
            await asyncio.sleep(0.15)
            assert fault.failures > 0
            assert not worker.done()
            assert not stopped.is_set()
            fault.down = False
            await asyncio.wait_for(stopped.wait(), 12)
            await asyncio.wait_for(worker, 12)
        finally:
            fault.down = False
            stopped.set()
            if not worker.done():
                try:
                    await asyncio.wait_for(worker, 12)
                except TimeoutError:
                    worker.cancel()
                    await asyncio.gather(worker, return_exceptions=True)
    asyncio.run(scenario())
    assert seen == ["queued without Redis"]
    assert outbox.summary() == {"sent": 1}
