"""Bounded private tactical storage.

History blocks are the only copy of raw positions. Archives merely pin blocks
for a confirmed round; detections retain compact, explainable aggregates.
"""
import copy
import json
import time
import uuid
import zlib

from sqlalchemy import delete, exists, func, select

from rcon.live_map.domain import CASE_SECONDS, HISTORY_SECONDS, normalize_stored_frame
from rcon.live_map.models import (
    TacticalArchive,
    TacticalBlock,
    TacticalDetection,
    TacticalReview,
    TacticalSettings,
)
from rcon.models import AdminIncident, enter_session

ARCHIVE_DAYS = {30, 90}
ARCHIVE_MAX_ROUNDS = 50
ARCHIVE_MAX_BYTES = 1024 * 1024 * 1024
DETECTION_PROFILE = {
    "min_kills": 25,
    "killrate_infantry": 1.25,
    "killrate_mg": 1.5,
    "killrate_armor": 2.0,
    "killrate_artillery": 3.0,
    "burst_kills": 6,
    "burst_unique_victims": 4,
    "burst_seconds": 60,
    "movement_mps": 50.0,
    "movement_consecutive": 2,
}
DEFAULT_SETTINGS = {
    "enabled": False,
    "monitor_enabled": False,
    "archive_enabled": False,
    "detection_enabled": False,
    "detection_profile": DETECTION_PROFILE,
    "calibrations": {},
    "monitors": [],
}


def lock_server(session, server):
    if session.get_bind().dialect.name == "postgresql":
        session.execute(select(func.pg_advisory_xact_lock(0x464C4D, int(server))))


def pack(value):
    return zlib.compress(
        json.dumps(value, separators=(",", ":"), allow_nan=False).encode(), 6
    )


def unpack(data):
    decoder = zlib.decompressobj()
    result = decoder.decompress(data, 32 * 1024 * 1024)
    if not decoder.eof:
        raise ValueError("Verlaufsblock überschreitet die zulässige Größe")
    return json.loads(result)


def _settings_value(row):
    value = {
        **copy.deepcopy(DEFAULT_SETTINGS),
        **(copy.deepcopy(row.value) if row else {}),
    }
    value["detection_profile"] = {
        **copy.deepcopy(DETECTION_PROFILE),
        **copy.deepcopy(value.get("detection_profile") or {}),
    }
    return value


def get_settings(server):
    with enter_session() as session:
        return _settings_value(session.get(TacticalSettings, server))


def update_settings(server, change):
    with enter_session() as session:
        lock_server(session, server)
        row = session.get(TacticalSettings, server, with_for_update=True)
        value = _settings_value(row)
        change(value)
        if row is None:
            session.add(TacticalSettings(server_number=server, value=value))
        else:
            row.value = value
        return value


def save_block(server, frames):
    if not frames:
        return
    encoded = pack(frames)
    round_id = frames[0]["round_id"]
    start_at, end_at = frames[0]["captured_at"], frames[-1]["captured_at"]
    with enter_session() as session:
        lock_server(session, server)
        block_id = str(
            uuid.uuid5(
                uuid.NAMESPACE_URL,
                f"live-map:{server}:{round_id}:{start_at}:{end_at}",
            )
        )
        if session.get(TacticalBlock, block_id) is not None:
            return
        session.add(
            TacticalBlock(
                id=block_id,
                server_number=server,
                round_id=round_id,
                start_at=start_at,
                end_at=end_at,
                data=encoded,
            )
        )
        archive = session.scalar(
            select(TacticalArchive).where(
                TacticalArchive.server_number == server,
                TacticalArchive.round_id == round_id,
            )
        )
        if archive:
            archive.start_at = min(archive.start_at, start_at)
            archive.end_at = max(archive.end_at, end_at)
            archive.estimated_bytes += len(encoded)
            archive.expires_at = archive.end_at + archive.retention_days * 86400


def _archive_for(session, server, archive_id, now):
    archive = session.get(TacticalArchive, str(archive_id))
    if not archive or archive.server_number != server or archive.expires_at <= now:
        raise LookupError("Gesicherte Runde nicht verfügbar")
    return archive


def history(server, start, end, round_id=None, now=None, archive_id=None):
    now = time.time() if now is None else now
    if not all(isinstance(x, (int, float)) for x in (start, end)) or not start <= end <= now + 2:
        raise ValueError("Ungültiger Zeitraum")
    if end - start > 900:
        raise ValueError("Pro Abfrage sind höchstens 15 Minuten möglich")
    with enter_session() as session:
        if archive_id:
            archive = _archive_for(session, server, archive_id, now)
            if round_id and round_id != archive.round_id:
                raise ValueError("Archiv und Runde passen nicht zusammen")
            round_id = archive.round_id
            if start < archive.start_at - 2 or end > archive.end_at + 2:
                raise ValueError("Zeitraum liegt außerhalb der gesicherten Runde")
        elif start < now - HISTORY_SECONDS:
            raise ValueError("Verlauf ist nur für die letzten 24 Stunden verfügbar")
        query = select(TacticalBlock).where(
            TacticalBlock.server_number == server,
            TacticalBlock.end_at >= start,
            TacticalBlock.start_at <= end,
        )
        if round_id:
            query = query.where(TacticalBlock.round_id == round_id)
        rows = session.scalars(
            query.order_by(TacticalBlock.start_at).limit(128)
        ).all()
        return [
            normalize_stored_frame(frame)
            for row in rows
            for frame in unpack(row.data)
            if start <= frame["captured_at"] <= end
        ]


def round_events(server, round_id):
    """Restore deduplicated round events and first-seen times after restart."""
    with enter_session() as session:
        rows = session.scalars(
            select(TacticalBlock)
            .where(
                TacticalBlock.server_number == server,
                TacticalBlock.round_id == round_id,
            )
            .order_by(TacticalBlock.start_at)
            .limit(2048)
        ).all()
        events, first_seen = {}, {}
        for row in rows:
            for frame in unpack(row.data):
                for player in frame.get("players", []):
                    player_id = player.get("player_id")
                    if player_id:
                        first_seen.setdefault(player_id, frame["captured_at"])
                for event in frame.get("events", []):
                    events[event["id"]] = event
        return list(events.values()), first_seen


def event_history(server, start, end, round_id, now=None, archive_id=None):
    """Return deduplicated event metadata for one bounded round timeline."""
    now = time.time() if now is None else now
    if not round_id or not start <= end or end - start > 6 * 3600:
        raise ValueError("Ereignisse erfordern eine Runde mit höchstens sechs Stunden")
    with enter_session() as session:
        if archive_id:
            archive = _archive_for(session, server, archive_id, now)
            if archive.round_id != round_id:
                raise ValueError("Archiv und Runde passen nicht zusammen")
        elif start < now - HISTORY_SECONDS:
            raise ValueError("Ereignisse sind nur für die letzten 24 Stunden verfügbar")
        rows = session.scalars(
            select(TacticalBlock)
            .where(
                TacticalBlock.server_number == server,
                TacticalBlock.round_id == round_id,
                TacticalBlock.end_at >= start,
                TacticalBlock.start_at <= end,
            )
            .order_by(TacticalBlock.start_at)
            .limit(2048)
        ).all()
        events, samples = {}, {}
        for row in rows:
            for frame in unpack(row.data):
                if start <= frame.get("captured_at", 0) <= end:
                    samples[frame["captured_at"]] = frame
                for event in frame.get("events", []):
                    if start <= event.get("time", 0) <= end:
                        events[event["id"]] = {
                            **event,
                            "kind": "teamkill" if event.get("teamkill") else "kill",
                        }
        ordered = [samples[key] for key in sorted(samples)]
        for previous, current in zip(ordered, ordered[1:]):
            elapsed = current["captured_at"] - previous["captured_at"]
            expected = max(
                12,
                float(previous.get("collector_interval") or 2) * 3 + 2,
            )
            if elapsed <= expected:
                continue
            gap_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"live-map-gap:{server}:{round_id}:{previous['captured_at']}:{current['captured_at']}",
                )
            )
            events[gap_id] = {
                "id": gap_id,
                "round_id": round_id,
                "kind": "data_gap",
                "time": previous["captured_at"],
                "end_time": current["captured_at"],
                "duration_seconds": round(elapsed, 1),
            }
        return sorted(events.values(), key=lambda item: item["time"])


def _round_rows(session, server, now):
    values = session.execute(
        select(
            TacticalBlock.round_id,
            func.min(TacticalBlock.start_at),
            func.max(TacticalBlock.end_at),
            func.sum(func.length(TacticalBlock.data)),
            func.count(TacticalBlock.id),
        )
        .where(
            TacticalBlock.server_number == server,
            TacticalBlock.end_at >= now - HISTORY_SECONDS,
        )
        .group_by(TacticalBlock.round_id)
    ).all()
    return {
        round_id: {
            "round_id": round_id,
            "start": max(start, now - HISTORY_SECONDS),
            "end": end,
            "bytes": int(size or 0),
            "data_quality": {
                "status": "available",
                "block_count": int(block_count or 0),
            },
        }
        for round_id, start, end, size, block_count in values
    }


def _archive_dict(row, now):
    return {
        "id": row.id,
        "round_id": row.round_id,
        "start": row.start_at,
        "end": row.end_at,
        "created_at": row.created_at,
        "expires_at": row.expires_at,
        "retention_days": row.retention_days,
        "created_by": row.created_by,
        "reason": row.reason,
        "incident_id": row.incident_id,
        "status": row.status,
        "bytes": int(row.estimated_bytes or 0),
        "expires_soon": row.expires_at - now <= 7 * 86400,
    }


def rounds(server, now=None):
    now = time.time() if now is None else now
    with enter_session() as session:
        result = _round_rows(session, server, now)
        archives = session.scalars(
            select(TacticalArchive)
            .where(
                TacticalArchive.server_number == server,
                TacticalArchive.expires_at > now,
            )
            .order_by(TacticalArchive.end_at.desc())
            .limit(100)
        ).all()
        for archive in archives:
            item = result.setdefault(
                archive.round_id,
                {
                    "round_id": archive.round_id,
                    "start": archive.start_at,
                    "end": archive.end_at,
                    "bytes": int(archive.estimated_bytes or 0),
                    "data_quality": {
                        "status": "retained",
                        "block_count": None,
                    },
                },
            )
            item["archive"] = _archive_dict(archive, now)
        return sorted(
            result.values(), key=lambda value: value["end"], reverse=True
        )[:100]


def list_archives(server, now=None):
    now = time.time() if now is None else now
    with enter_session() as session:
        rows = session.scalars(
            select(TacticalArchive)
            .where(
                TacticalArchive.server_number == server,
                TacticalArchive.expires_at > now,
            )
            .order_by(TacticalArchive.end_at.desc())
            .limit(100)
        ).all()
        return [_archive_dict(row, now) for row in rows]


def create_archive(
    server,
    round_id,
    start_at,
    end_at,
    created_by,
    reason,
    retention_days,
    incident_id=None,
    collecting=False,
    now=None,
):
    now = time.time() if now is None else now
    reason = str(reason or "").strip()
    if not reason or len(reason) > 1000:
        raise ValueError("Eine Begründung mit höchstens 1000 Zeichen ist erforderlich")
    retention_days = int(retention_days)
    if retention_days not in ARCHIVE_DAYS:
        raise ValueError("Aufbewahrung muss 30 oder 90 Tage betragen")
    if not round_id or not isinstance(start_at, (int, float)) or not isinstance(end_at, (int, float)):
        raise ValueError("Bestätigte Runde erforderlich")
    with enter_session() as session:
        lock_server(session, server)
        expired = session.scalar(
            select(TacticalArchive).where(
                TacticalArchive.server_number == server,
                TacticalArchive.round_id == round_id,
                TacticalArchive.expires_at <= now,
            )
        )
        if expired:
            session.delete(expired)
            session.flush()
        existing = session.scalar(
            select(TacticalArchive).where(
                TacticalArchive.server_number == server,
                TacticalArchive.round_id == round_id,
                TacticalArchive.expires_at > now,
            )
        )
        if existing:
            raise ValueError("Diese Runde ist bereits gesichert")
        active = session.scalars(
            select(TacticalArchive).where(
                TacticalArchive.server_number == server,
                TacticalArchive.expires_at > now,
            )
        ).all()
        if len(active) >= ARCHIVE_MAX_ROUNDS:
            raise ValueError("Archivlimit von 50 Runden erreicht")
        used = sum(int(row.estimated_bytes or 0) for row in active)
        size = session.scalar(
            select(func.sum(func.length(TacticalBlock.data))).where(
                TacticalBlock.server_number == server,
                TacticalBlock.round_id == round_id,
            )
        ) or 0
        if used + int(size) > ARCHIVE_MAX_BYTES:
            raise ValueError("Archivlimit von 1 GiB erreicht")
        row = TacticalArchive(
            id=str(uuid.uuid4()),
            server_number=server,
            round_id=str(round_id),
            start_at=float(start_at),
            end_at=float(end_at),
            created_at=now,
            expires_at=float(end_at) + retention_days * 86400,
            retention_days=retention_days,
            created_by=str(created_by)[:150],
            reason=reason,
            incident_id=str(incident_id)[:36] if incident_id else None,
            status="collecting" if collecting else "complete",
            estimated_bytes=int(size),
        )
        session.add(row)
        return _archive_dict(row, now)


def update_archive(
    server, archive_id, *, retention_days=None, incident_id=None, now=None
):
    now = time.time() if now is None else now
    with enter_session() as session:
        lock_server(session, server)
        row = _archive_for(session, server, archive_id, now)
        if retention_days is not None:
            retention_days = int(retention_days)
            if retention_days not in ARCHIVE_DAYS:
                raise ValueError("Aufbewahrung muss 30 oder 90 Tage betragen")
            if retention_days < row.retention_days:
                raise ValueError("Eine gesicherte Runde kann nur verlängert werden")
            row.retention_days = retention_days
            row.expires_at = row.end_at + retention_days * 86400
        if incident_id is not None:
            row.incident_id = str(incident_id)[:36] if incident_id else None
        return _archive_dict(row, now)


def delete_archive(server, archive_id, now=None):
    now = time.time() if now is None else now
    with enter_session() as session:
        lock_server(session, server)
        row = _archive_for(session, server, archive_id, now)
        result = _archive_dict(row, now)
        session.delete(row)
        return result


def finish_archive(server, round_id, end_at):
    with enter_session() as session:
        row = session.scalar(
            select(TacticalArchive).where(
                TacticalArchive.server_number == server,
                TacticalArchive.round_id == round_id,
                TacticalArchive.status == "collecting",
            )
        )
        if row:
            row.status = "complete"
            row.end_at = max(row.end_at, end_at)
            row.expires_at = row.end_at + row.retention_days * 86400


def _detection_dict(row):
    return {
        "id": row.id,
        "round_id": row.round_id,
        "player_id": row.player_id,
        "player_name": row.player_name,
        "kind": row.kind,
        "severity": row.severity,
        "first_at": row.first_at,
        "last_at": row.last_at,
        "expires_at": row.expires_at,
        "rule_version": row.rule_version,
        "status": row.status,
        "incident_id": row.incident_id,
        "evidence": copy.deepcopy(row.evidence),
    }


def upsert_detections(server, values, now=None):
    now = time.time() if now is None else now
    with enter_session() as session:
        lock_server(session, server)
        for value in values:
            row = session.get(
                TacticalDetection,
                (value["id"], server),
                with_for_update=True,
            )
            if row is None:
                row = TacticalDetection(
                    id=value["id"],
                    server_number=server,
                    round_id=value["round_id"],
                    player_id=value["player_id"],
                    player_name=value.get("player_name"),
                    kind=value["kind"],
                    severity=value["severity"],
                    first_at=value["first_at"],
                    last_at=value["last_at"],
                    expires_at=now + HISTORY_SECONDS,
                    rule_version=value["rule_version"],
                    status="open",
                    evidence=value,
                )
                session.add(row)
            elif row.server_number == server and row.status == "open":
                row.player_name = value.get("player_name") or row.player_name
                row.severity = value["severity"]
                row.first_at = min(row.first_at, value["first_at"])
                row.last_at = max(row.last_at, value["last_at"])
                row.expires_at = now + HISTORY_SECONDS
                row.rule_version = value["rule_version"]
                row.evidence = value


def list_detections(
    server, *, round_id=None, player_id=None, status=None, now=None, limit=200
):
    now = time.time() if now is None else now
    with enter_session() as session:
        query = select(TacticalDetection).where(
            TacticalDetection.server_number == server,
            TacticalDetection.expires_at > now,
        )
        if round_id:
            query = query.where(TacticalDetection.round_id == round_id)
        if player_id:
            query = query.where(TacticalDetection.player_id == player_id)
        if status:
            query = query.where(TacticalDetection.status == status)
        rows = session.scalars(
            query.order_by(TacticalDetection.last_at.desc()).limit(
                min(500, max(1, int(limit)))
            )
        ).all()
        result = [_detection_dict(row) for row in rows]
    statuses = review_statuses(server)
    for item in result:
        item["review"] = statuses.get(item["id"])
    return result


def get_detection(server, detection_id, now=None):
    now = time.time() if now is None else now
    with enter_session() as session:
        row = session.get(TacticalDetection, (str(detection_id), server))
        if not row or row.server_number != server or row.expires_at <= now:
            raise LookupError("Prüfhinweis nicht verfügbar")
        result = _detection_dict(row)
    result["review"] = review_statuses(server).get(result["id"])
    return result


def attach_detection_incident(server, detection_id, incident_id, status=None):
    with enter_session() as session:
        row = session.get(
            TacticalDetection,
            (str(detection_id), server),
            with_for_update=True,
        )
        if not row or row.server_number != server:
            raise LookupError("Prüfhinweis nicht verfügbar")
        row.incident_id = str(incident_id)
        if status:
            row.status = str(status)


def review_statuses(server):
    with enter_session() as session:
        rows = session.execute(
            select(TacticalReview, AdminIncident)
            .join(AdminIncident, TacticalReview.incident_id == AdminIncident.id)
            .where(
                TacticalReview.server_number == server,
                TacticalReview.expires_at > time.time(),
            )
            .order_by(TacticalReview.expires_at.desc())
            .limit(500)
        ).all()
        return {
            review.signal_id: {
                "incident_id": review.incident_id,
                "status": incident.status,
                "revision": incident.revision,
                "assigned_to": incident.assigned_to,
                "saved": review.evidence is not None,
            }
            for review, incident in rows
        }


def attach_review(server, signal_id, incident_id, evidence=None):
    with enter_session() as session:
        lock_server(session, server)
        row = session.get(TacticalReview, (server, signal_id), with_for_update=True)
        if row is None:
            row = TacticalReview(
                server_number=server,
                signal_id=signal_id,
                incident_id=incident_id,
                expires_at=time.time() + HISTORY_SECONDS,
            )
            session.add(row)
        if evidence is not None and row.evidence is None:
            row.evidence = pack(evidence)
            row.expires_at = time.time() + CASE_SECONDS


def get_evidence(server, signal_id):
    with enter_session() as session:
        row = session.get(TacticalReview, (server, signal_id))
        if row is None or row.expires_at <= time.time() or row.evidence is None:
            raise LookupError("Gesicherter Ausschnitt nicht verfügbar")
        evidence = unpack(row.evidence)
        for frame in evidence.get("frames", []):
            normalize_stored_frame(frame)
        return evidence


def cleanup(server, now=None):
    now = time.time() if now is None else now
    with enter_session() as session:
        session.execute(
            delete(TacticalArchive).where(
                TacticalArchive.server_number == server,
                TacticalArchive.expires_at <= now,
            )
        )
        protected = exists(
            select(TacticalArchive.id).where(
                TacticalArchive.server_number == TacticalBlock.server_number,
                TacticalArchive.round_id == TacticalBlock.round_id,
                TacticalArchive.expires_at > now,
            )
        )
        session.execute(
            delete(TacticalBlock).where(
                TacticalBlock.server_number == server,
                TacticalBlock.end_at < now - HISTORY_SECONDS,
                ~protected,
            )
        )
        session.execute(
            delete(TacticalDetection).where(
                TacticalDetection.server_number == server,
                TacticalDetection.expires_at <= now,
            )
        )
        session.execute(
            delete(TacticalReview).where(
                TacticalReview.server_number == server,
                TacticalReview.expires_at <= now,
            )
        )
