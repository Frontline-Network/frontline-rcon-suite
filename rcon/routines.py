import logging
import threading
import time

from rcon.audit import ingame_mods, online_mods
from rcon.perf_statistics import PerformanceStatistics
from rcon.rcon import HLLCommandFailedError, Rcon, get_rcon
from rcon.user_config.auto_kick import AutoVoteKickUserConfig
from rcon.vote_map import VoteMap

logger = logging.getLogger(__name__)


def toggle_votekick(rcon: Rcon):
    config = AutoVoteKickUserConfig.load_from_db()

    if not config.enabled:
        return

    condition_type = config.condition.upper()
    min_online = config.minimum_online_mods
    min_ingame = config.minimum_ingame_mods
    condition = all if condition_type == "AND" else any
    online_mods_ = online_mods()
    ingame_mods_ = ingame_mods(rcon)

    ok_online = len(online_mods_) >= min_online
    ok_ingame = len(ingame_mods_) >= min_ingame

    if condition([ok_ingame, ok_online]):
        logger.debug(
            f"Turning votekick off {condition_type=} {min_online=} {min_ingame=} {ok_online=} {ok_ingame=} {online_mods_=} {ingame_mods_=}"
        )
        rcon.set_votekick_enabled(False)
    else:
        logger.debug(
            f"Turning votekick on {condition_type=} {min_online=} {min_ingame=} {ok_online=} {ok_ingame=} {online_mods_=} {ingame_mods_=}"
        )
        rcon.set_votekick_enabled(True)


def dump_rcon_performance_stats():
    pl = PerformanceStatistics("rcon", True)
    d = pl.dump()
    for k, v in d.items():
        logger.info(f"{k}: {v}")


def _next_deadline(interval: float, now: float | None = None) -> float | None:
    if interval <= 0:
        return None
    return (time.monotonic() if now is None else now) + interval


def _sleep_until_next_deadline(
    *deadlines: float | None, now: float | None = None
) -> float:
    now = time.monotonic() if now is None else now
    active_deadlines = [deadline for deadline in deadlines if deadline is not None]
    if not active_deadlines:
        return 30.0
    return max(0.1, min(30.0, min(active_deadlines) - now))


def run(stop_event: threading.Event | None = None):
    stop_event = stop_event or threading.Event()
    max_fails = 5
    rcon = get_rcon()
    performance_interval = float(rcon.performance_stats_interval())
    next_performance_dump = time.monotonic() if performance_interval > 0 else None
    next_routines_run = time.monotonic()

    from rcon.leadership_vote.service import Runtime

    leadership = Runtime()
    next_leadership_step = time.monotonic()
    try:
        while not stop_event.is_set():
            now = time.monotonic()
            if now >= next_leadership_step:
                try:
                    leadership.step(rcon)
                except Exception:
                    logger.exception("Leadership voting must not stop other routines")
                next_leadership_step = _next_deadline(5.0)
            if next_performance_dump is not None and now >= next_performance_dump:
                try:
                    dump_rcon_performance_stats()
                except Exception:
                    # Statistics must never stop gameplay routines. The former
                    # dedicated scheduler process provided the same isolation.
                    logger.exception("Unable to dump RCON performance statistics")
                next_performance_dump = _next_deadline(performance_interval)

            if now >= next_routines_run:
                try:
                    toggle_votekick(rcon)
                    VoteMap().send_reminder()
                    max_fails = 5
                except HLLCommandFailedError:
                    max_fails -= 1
                    if max_fails <= 0:
                        logger.exception("Routines failed 5 times in a row; stopping")
                        raise
                next_routines_run = _next_deadline(30.0)

            stop_event.wait(
                _sleep_until_next_deadline(
                    next_leadership_step,
                    next_routines_run,
                    next_performance_dump,
                )
            )
    finally:
        try:
            leadership.close()
        except Exception:
            logger.exception("Unable to close leadership runtime")
