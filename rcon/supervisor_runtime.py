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
MODE_KEY = "frontline:supervisor_runtime:mode"
RUNNING = "RUNNING"
STOPPED = "STOPPED"
SPLIT_MODE = "split"
SHARED_MODE = "shared"


def redis_text(value):
    if isinstance(value, bytes):
        return value.decode("utf-8")
    return value


def decode_service_state(raw_state: dict) -> dict[str, str]:
    return {
        str(redis_text(key)): str(redis_text(value))
        for key, value in raw_state.items()
    }


def read_service_controls(red, service_names: Sequence[str]) -> dict[str, tuple[str, str]]:
    """Read all desired states and restart tokens with one Redis command.

    The former monitor loop issued two ``HGET`` calls per service every second
    and rewrote every unchanged ``RUNNING`` state. On a multi-instance host
    that made the health monitor itself a material Redis poller. ``HMGET``
    keeps the same one-second control response while making the cost constant
    per runtime process.
    """
    fields = [
        field
        for name in service_names
        for field in (f"{name}:desired", f"{name}:restart")
    ]
    values = red.hmget(STATE_KEY, fields)
    controls: dict[str, tuple[str, str]] = {}
    for index, name in enumerate(service_names):
        desired = redis_text(values[index * 2]) or RUNNING
        restart = redis_text(values[index * 2 + 1]) or ""
        controls[name] = (desired, restart)
    return controls


def mark_runtime_mode(mode: str, red=None) -> None:
    """Persist the active supervisor topology for the next mode transition."""
    if mode not in {SPLIT_MODE, SHARED_MODE}:
        raise ValueError(f"Unsupported supervisor runtime mode: {mode}")
    if red is None:
        from rcon.cache_utils import get_redis_client

        red = get_redis_client()
    red.set(MODE_KEY, mode)


def prepare_shared_state(red, service_names: Sequence[str]) -> bool:
    """Reset stale controls only when entering shared mode from split mode.

    A shared-runtime restart must retain intentional per-service stop requests.
    Split Supervisor, however, starts its autostart programs afresh and marks
    that topology in Redis.  On the next real split-to-shared transition, old
    controls from an earlier canary must therefore not silently disable a
    service.
    """
    previous_mode = redis_text(red.get(MODE_KEY))
    transitioned = previous_mode != SHARED_MODE
    if transitioned:
        red.hset(
            STATE_KEY,
            mapping={f"{name}:desired": RUNNING for name in service_names},
        )
    mark_runtime_mode(SHARED_MODE, red=red)
    return transitioned


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


def _run_auto_settings(stop_event: threading.Event) -> None:
    from rcon import auto_settings

    auto_settings.run(stop_event=stop_event)


def _run_broadcasts(stop_event: threading.Event) -> None:
    from rcon import broadcast

    broadcast.run(stop_event=stop_event)


def _run_live_map(stop_event: threading.Event) -> None:
    from rcon.live_map.service import run
    run(stop_event)


def _run_population_history(stop_event: threading.Event) -> None:
    from rcon.population import run

    run(stop_event=stop_event)


DEFAULT_SERVICES: tuple[ServiceSpec, ...] = (
    ServiceSpec("population_history", _run_population_history),
    ServiceSpec("live_map", _run_live_map),
    ServiceSpec("expiring_vips", _run_expiring_vips),
    ServiceSpec("live_stats_refresh", _run_live_stats),
    ServiceSpec("autobalancer", _run_autobalancer),
    ServiceSpec("blacklists", _run_blacklists),
    ServiceSpec("log_recorder", _run_log_recorder),
    ServiceSpec("routines", _run_routines),
    ServiceSpec("auto_settings", _run_auto_settings),
    ServiceSpec("broadcasts", _run_broadcasts),
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

    prepare_shared_state(red, service_specs)
    for name in service_specs:
        red.hsetnx(STATE_KEY, f"{name}:desired", RUNNING)

    controls = read_service_controls(red, service_specs)
    restart_tokens = {name: values[1] for name, values in controls.items()}

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
            controls = read_service_controls(red, service_specs)
            for name in service_specs:
                desired, restart_token = controls[name]
                thread = threads.get(name)

                if restart_token != restart_tokens[name]:
                    if thread and thread.is_alive():
                        logger.info("Restarting requested shared service %s", name)
                        stop_events[name].set()
                        thread.join(timeout=MONITOR_INTERVAL_SECONDS)
                        if thread.is_alive():
                            # Never start a duplicate worker. The cooperative
                            # service will be checked again on the next monitor
                            # iteration until it has stopped completely.
                            continue
                    threads.pop(name, None)
                    stop_events.pop(name, None)
                    thread = None
                    restart_tokens[name] = restart_token

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
    except KeyboardInterrupt:
        logger.info("Stopping shared supervisor runtime")
    finally:
        runtime_stop_event.set()
        for stop_event in stop_events.values():
            stop_event.set()
        for thread in list(threads.values()):
            thread.join(timeout=1)
