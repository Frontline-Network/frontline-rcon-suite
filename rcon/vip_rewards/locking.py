"""Session advisory locks shared by API, Seed-VIP and reward workers."""

from contextlib import contextmanager
from contextvars import ContextVar
import hashlib
from time import monotonic, sleep
from functools import wraps

from sqlalchemy import text

_held = ContextVar("vip_reward_locks", default=frozenset())


@contextmanager
def lock(key):
    from rcon.models import get_engine

    number = int.from_bytes(
        hashlib.sha256(key.encode()).digest()[:8], "big", signed=True
    )
    held = _held.get()
    if number in held:
        yield
        return
    # A dedicated connection keeps the advisory lock across journal commits and RCON I/O.
    with get_engine().connect() as connection:
        deadline = monotonic() + 15
        while not connection.execute(
            text("SELECT pg_try_advisory_lock(:key)"), {"key": number}
        ).scalar():
            if monotonic() >= deadline:
                raise TimeoutError("VIP operation is busy; no action was attempted")
            sleep(0.1)
        token = _held.set(held | {number})
        try:
            yield
        finally:
            _held.reset(token)
            connection.execute(text("SELECT pg_advisory_unlock(:key)"), {"key": number})


def vip_lock(player_id):
    from rcon.utils import get_server_number

    return lock(f"vip:{get_server_number()}:{player_id}")


def switch_state_lock():
    from rcon.utils import get_server_number

    return lock(f"vip-rewards-switch-state:{get_server_number()}")


def serialized_vip(func):
    @wraps(func)
    def wrapped(self, player_id, *args, **kwargs):
        with vip_lock(player_id):
            return func(self, player_id, *args, **kwargs)

    return wrapped
