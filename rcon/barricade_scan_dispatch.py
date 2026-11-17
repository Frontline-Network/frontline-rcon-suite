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


async def scan_once(server_number, integration_id, game, sender, is_present, *, credential_id, page_size=100):
    """Traverse once; unknown presence is skipped and the next pass starts at zero."""
    after_id = 0
    while True:
        rows = await asyncio.to_thread(journal.find_unreserved_open_sessions,
                                       server_number, integration_id, after_id=after_id, limit=page_size)
        if not rows:
            return
        for session_id, player_id in rows:
            after_id = session_id
            # A live player ID alone does not prove this particular history
            # session is current: an old orphan may have the same player ID.
            if await is_present(session_id, player_id) is not True:
                continue
            await dispatch(server_number, integration_id, session_id, player_id, game, sender, credential_id=credential_id)
        if len(rows) < page_size:
            return


async def dispatch(server_number, integration_id, session_id, player_id, game, sender, *, credential_id, timeout=15):
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
            delivery_id = journal.reserve(server_number, integration_id, session_id, player_id, game)
            if delivery_id is None:
                return 'already_recorded'
            if cancelled.is_set():
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
