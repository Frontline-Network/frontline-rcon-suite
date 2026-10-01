"""Durable population recording and bounded queries for external analytics."""

import logging
import math
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Event
from uuid import UUID

from sqlalchemy import delete, func, select, text

from rcon.models import get_session_maker
from rcon.population_models import PopulationSample as Sample
from rcon.population_models import SeedingSession
from rcon.user_config.population_history import PopulationHistoryUserConfig as Config

logger = logging.getLogger(__name__)
MAX_POINTS = 5000
MAX_PERIOD_SECONDS = 31 * 86400
RESOLUTIONS = {"raw": 0, "1m": 60, "5m": 300, "15m": 900, "60m": 3600}
LOCK_NAMESPACE = 17481237


@contextmanager
def enter_session():
    # Unlike the legacy helper, propagate schema/storage failures to the API
    # and recorder instead of returning an apparently successful empty result.
    with get_session_maker().begin() as db:
        yield db


def utc(value):
    return (
        datetime.fromtimestamp(value, timezone.utc).isoformat().replace("+00:00", "Z")
    )


def timestamp(value):
    """Require an explicit timezone for ISO timestamps; also accept Unix seconds."""
    try:
        result = float(value)
    except (TypeError, ValueError):
        try:
            parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
            if parsed.tzinfo is None:
                raise ValueError
            result = parsed.timestamp()
        except (ValueError, OverflowError) as error:
            raise ValueError(
                "Use an ISO timestamp with timezone or Unix seconds"
            ) from error
    if not math.isfinite(result) or not 0 <= result <= 32503680000:
        raise ValueError("Timestamp is outside the supported range")
    return result


def period(start, end):
    start, end = timestamp(start), timestamp(end)
    if not 0 < end - start <= MAX_PERIOD_SECONDS:
        raise ValueError("The period must be positive and at most 31 days")
    if end > time.time() + 60:
        raise ValueError("The period must not extend into the future")
    return start, end


def _lock(db, server, *, wait=False):
    """Transaction locks are released even if a recorder process is killed."""
    if db.get_bind().dialect.name != "postgresql":
        return True  # SQLite is only used by unit tests.
    function = "pg_advisory_xact_lock" if wait else "pg_try_advisory_xact_lock"
    value = db.scalar(
        text(f"SELECT {function}(:namespace, :server)"),
        {"namespace": LOCK_NAMESPACE, "server": server},
    )
    return True if wait else bool(value)


def record_sample(rcon, server, config, *, clock=time.time):
    """One query per scheduled slot, across restarts and competing processes."""
    now = clock()
    interval = config.interval_seconds
    scheduled = int(now) // interval * interval
    with enter_session() as db:
        if not _lock(db, server):
            return False
        last = db.scalar(
            select(Sample)
            .where(Sample.server_number == server)
            .order_by(Sample.scheduled_at.desc())
            .limit(1)
        )
        # Also avoid overlapping slots when the sampling interval is changed.
        if last and scheduled < last.scheduled_at + last.interval_seconds:
            return False
        sample = Sample(
            server_number=server,
            scheduled_at=scheduled,
            captured_at=now,
            interval_seconds=interval,
            status="rcon_error",
        )
        try:
            slots = rcon.get_slots()
            count, maximum = slots["current_players"], slots["max_players"]
            if (
                type(count) is not int
                or type(maximum) is not int
                or not 0 <= count <= maximum <= 1000
            ):
                raise ValueError("Invalid RCON slot counts")
            captured = clock()
            if captured >= scheduled + interval or captured < scheduled:
                raise ValueError("RCON query exceeded its sampling slot")
            sample.captured_at = captured
            sample.player_count, sample.max_players = count, maximum
            sample.status = "ok"
        except Exception as error:
            # Store a classified failure, never an invented zero or raw error text.
            logger.warning("Population query failed: %s", type(error).__name__)
        if sample.status == "ok":
            try:
                sample.map_name = str(rcon.get_map())[:160]
            except Exception:
                logger.debug("Population map metadata unavailable")
        db.add(sample)
        db.flush()
    return True


def prune(server, retention_days, *, now=None):
    now = time.time() if now is None else now
    with enter_session() as db:
        db.execute(
            delete(Sample).where(
                Sample.server_number == server,
                Sample.scheduled_at < now - retention_days * 86400,
            )
        )


def run(stop_event=None):
    from rcon.rcon import get_rcon
    from rcon.utils import get_server_number

    stop_event = stop_event or Event()
    server = int(get_server_number())
    next_prune = 0.0
    while not stop_event.is_set():
        interval = 30
        try:
            config = Config.load_from_db(default_on_validation_error=False)
            interval = config.interval_seconds
            if config.enabled:
                record_sample(get_rcon(), server, config)
            if time.monotonic() >= next_prune:
                prune(server, config.retention_days)
                next_prune = time.monotonic() + 3600
        except Exception as error:
            logger.warning("Population recorder unavailable: %s", type(error).__name__)
            if stop_event.wait(5):
                return
        stop_event.wait(max(0.1, interval - time.time() % interval))


def _raw(sample):
    return {
        "scheduled_at": utc(sample.scheduled_at),
        "captured_at": utc(sample.captured_at),
        "interval_seconds": sample.interval_seconds,
        "status": sample.status,
        "player_count": sample.player_count,
        "max_players": sample.max_players,
        "map": sample.map_name,
    }


def history(server, start, end, resolution="5m", limit=MAX_POINTS):
    start, end = period(start, end)
    if resolution not in RESOLUTIONS:
        raise ValueError("resolution must be raw, 1m, 5m, 15m or 60m")
    if not 1 <= limit <= MAX_POINTS:
        raise ValueError("limit must be between 1 and 5000")
    seconds = RESOLUTIONS[resolution]
    first_bucket = int(start) // seconds * seconds if seconds else 0
    buckets = math.ceil((end - first_bucket) / seconds) if seconds else 0
    if buckets > limit:
        raise ValueError("Too many buckets; shorten the period or increase resolution")
    with enter_session() as db:
        first, last = db.execute(
            select(func.min(Sample.scheduled_at), func.max(Sample.scheduled_at)).where(
                Sample.server_number == server, Sample.status == "ok"
            )
        ).one()
        result = {
            "server_number": server,
            "from": utc(start),
            "to": utc(end),
            "resolution": resolution,
            "timezone": "UTC",
            "source": "rcon_slots",
            "first_available_at": utc(first) if first is not None else None,
            "last_available_at": utc(last) if last is not None else None,
            "next_from": None,
        }
        query = (
            select(Sample)
            .where(
                Sample.server_number == server,
                Sample.scheduled_at >= start,
                Sample.scheduled_at < end,
            )
            .order_by(Sample.scheduled_at)
        )
        if not seconds:
            rows = list(db.scalars(query.limit(limit + 1)))
            if len(rows) > limit:
                result["next_from"] = utc(rows[limit].scheduled_at)
            result["points"] = [_raw(row) for row in rows[:limit]]
            return result

        points = [
            {
                "from": utc(max(start, t)),
                "to": utc(min(end, t + seconds)),
                "mean": None,
                "min": None,
                "max": None,
                "sample_count": 0,
                "failed_sample_count": 0,
                "sampling_coverage": 0.0,
            }
            for t in range(first_bucket, math.ceil(end), seconds)
        ]
        totals = [0] * len(points)
        covered = [0.0] * len(points)
        for row in db.scalars(query.execution_options(yield_per=2000)):
            index = (row.scheduled_at - first_bucket) // seconds
            point = points[index]
            if row.status != "ok":
                point["failed_sample_count"] += 1
                continue
            point["sample_count"] += 1
            totals[index] += row.player_count
            point["min"] = (
                row.player_count
                if point["min"] is None
                else min(point["min"], row.player_count)
            )
            point["max"] = (
                row.player_count
                if point["max"] is None
                else max(point["max"], row.player_count)
            )
            bucket_end = min(end, first_bucket + (index + 1) * seconds)
            covered[index] += max(
                0,
                min(bucket_end, row.scheduled_at + row.interval_seconds)
                - row.scheduled_at,
            )
        for index, point in enumerate(points):
            if point["sample_count"]:
                point["mean"] = totals[index] / point["sample_count"]
            duration = min(end, first_bucket + (index + 1) * seconds) - max(
                start, first_bucket + index * seconds
            )
            point["sampling_coverage"] = min(1.0, covered[index] / duration)
        result["points"] = points
        result["sampling_coverage"] = sum(covered) / (end - start)
        return result


def _seeding_dict(row):
    return {
        "id": row.id,
        "server_number": row.server_number,
        "started_at": utc(row.started_at),
        "ended_at": utc(row.ended_at) if row.ended_at is not None else None,
        "seeder_count": row.seeder_count,
        "source": "manual",
    }


def seeding_history(server, start, end):
    start, end = period(start, end)
    with enter_session() as db:
        rows = list(
            db.scalars(
                select(SeedingSession)
                .where(
                    SeedingSession.server_number == server,
                    SeedingSession.started_at < end,
                    (SeedingSession.ended_at >= start)
                    | SeedingSession.ended_at.is_(None),
                )
                .order_by(SeedingSession.started_at)
                .limit(MAX_POINTS + 1)
            )
        )
        if len(rows) > MAX_POINTS:
            raise ValueError("Too many seeding sessions; shorten the period")
        return [_seeding_dict(row) for row in rows]


def mark_seeding(server, action, session_id, actor, seeder_count=None, *, now=None):
    session_id = str(UUID(str(session_id)))  # Caller supplies a retry-safe UUID.
    if action not in {"start", "end"}:
        raise ValueError("action must be start or end")
    if seeder_count is not None and (
        type(seeder_count) is not int or not 0 <= seeder_count <= 1000
    ):
        raise ValueError("seeder_count must be null or an integer between 0 and 1000")
    if action == "end" and seeder_count is not None:
        raise ValueError("seeder_count is recorded when starting a session")
    now = time.time() if now is None else now
    with enter_session() as db:
        _lock(db, server, wait=True)
        row = db.get(SeedingSession, session_id)
        if row and row.server_number != server:
            raise ValueError("Session belongs to a different server")
        if action == "start":
            if row:
                if row.seeder_count != seeder_count:
                    raise ValueError("Session ID already exists with different data")
            else:
                active = db.scalar(
                    select(SeedingSession.id).where(
                        SeedingSession.active_server == server
                    )
                )
                if active:
                    raise ValueError(
                        "A seeding session is already open for this server"
                    )
                row = SeedingSession(
                    id=session_id,
                    server_number=server,
                    active_server=server,
                    started_at=now,
                    seeder_count=seeder_count,
                    created_by=actor,
                )
                db.add(row)
        else:
            if not row:
                raise ValueError("Unknown seeding session")
            if row.ended_at is None:
                row.ended_at, row.ended_by, row.active_server = (
                    max(now, row.started_at),
                    actor,
                    None,
                )
        db.flush()
        return _seeding_dict(row)
