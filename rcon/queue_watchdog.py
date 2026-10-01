"""Observe admission stalls; never change slots, reset queues or touch players."""

from __future__ import annotations

import json
import logging
import math
import os
import time
from dataclasses import dataclass

logger = logging.getLogger(__name__)

POLL_SECONDS = 30
STALL_SECONDS = 180
ROUND_GRACE_SECONDS = 180
MAX_SAMPLE_SECONDS = 10
MAX_GAP_SECONDS = 90
ALERT_COOLDOWN_SECONDS = 900
STATUS_TTL_SECONDS = 120
MIN_FREE_PUBLIC_SLOTS = 2


@dataclass(frozen=True)
class Sample:
    captured_at: float
    round_id: str
    round_age: float
    remaining: int
    player_ids: frozenset[str]
    capacity: int
    queued: int
    queue_limit: int
    vip_slots: int

    @property
    def public_free(self) -> int:
        # Conservatively reserve all VIP slots, even if VIPs are already online.
        return max(0, self.capacity - self.vip_slots - len(self.player_ids))


def _count(data: dict, key: str) -> int:
    value = data.get(key)
    if type(value) is not int or value < 0:
        raise ValueError(f"Invalid queue sample field: {key}")
    return value


def capture(api) -> Sample:
    """Uncached reads, checked against the recorder before AND after sampling."""
    from rcon.utils import MapsHistory

    started = time.time()
    history = MapsHistory()
    before = history.get_current_map() or {}
    state = api.exchange(
        "GetServerInformation", 2, {"Name": "session", "Value": ""}
    ).content_dict
    rows = api.exchange(
        "GetServerInformation", 2, {"Name": "players", "Value": ""}
    ).content_dict["players"]
    after = history.get_current_map() or {}
    now = time.time()
    layer, start = before.get("name"), before.get("start")
    if (
        not 0 <= now - started <= MAX_SAMPLE_SECONDS
        or type(start) not in (int, float)
        or not math.isfinite(start)
        or not 0 < start <= now
        or not layer
        or layer != state.get("mapId")
        or before.get("end") is not None
        or before.get("guessed", False)
        or any(
            before.get(k) != after.get(k) for k in ("name", "start", "end", "guessed")
        )
    ):
        raise ValueError("Queue sample has no stable, recorder-confirmed round")
    if not isinstance(rows, list):
        raise ValueError("Invalid queue roster")
    ids = [row.get("iD") if isinstance(row, dict) else None for row in rows]
    if any(not isinstance(pid, str) or not pid.strip() for pid in ids):
        raise ValueError("Missing player identity in queue roster")
    players = frozenset(ids)
    capacity = _count(state, "maxPlayerCount")
    queued = _count(state, "queueCount")
    limit = _count(state, "maxQueueCount")
    reserved = _count(state, "maxVipQueueCount")
    if (
        len(players) != len(rows)
        or _count(state, "playerCount") != len(players)
        or not 0 < capacity <= 200
        or len(players) > capacity
        or reserved > capacity
        or queued > limit
    ):
        raise ValueError("Inconsistent player/queue counts; not evidence of a stall")
    return Sample(
        captured_at=now,
        round_id=f"{layer}:{start}",
        round_age=now - start,
        remaining=_count(state, "remainingMatchTime"),
        player_ids=players,
        capacity=capacity,
        queued=queued,
        queue_limit=limit,
        vip_slots=reserved,
    )


class Detector:
    """Requires consecutive valid observations; restarts cannot inherit a stall."""

    def __init__(self):
        self.reset()

    def reset(self):
        self.previous: Sample | None = None
        self.last_seen: float | None = None
        self.since: float | None = None
        self.suppressed_until = 0.0
        self.reported = False

    def observe(self, sample: Sample, *, now: float, wall_time: float) -> dict:
        if not 0 <= wall_time - sample.captured_at <= MAX_SAMPLE_SECONDS:
            self.reset()
            return {"state": "unknown", "alert": False}
        if (
            self.last_seen is not None
            and not 0 < now - self.last_seen <= MAX_GAP_SECONDS
        ):
            self.reset()
        previous = self.previous
        changed_round = previous is not None and (
            previous.round_id != sample.round_id
            or sample.remaining > previous.remaining + 5
        )
        changed_limits = previous is not None and (
            (previous.capacity, previous.queue_limit, previous.vip_slots)
            != (sample.capacity, sample.queue_limit, sample.vip_slots)
        )
        joined = previous is not None and bool(sample.player_ids - previous.player_ids)
        if changed_round:
            self.suppressed_until = now + ROUND_GRACE_SECONDS
        if changed_round or changed_limits or joined:
            self.since = None
            self.reported = False
        self.previous, self.last_seen = sample, now
        grace = sample.round_age < ROUND_GRACE_SECONDS or now < self.suppressed_until
        candidate = (
            not grace
            and sample.queued > 0
            and sample.public_free >= MIN_FREE_PUBLIC_SLOTS
        )
        if not candidate:
            self.since = None
            self.reported = False
        elif self.since is None:
            self.since = now
        duration = 0 if self.since is None else int(now - self.since)
        stalled = candidate and duration >= STALL_SECONDS
        return {
            "state": (
                "round_grace"
                if grace
                else (
                    "suspected_stall"
                    if stalled
                    else "observing" if candidate else "normal"
                )
            ),
            "alert": stalled and not self.reported,
            "round_id": sample.round_id,
            "players": len(sample.player_ids),
            "capacity": sample.capacity,
            "queued": sample.queued,
            "queue_limit": sample.queue_limit,
            "vip_slots": sample.vip_slots,
            "public_free": sample.public_free,
            "observed_seconds": duration,
        }


class QueueWatchdog:
    def __init__(self):
        self.detector = Detector()

    def step(self, api):
        if os.getenv("HLL_QUEUE_WATCHDOG_ENABLED", "true").lower() in {
            "0",
            "false",
            "no",
            "off",
        }:
            self.detector.reset()
            return
        from rcon.cache_utils import get_redis_client
        from rcon.discord import send_to_discord_audit
        from rcon.utils import get_server_number

        server = get_server_number()
        red = get_redis_client()
        try:
            sample = capture(api)
            status = self.detector.observe(
                sample, now=time.monotonic(), wall_time=time.time()
            )
        except Exception:
            self.detector.reset()
            # Invalid/transition data is expected and is never an admin alarm.
            logger.debug(
                "Queue observation unavailable; resetting evidence", exc_info=True
            )
            status = {"state": "unknown", "alert": False}
        status["checked_at"] = time.time()
        red.setex(
            f"queue_watchdog:{server}:status", STATUS_TTL_SECONDS, json.dumps(status)
        )
        if not status["alert"]:
            return
        # Reserve BEFORE enqueueing. Survives process restarts and prevents
        # duplicate workers or an ambiguous enqueue result from spamming admins.
        if not red.set(
            f"queue_watchdog:{server}:alert_cooldown",
            "1",
            nx=True,
            ex=ALERT_COOLDOWN_SECONDS,
        ):
            return
        self.detector.reported = True
        message = (
            f"Möglicher Warteschlangen-Stau / Possible queue stall: "
            f"{status['players']}/{status['capacity']} players, "
            f"queue {status['queued']}/{status['queue_limit']}, "
            f"VIP slots {status['vip_slots']}, "
            f"{status['public_free']} free public slots. "
            f"Seit {status['observed_seconds']} Sekunden kein Beitritt beobachtet / "
            f"No joins observed for {status['observed_seconds']} seconds. "
            "Bitte Aufnahme prüfen; kein automatischer Eingriff. / "
            "Please check admission; no automatic action taken."
        )
        logger.warning("%s", message)
        send_to_discord_audit(
            message, "queue_watchdog", by="Queue watchdog", silent=False
        )
