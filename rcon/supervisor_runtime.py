"""Shared runtime for compatible long-lived supervisor services.

The selected services are I/O-bound loops for one game server. Running them in
threads preserves independent RCON connections (``ServerCtl`` is thread-aware)
while sharing the Python interpreter and imported modules.
"""

from __future__ import annotations

import logging
import threading
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass

logger = logging.getLogger(__name__)

RESTART_DELAY_SECONDS = 5.0
MONITOR_INTERVAL_SECONDS = 1.0
STATE_KEY = "frontline:supervisor_runtime:services"
RUNNING = "RUNNING"
STOPPED = "STOPPED"


def redis_text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def decode_service_state(raw_state: dict) -> dict[str, str]:
    return {
        str(redis_text(key)): str(redis_text(value))
        for key, value in raw_state.items()
    }


@dataclass(frozen=True)
class ServiceSpec:
    name: str
    target: Callable[[threading.Event], None]


def _run_expiring_vips(stop_event: threading.Event) -> None:
    from rcon.expiring_vips import service

    service.run(stop_event=stop_event)


def _run_live_stats(stop_event: threading.Event) -> None:
    from rcon.player_stats import live_stats_loop

    live_stats_loop(stop_event=stop_event)


def _run_autobalancer(stop_event: threading.Event) -> None:
    from rcon.autobalancer import service

    service.run(stop_event=stop_event)


def _run_blacklists(stop_event: threading.Event) -> None:
    from rcon.blacklist import BlacklistCommandHandler

    BlacklistCommandHandler().run(stop_event=stop_event)


def _run_log_recorder(stop_event: threading.Event) -> None:
    from rcon.logs.recorder import LogRecorder

    LogRecorder(10).run(stop_event=stop_event)


def _run_routines(stop_event: threading.Event) -> None:
    from rcon import routines

    routines.run(stop_event=stop_event)


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
            spec.target(stop_event)
            if not stop_event.is_set():
                logger.warning("Shared supervisor service %s returned", spec.name)
        except Exception:
            logger.exception("Shared supervisor service %s stopped", spec.name)

        if stop_event.wait(restart_delay):
            return


def _start_service(spec: ServiceSpec, stop_event: threading.Event) -> threading.Thread:
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
    red = get_redis_client()

    runtime_stop_event = threading.Event()
    threads: dict[str, threading.Thread] = {}
    stop_events: dict[str, threading.Event] = {}
    service_specs = {spec.name: spec for spec in services}

    for name in service_specs:
        red.hsetnx(STATE_KEY, f"{name}:desired", RUNNING)

    def start_service(name: str) -> None:
        stop_event = threading.Event()
        stop_events[name] = stop_event
        threads[name] = _start_service(service_specs[name], stop_event)
        now = int(time.time())
        red.hset(
            STATE_KEY,
            mapping={
                f"{name}:state": RUNNING,
                f"{name}:start": now,
                f"{name}:spawnerr": "",
            },
        )

    for name in service_specs:
        if redis_text(red.hget(STATE_KEY, f"{name}:desired")) != STOPPED:
            start_service(name)
        else:
            red.hset(STATE_KEY, f"{name}:state", STOPPED)

    try:
        while not runtime_stop_event.wait(MONITOR_INTERVAL_SECONDS):
            for name in service_specs:
                desired = (
                    redis_text(red.hget(STATE_KEY, f"{name}:desired")) or RUNNING
                )
                thread = threads.get(name)

                if desired == STOPPED:
                    if thread and thread.is_alive():
                        stop_events[name].set()
                        thread.join(timeout=MONITOR_INTERVAL_SECONDS)
                    if not thread or not thread.is_alive():
                        threads.pop(name, None)
                        stop_events.pop(name, None)
                        red.hset(
                            STATE_KEY,
                            mapping={
                                f"{name}:state": STOPPED,
                                f"{name}:stop": int(time.time()),
                            },
                        )
                    continue

                if not thread or not thread.is_alive():
                    if thread is None:
                        logger.info(
                            "Starting requested shared supervisor service %s", name
                        )
                    else:
                        logger.error(
                            "Shared supervisor thread %s died; restarting", name
                        )
                    start_service(name)
                else:
                    red.hset(STATE_KEY, f"{name}:state", RUNNING)
    except KeyboardInterrupt:
        logger.info("Stopping shared supervisor runtime")
    finally:
        runtime_stop_event.set()
        for stop_event in stop_events.values():
            stop_event.set()
        for thread in list(threads.values()):
            thread.join(timeout=1)
