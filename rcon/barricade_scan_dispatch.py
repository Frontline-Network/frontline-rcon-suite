"""Experimental async adapter for durable Barricade scan delivery.

Not wired to the consumer: caller identity, session discovery and review UI
must be resolved before it can replace the production scan loop.
"""
import asyncio
from contextvars import Context
from threading import Event
import logging

from rcon import barricade_scan_journal as journal

logger = logging.getLogger(__name__)


def key_is_live(credential_id):
    from api.barricade_scan_auth import current_credential_is_authorized
    return current_credential_is_authorized(credential_id)


async def scan_once(server_number, integration_id, game, sender, is_present, *, credential_id,
                    is_observed=None, page_size=100):
    """Traverse once; ambiguous activation or presence is deferred, not sent.

    This is experimental: a boundary compares two clocks and cannot prove that
    a game server exposes all log events promptly or uses a synchronized clock.
    """
    boundary = await asyncio.to_thread(journal.registration_boundary, server_number, integration_id, credential_id)
    if boundary is None:
        return 'unauthorized'
    async def record_review(session_id, player_id, cause):
        def record():
            with journal.delivery_scope(server_number, integration_id):
                if (journal.credential_is_registered(server_number, integration_id, credential_id)
                        and key_is_live(credential_id) is True):
                    journal.mark_activation_review(server_number, integration_id, session_id, player_id, game, cause)
        await asyncio.to_thread(record)

    after_id = 0
    while True:
        rows = await asyncio.to_thread(journal.find_unreserved_open_sessions,
                                       server_number, integration_id, after_id=after_id, limit=page_size,
                                       include_start=True)
        if not rows:
            break
        for session_id, player_id, start_event_us, delivery_status in rows:
            after_id = session_id
            classification = journal.classify_activation_start(boundary, start_event_us)
            if delivery_status != 'queued' and classification in ('before', 'ambiguous', 'unknown'):
                # Historical open rows alone do not mean the player is online.
                # Do not flood the review queue with stale records. Unknown
                # roster state is retried on the next traversal.
                if is_observed is not None and await is_observed(session_id, player_id) is True:
                    await record_review(session_id, player_id, 'activation_' + classification)
                continue
            if delivery_status != 'queued' and classification != 'after':
                continue
            await dispatch(server_number, integration_id, session_id, player_id, game, sender,
                           credential_id=credential_id, verify_session=is_present)
        if len(rows) < page_size:
            break
    after_id = 0
    while True:
        rows = await asyncio.to_thread(journal.find_unreserved_recent_closed_sessions,
            server_number, integration_id, boundary, after_id=after_id, limit=page_size)
        if not rows:
            return
        for session_id, player_id in rows:
            after_id = session_id
            await record_review(session_id, player_id, 'session_ended_before_scan')
        if len(rows) < page_size:
            return


async def dispatch(server_number, integration_id, session_id, player_id, game, sender, *, credential_id, verify_session, timeout=15):
    """Send once; a lost response leaves durable review, never an auto-retry."""
    loop = asyncio.get_running_loop()
    cancelled = Event()

    def worker():
        with journal.delivery_scope(server_number, integration_id):
            if cancelled.is_set():
                return 'cancelled'
            if (not journal.credential_is_registered(server_number, integration_id, credential_id)
                    or key_is_live(credential_id) is not True):
                return 'unauthorized'
            journal.recover_interrupted(server_number, integration_id)
            # Verify after acquiring the send lock: a previous snapshot may be
            # stale after waiting for another request or a credential rotation.
            presence = None
            try:
                presence = Context().run(asyncio.run_coroutine_threadsafe,
                                         verify_session(session_id, player_id), loop)
                if presence.result(timeout=timeout) is not True:
                    return 'deferred'
            except Exception:
                if presence is not None:
                    presence.cancel()
                return 'deferred'
            if cancelled.is_set():
                return 'cancelled'
            # The asynchronous presence check may take several seconds. A
            # key or its user's permissions can be revoked while it runs.
            if (not journal.credential_is_registered(server_number, integration_id, credential_id)
                    or key_is_live(credential_id) is not True):
                return 'unauthorized'
            delivery_id = journal.reserve(server_number, integration_id, session_id, player_id, game)
            if delivery_id is None:
                return 'already_recorded'
            if cancelled.is_set():
                journal.finish(delivery_id, server_number, integration_id, confirmed=False)
                return 'review'
            # A revocation during the database reservation must not start an
            # external request. Keep the durable record for explicit review.
            if (not journal.credential_is_registered(server_number, integration_id, credential_id)
                    or key_is_live(credential_id) is not True):
                journal.finish(delivery_id, server_number, integration_id, confirmed=False)
                return 'review'
            response = None
            try:
                # Keep the database lock's context out of the event-loop task.
                response = Context().run(asyncio.run_coroutine_threadsafe,
                                         sender(player_id, game), loop)
                response.result(timeout=timeout)
            except Exception:
                if response is not None:
                    response.cancel()
                journal.finish(delivery_id, server_number, integration_id, confirmed=False)
                return 'review'
            if not journal.finish(delivery_id, server_number, integration_id, confirmed=True):
                raise RuntimeError('Barricade scan confirmation was not recorded')
            return 'done'

    task = Context().run(asyncio.create_task, asyncio.to_thread(worker))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        cancelled.set()
        # The worker holds the lock until the remote outcome is recorded.
        # Observe exceptions even if the caller no longer awaits the task.
        def observe(future):
            if not future.cancelled():
                exc = future.exception()
                if exc is not None:
                    logger.error('Cancelled Barricade scan worker failed', exc_info=(type(exc), exc, exc.__traceback__))
        task.add_done_callback(observe)
        raise
