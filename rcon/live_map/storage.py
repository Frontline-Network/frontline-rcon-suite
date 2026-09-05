"""Bounded private storage. Evidence never enters generic incident payloads."""
import copy
import json
import time
import uuid
import zlib

from sqlalchemy import delete, select, func

from rcon.live_map.domain import CASE_SECONDS, HISTORY_SECONDS
from rcon.live_map.models import TacticalBlock, TacticalReview, TacticalSettings
from rcon.models import AdminIncident, enter_session

DEFAULT_SETTINGS = {"enabled": False, "monitor_enabled": False, "calibrations": {}, "monitors": []}


def lock_server(session, server):
    # A row lock alone cannot serialize simultaneous creation of the first row.
    if session.get_bind().dialect.name == "postgresql":
        session.execute(select(func.pg_advisory_xact_lock(0x464C4D, int(server))))


def pack(value):
    return zlib.compress(json.dumps(value, separators=(",", ":"), allow_nan=False).encode(), 6)


def unpack(data):
    decoder = zlib.decompressobj()
    result = decoder.decompress(data, 32 * 1024 * 1024)
    if not decoder.eof:
        raise ValueError("Verlaufsblock überschreitet die zulässige Größe")
    return json.loads(result)


def get_settings(server):
    with enter_session() as session:
        row = session.get(TacticalSettings, server)
        return {**copy.deepcopy(DEFAULT_SETTINGS), **(copy.deepcopy(row.value) if row else {})}


def update_settings(server, change):
    with enter_session() as session:
        lock_server(session, server)
        row = session.get(TacticalSettings, server, with_for_update=True)
        value = {**copy.deepcopy(DEFAULT_SETTINGS), **(copy.deepcopy(row.value) if row else {})}
        change(value)
        if row is None:
            session.add(TacticalSettings(server_number=server, value=value))
        else:
            row.value = value
        return value


def save_block(server, frames):
    if not frames:
        return
    with enter_session() as session:
        lock_server(session, server)
        block_id = str(uuid.uuid5(uuid.NAMESPACE_URL, f"live-map:{server}:{frames[0]['round_id']}:{frames[0]['captured_at']}:{frames[-1]['captured_at']}"))
        if session.get(TacticalBlock, block_id) is not None:
            return
        session.add(TacticalBlock(id=block_id, server_number=server,
                                  round_id=frames[0]["round_id"], start_at=frames[0]["captured_at"],
                                  end_at=frames[-1]["captured_at"], data=pack(frames)))


def history(server, start, end, round_id=None, now=None):
    now = time.time() if now is None else now
    if not all(isinstance(x, (int, float)) for x in (start, end)) or not now - HISTORY_SECONDS <= start <= end <= now + 2:
        raise ValueError("Verlauf ist nur für die letzten 24 Stunden verfügbar")
    if end - start > 900:
        raise ValueError("Pro Abfrage sind höchstens 15 Minuten möglich")
    with enter_session() as session:
        query = select(TacticalBlock).where(TacticalBlock.server_number == server,
                                            TacticalBlock.end_at >= start, TacticalBlock.start_at <= end)
        if round_id:
            query = query.where(TacticalBlock.round_id == round_id)
        rows = session.scalars(query.order_by(TacticalBlock.start_at).limit(128)).all()
        return [frame for row in rows for frame in unpack(row.data) if start <= frame["captured_at"] <= end]


def rounds(server, now=None):
    now = time.time() if now is None else now
    from sqlalchemy import func
    with enter_session() as session:
        values = session.execute(select(TacticalBlock.round_id, func.min(TacticalBlock.start_at), func.max(TacticalBlock.end_at))
                                 .where(TacticalBlock.server_number == server, TacticalBlock.end_at >= now - HISTORY_SECONDS)
                                 .group_by(TacticalBlock.round_id).order_by(func.max(TacticalBlock.end_at).desc()).limit(100)).all()
        return [{"round_id": r, "start": max(s, now - HISTORY_SECONDS), "end": e} for r, s, e in values]


def review_statuses(server):
    with enter_session() as session:
        rows = session.execute(select(TacticalReview, AdminIncident)
                               .join(AdminIncident, TacticalReview.incident_id == AdminIncident.id)
                               .where(TacticalReview.server_number == server, TacticalReview.expires_at > time.time())
                               .order_by(TacticalReview.expires_at.desc()).limit(500)).all()
        return {r.signal_id: {"incident_id": r.incident_id, "status": i.status,
                              "revision": i.revision, "assigned_to": i.assigned_to,
                              "saved": r.evidence is not None} for r, i in rows}


def attach_review(server, signal_id, incident_id, evidence=None):
    with enter_session() as session:
        lock_server(session, server)
        row = session.get(TacticalReview, (server, signal_id), with_for_update=True)
        if row is None:
            row = TacticalReview(server_number=server, signal_id=signal_id, incident_id=incident_id,
                                 expires_at=time.time() + HISTORY_SECONDS)
            session.add(row)
        if evidence is not None and row.evidence is None:
            row.evidence = pack(evidence)
            row.expires_at = time.time() + CASE_SECONDS


def get_evidence(server, signal_id):
    with enter_session() as session:
        row = session.get(TacticalReview, (server, signal_id))
        if row is None or row.expires_at <= time.time() or row.evidence is None:
            raise LookupError("Gesicherter Ausschnitt nicht verfügbar")
        return unpack(row.evidence)


def cleanup(server, now=None):
    now = time.time() if now is None else now
    with enter_session() as session:
        session.execute(delete(TacticalBlock).where(TacticalBlock.server_number == server, TacticalBlock.end_at < now - HISTORY_SECONDS))
        session.execute(delete(TacticalReview).where(TacticalReview.server_number == server, TacticalReview.expires_at <= now))
