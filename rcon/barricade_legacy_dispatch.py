"""Journal legacy scan attempts without attributing them to a peer."""
import asyncio
import logging
from contextvars import Context
from threading import Event
from uuid import UUID

from rcon import barricade_scan_journal as journal

logger = logging.getLogger(__name__)


def _valid_namespace(namespace):
    if not isinstance(namespace, str) or not namespace.startswith('unbound:'):
        return False
    try:
        return UUID(hex=namespace.removeprefix('unbound:')).hex == namespace.removeprefix('unbound:')
    except ValueError:
        return False


async def dispatch(server_number, namespace, rows, game, sender, *, timeout=15):
    """Journal the batch before sending and never retry an uncertain result.

    The random namespace identifies only this connection attempt. It is not a
    credential, integration or assertion that another connection is distinct.
    """
    if not _valid_namespace(namespace):
        raise ValueError('Invalid unbound scan namespace')
    loop = asyncio.get_running_loop()
    cancelled = Event()

    def worker():
        with journal.delivery_scope(server_number, namespace):
            if cancelled.is_set():
                return 'cancelled'
            journal.recover_interrupted(server_number, namespace)
            reserved = []
            try:
                for player_id, session_id in rows:
                    delivery_id = journal.reserve_unbound(server_number, namespace, session_id, player_id, game)
                    if delivery_id is not None:
                        reserved.append((delivery_id, player_id))
            except Exception:
                for delivery_id, _ in reserved:
                    journal.finish(delivery_id, server_number, namespace, confirmed=False)
                raise
            if not reserved:
                return 'already_recorded'
            if cancelled.is_set():
                for delivery_id, _ in reserved:
                    journal.finish(delivery_id, server_number, namespace, confirmed=False)
                return 'review'
            response = None
            try:
                response = Context().run(asyncio.run_coroutine_threadsafe,
                    sender([player_id for _, player_id in reserved], game), loop)
                response.result(timeout=timeout)
            except Exception:
                if response is not None:
                    response.cancel()
                for delivery_id, _ in reserved:
                    journal.finish(delivery_id, server_number, namespace, confirmed=False)
                return 'review'
            for delivery_id, _ in reserved:
                if not journal.finish(delivery_id, server_number, namespace, confirmed=True):
                    raise RuntimeError('Unbound scan confirmation was not recorded')
            return 'done'

    task = Context().run(asyncio.create_task, asyncio.to_thread(worker))
    try:
        return await asyncio.shield(task)
    except asyncio.CancelledError:
        cancelled.set()
        def observe(future):
            if not future.cancelled() and future.exception() is not None:
                logger.error('Cancelled unbound Barricade scan worker failed', exc_info=future.exception())
        task.add_done_callback(observe)
        raise
