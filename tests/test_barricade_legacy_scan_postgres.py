"""Legacy scan delivery is recorded without inventing a peer identity."""
import asyncio
import os
from datetime import datetime, timedelta
from unittest.mock import AsyncMock, patch
from sqlalchemy import select

import pytest
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api import barricade

from rcon import barricade_scan_journal as journal
from rcon import barricade_legacy_dispatch as legacy
from rcon import barricade_scan_dispatch as durable
from tests.test_barricade_scan_journal_postgres import database, prepare, prepare_adapter, verified


def test_actual_legacy_consumer_journals_lost_reply_before_advancing(database, monkeypatch):
    prepare(database, monkeypatch)
    monkeypatch.setattr(barricade, 'get_server_number', lambda: '3')
    async def run():
        consumer = barricade.BarricadeConsumer()
        initial = datetime(2026, 1, 1, 12)
        later = initial + timedelta(seconds=1)
        query = AsyncMock(side_effect=[[('synthetic-eos', later, 11)], []])
        consumer.send_request = AsyncMock(side_effect=OSError('synthetic lost response'))
        with patch.object(barricade, 'get_most_recent_session_date', AsyncMock(return_value=initial)), \
             patch.object(barricade, 'get_joined_players_since', query), \
             patch.object(barricade.asyncio, 'sleep', AsyncMock(side_effect=[None, None, asyncio.CancelledError])):
            with pytest.raises(asyncio.CancelledError):
                await consumer._scan_players_loop()
        consumer.send_request.assert_awaited_once()
        assert query.await_args_list[1].args[0] == later
        rows = journal.list_reviews(3)['results']
        assert len(rows) == 1 and rows[0]['player_session_id'] == 11
        assert rows[0]['identity_kind'] == 'unbound_connection' and rows[0]['status'] == 'review'
    asyncio.run(run())


def test_lost_reply_retained_for_review_and_never_replayed(database, monkeypatch):
    prepare(database, monkeypatch)
    namespace = 'unbound:0123456789abcdef0123456789abcdef'
    sender = AsyncMock(side_effect=OSError('synthetic lost reply'))
    rows = [('synthetic-eos', 11), ('synthetic-eos-two', 12)]
    assert asyncio.run(legacy.dispatch(3, namespace, rows, 'HLLV', sender)) == 'review'
    assert asyncio.run(legacy.dispatch(3, namespace, rows, 'HLLV', sender)) == 'already_recorded'
    sender.assert_awaited_once()
    reviews = journal.list_reviews(3)['results']
    assert {item['player_session_id'] for item in reviews} == {11, 12}
    assert all(item['integration_id'] == namespace and item['identity_kind'] == 'unbound_connection' for item in reviews)
    with pytest.raises(ValueError, match='unbound'):
        journal.resolve_review(3, namespace, reviews[0]['id'], decision='retry', actor='operator', reason='test')
    journal.resolve_review(3, namespace, reviews[0]['id'], decision='dismissed', actor='operator', reason='checked')
    assert len(journal.list_reviews(3)['results']) == 1


def test_failed_reservation_never_sends(database, monkeypatch):
    prepare(database, monkeypatch)
    namespace = 'unbound:fedcba9876543210fedcba9876543210'
    sender = AsyncMock()
    monkeypatch.setattr(journal, 'reserve', lambda *_: (_ for _ in ()).throw(OSError('db unavailable')))
    with pytest.raises(OSError):
        asyncio.run(legacy.dispatch(3, namespace, [('synthetic-eos', 11)], 'HLLV', sender))
    sender.assert_not_awaited()


def test_success_recorded_without_review(database, monkeypatch):
    prepare(database, monkeypatch)
    sender = AsyncMock(return_value=None)
    namespace = 'unbound:0123456789abcdef0123456789abcdef'
    assert asyncio.run(legacy.dispatch(3, namespace, [('synthetic-eos', 11)], 'HLLV', sender)) == 'done'
    sender.assert_awaited_once_with(['synthetic-eos'], 'HLLV')
    assert journal.list_reviews(3)['results'] == []


def test_later_unbound_connection_never_replays_uncertain_session(database, monkeypatch):
    prepare(database, monkeypatch)
    first = 'unbound:0123456789abcdef0123456789abcdef'
    second = 'unbound:fedcba9876543210fedcba9876543210'
    sender = AsyncMock(side_effect=OSError('synthetic lost response'))
    assert asyncio.run(legacy.dispatch(3, first, [('synthetic-eos', 11)], 'HLLV', sender)) == 'review'
    next_sender = AsyncMock()
    assert asyncio.run(legacy.dispatch(3, second, [('synthetic-eos', 11)], 'HLLV', next_sender)) == 'already_recorded'
    next_sender.assert_not_awaited()
    reviews = journal.list_reviews(3)['results']
    assert {row['integration_id'] for row in reviews} == {first, second}
    assert {row['review_cause'] for row in reviews} == {'uncertain_delivery', 'prior_unbound_uncertain'}
    assert all(row['identity_kind'] == 'unbound_connection' for row in reviews)
    later = next(row for row in reviews if row['integration_id'] == second)
    with pytest.raises(ValueError, match='not sent'):
        journal.resolve_review(3, second, later['id'], decision='confirmed', actor='operator', reason='test')
    # A different, verified session is not globally blocked.
    assert asyncio.run(legacy.dispatch(3, second, [('synthetic-eos', 12)], 'HLLV', next_sender)) == 'done'
    next_sender.assert_awaited_once()


def test_other_unbound_connection_does_not_resend_while_first_is_in_flight(database, monkeypatch):
    prepare(database, monkeypatch)
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def first_sender(_players, _game):
            entered.set()
            await release.wait()
            raise OSError('synthetic lost response')
        first = 'unbound:0123456789abcdef0123456789abcdef'
        second = 'unbound:fedcba9876543210fedcba9876543210'
        task = asyncio.create_task(legacy.dispatch(3, first, [('synthetic-eos', 11)], 'HLLV', first_sender))
        await asyncio.wait_for(entered.wait(), 5)
        next_sender = AsyncMock()
        try:
            assert await legacy.dispatch(3, second, [('synthetic-eos', 11)], 'HLLV', next_sender) == 'already_recorded'
            next_sender.assert_not_awaited()
        finally:
            release.set()
        assert await asyncio.wait_for(task, 5) == 'review'
        assert {row['review_cause'] for row in journal.list_reviews(3)['results']} == {
            'uncertain_delivery', 'prior_unbound_uncertain'}
    asyncio.run(run())


def test_registered_connection_does_not_replay_prior_unbound_uncertainty(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    unbound = 'unbound:0123456789abcdef0123456789abcdef'
    registered = 'integration:01234567-89ab-4def-8012-0123456789ab'
    lost = AsyncMock(side_effect=OSError('synthetic lost response'))
    assert asyncio.run(legacy.dispatch(3, unbound, [('synthetic-eos', 11)], 'HLLV', lost)) == 'review'
    sender = AsyncMock()
    assert asyncio.run(durable.dispatch(3, registered, 11, 'synthetic-eos', 'HLLV', sender,
                                        credential_id=1, verify_session=verified)) == 'already_recorded'
    sender.assert_not_awaited()
    row = next(item for item in journal.list_reviews(3)['results'] if item['integration_id'] == registered)
    assert row['identity_kind'] == 'registered_integration' and row['review_cause'] == 'prior_unbound_uncertain'
    with pytest.raises(ValueError, match='prior unattributed'):
        journal.resolve_review(3, registered, row['id'], decision='retry', actor='operator', reason='test')


def test_registered_previously_queued_retry_is_returned_to_review(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    unbound = 'unbound:0123456789abcdef0123456789abcdef'
    registered = 'integration:01234567-89ab-4def-8012-0123456789ab'
    with journal.delivery_scope(3, registered):
        ident = journal.reserve(3, registered, 11, 'synthetic-eos', 'HLLV')
        assert journal.finish(ident, 3, registered, confirmed=False)
    journal.resolve_review(3, registered, ident, decision='retry', actor='operator', reason='prior review')
    lost = AsyncMock(side_effect=OSError('synthetic lost response'))
    assert asyncio.run(legacy.dispatch(3, unbound, [('synthetic-eos', 11)], 'HLLV', lost)) == 'review'
    sender = AsyncMock()
    assert asyncio.run(durable.dispatch(3, registered, 11, 'synthetic-eos', 'HLLV', sender,
                                        credential_id=1, verify_session=verified)) == 'already_recorded'
    sender.assert_not_awaited()
    row = next(item for item in journal.list_reviews(3)['results'] if item['id'] == ident)
    assert row['review_cause'] == 'prior_unbound_uncertain' and row['status'] == 'review'


def test_registered_scan_does_not_race_inflight_unbound_send(database, monkeypatch):
    prepare_adapter(database, monkeypatch)
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def unbound_sender(_players, _game):
            entered.set()
            await release.wait()
            raise OSError('synthetic lost response')
        unbound = 'unbound:0123456789abcdef0123456789abcdef'
        registered = 'integration:01234567-89ab-4def-8012-0123456789ab'
        first = asyncio.create_task(legacy.dispatch(3, unbound, [('synthetic-eos', 11)], 'HLLV', unbound_sender))
        await asyncio.wait_for(entered.wait(), 5)
        later = AsyncMock()
        try:
            result = await durable.dispatch(3, registered, 11, 'synthetic-eos', 'HLLV', later,
                                            credential_id=1, verify_session=verified)
            assert result == 'already_recorded'
            later.assert_not_awaited()
        finally:
            release.set()
        assert await asyncio.wait_for(first, 5) == 'review'
    asyncio.run(run())


def test_partial_reservation_failure_does_not_send_and_is_reviewable(database, monkeypatch):
    prepare(database, monkeypatch)
    original = journal.reserve
    calls = []
    def fail_second(*args):
        calls.append(args)
        if len(calls) == 2:
            raise OSError('synthetic database failure')
        return original(*args)
    monkeypatch.setattr(journal, 'reserve', fail_second)
    sender = AsyncMock()
    namespace = 'unbound:0123456789abcdef0123456789abcdef'
    with pytest.raises(OSError):
        asyncio.run(legacy.dispatch(3, namespace, [('one', 11), ('two', 12)], 'HLLV', sender))
    sender.assert_not_awaited()
    reviews = journal.list_reviews(3)['results']
    assert len(reviews) == 1 and reviews[0]['player_session_id'] == 11


def test_interrupted_sending_is_visible_and_recoverable_without_resend(database, monkeypatch):
    prepare(database, monkeypatch)
    namespace = 'unbound:0123456789abcdef0123456789abcdef'
    with journal.delivery_scope(3, namespace):
        ident = journal.reserve(3, namespace, 11, 'synthetic-eos', 'HLLV')
    row = journal.list_reviews(3)['results'][0]
    assert row['id'] == ident and row['status'] == 'sending'
    journal.resolve_review(3, namespace, ident, decision='recover', actor='operator', reason='sender interrupted')
    row = journal.list_reviews(3)['results'][0]
    assert row['status'] == 'review' and row['identity_kind'] == 'unbound_connection'
    with pytest.raises(ValueError, match='unbound'):
        journal.resolve_review(3, namespace, ident, decision='retry', actor='operator', reason='test')


def test_connection_cancellation_records_uncertain_delivery(database, monkeypatch):
    prepare(database, monkeypatch)
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def sender(_players, _game):
            entered.set()
            await release.wait()
        namespace = 'unbound:0123456789abcdef0123456789abcdef'
        task = asyncio.create_task(legacy.dispatch(3, namespace, [('synthetic-eos', 11)], 'HLLV', sender))
        await asyncio.wait_for(entered.wait(), 5)
        task.cancel()
        with pytest.raises(asyncio.CancelledError):
            await task
        release.set()
        def status():
            with database() as session:
                return session.scalar(select(journal.BarricadeScanDelivery.status))
        for _ in range(100):
            value = await asyncio.to_thread(status)
            if value != 'sending':
                break
            await asyncio.sleep(.02)
        assert value in ('review', 'done')
        # A cancelled waiter is not evidence that the remote action failed.
        if value == 'review':
            assert journal.list_reviews(3)['results'][0]['identity_kind'] == 'unbound_connection'
    asyncio.run(run())


def test_review_waits_for_active_sender_and_cannot_overwrite_success(database, monkeypatch):
    prepare(database, monkeypatch)
    async def run():
        entered, release = asyncio.Event(), asyncio.Event()
        async def sender(_players, _game):
            entered.set()
            await release.wait()
        namespace = 'unbound:0123456789abcdef0123456789abcdef'
        task = asyncio.create_task(legacy.dispatch(3, namespace, [('synthetic-eos', 11)], 'HLLV', sender))
        await asyncio.wait_for(entered.wait(), 5)
        row = journal.list_reviews(3)['results'][0]
        review = asyncio.create_task(asyncio.to_thread(journal.resolve_review, 3, namespace, row['id'],
            decision='recover', actor='operator', reason='check'))
        await asyncio.sleep(.2)
        assert not review.done()
        release.set()
        assert await asyncio.wait_for(task, 5) == 'done'
        with pytest.raises(ValueError, match='not awaiting'):
            await asyncio.wait_for(review, 5)
        assert journal.list_reviews(3)['results'] == []
    asyncio.run(run())
