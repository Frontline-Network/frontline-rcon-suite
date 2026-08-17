"""Shared runtime for compatible long-lived supervisor services.

The selected services are I/O-bound loops for one game server. Running them in
threads preserves independent RCON connections (``ServerCtl`` is thread-aware)
while sharing the Python interpreter and imported modules.
"""

from __future__ import annotations

import logging
import threading
from collections.abc import Callable, Sequence
from dataclasses import dataclass

logger = logging.getLogger(__name__)

RESTART_DELAY_SECONDS = 5.0
MONITOR_INTERVAL_SECONDS = 5.0


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    target: Callable[[], None]


def _run_expiring_vips() -> None:
    from rcon.expiring_vips import service

    service.run()


def _run_live_stats() -> None:
    from rcon.player_stats import live_stats_loop

    live_stats_loop()


def _run_autobalancer() -> None:
    from rcon.autobalancer import service

    service.run()


def _run_blacklists() -> None:
    from rcon.blacklist import BlacklistCommandHandler

    BlacklistCommandHandler().run()


def _run_log_recorder() -> None:
    from rcon.logs.recorder import LogRecorder

    LogRecorder(10).run()


def _run_routines() -> None:
    from rcon import routines

    routines.run()


DEFAULT_SERVICES: tuple[ServiceSpec, ...] = (
    ServiceSpec("expiring_vips", _run_expiring_vips),
    ServiceSpec("live_stats", _run_live_stats),
    ServiceSpec("autobalancer", _run_autobalancer),
    ServiceSpec("blacklists", _run_blacklists),
    ServiceSpec("log_recorder", _run_log_recorder),
    ServiceSpec("routines", _run_routines),
)


def _service_loop(
    spec: ServiceSpec,
    stop_event: threading.Event,
    restart_delay: float = RESTART_DELAY_SECONDS,
) -> None:
    while not stop_event.is_set():
        try:
            logger.info("Starting shared supervisor service %s", spec.name)
            spec.target()
            logger.warning("Shared supervisor service %s returned", spec.name)
        except Exception:
            logger.exception("Shared supervisor service %s stopped", spec.name)

        if stop_event.wait(restart_delay):
            return


def _start_service(
    spec: ServiceSpec, stop_event: threading.Event
) -> threading.Thread:
    thread = threading.Thread(
        target=_service_loop,
        args=(spec, stop_event),
        name=f"frontline-{spec.name}",
        daemon=True,
    )
    thread.start()
    return thread


def run(services: Sequence[ServiceSpec] = DEFAULT_SERVICES) -> None:
    # Initialize the shared, thread-aware controller before workers race to use
    # it. ServerCtl keeps a separate socket per calling thread.
    from rcon.cache_utils import get_redis_client
    from rcon.rcon import get_rcon

    get_rcon()
    get_redis_client()

    stop_event = threading.Event()
    threads = {spec.name: _start_service(spec, stop_event) for spec in services}

    try:
        while not stop_event.wait(MONITOR_INTERVAL_SECONDS):
            for spec in services:
                thread = threads[spec.name]
                if not thread.is_alive():
                    logger.error(
                        "Shared supervisor thread %s died; restarting", spec.name
                    )
                    threads[spec.name] = _start_service(spec, stop_event)
    except KeyboardInterrupt:
        logger.info("Stopping shared supervisor runtime")
    finally:
        stop_event.set()
        for thread in threads.values():
            thread.join(timeout=1)
