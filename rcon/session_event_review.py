"""Server-scoped operator review for session events with ambiguous history."""
from datetime import datetime, timezone
import hashlib
import json

from sqlalchemy import select, tuple_

from rcon.models import (
    PendingPlayerConnect, PendingPlayerDisconnect, PlayerID, PlayerSession,
    SessionEventResolution, UnidentifiedSessionEvent, get_session_maker,
)
from rcon.player_history import (
    _lock_player_session_events, _reassign_overlapping_disconnects,
    _reconcile_pending_disconnects, _legacy_connect_log_candidates,
)


def _event_time(event_us: int) -> str:
    return datetime.fromtimestamp(event_us / 1_000_000, timezone.utc).isoformat()


def record_unidentified(server_number: int, kind: str, event_us: int, player_name: str, raw: str) -> str:
    server_number, event_us = int(server_number), int(event_us)
    if not 1 <= server_number <= 32 or kind not in {"connect", "disconnect"} or event_us < 0:
        raise ValueError("Invalid unidentified session event")
    if not isinstance(player_name, str) or not isinstance(raw, str):
        raise ValueError("Invalid unidentified session event")
    encoded = json.dumps([server_number, kind, event_us, player_name, raw], ensure_ascii=False,
                         separators=(",", ":")).encode("utf-8")
    fingerprint = hashlib.sha256(encoded).hexdigest()
    with get_session_maker()() as session, session.begin():
        _lock_player_session_events(session, server_number, "unidentified:" + fingerprint)
        if session.get(UnidentifiedSessionEvent, fingerprint) is None:
            session.add(UnidentifiedSessionEvent(fingerprint=fingerprint, server_number=server_number,
                event_kind=kind, event_us=event_us, player_name=player_name, raw=raw))
    return fingerprint


def discard_unidentified(server_number: int, fingerprint: str, reason: str, actor: str) -> bool:
    server_number = int(server_number)
    if (not 1 <= server_number <= 32 or len(fingerprint) != 64
            or any(char not in "0123456789abcdef" for char in fingerprint)
            or not actor or not actor.strip() or len(actor) > 150
            or not reason or not reason.strip() or len(reason) > 1000):
        raise ValueError("Invalid event, operator or reason")
    with get_session_maker()() as session, session.begin():
        row = session.get(UnidentifiedSessionEvent, fingerprint, with_for_update=True)
        if row is None or row.server_number != server_number or row.resolved_at is not None:
            return False
        row.resolved_at = datetime.now(timezone.utc)
        row.resolved_by = actor.strip()
        row.resolution_reason = reason.strip()
        return True


def list_pending(server_number: int, limit: int = 50) -> dict:
    server_number, limit = int(server_number), int(limit)
    if not 1 <= server_number <= 32 or not 1 <= limit <= 100:
        raise ValueError("Invalid server or pagination")
    with get_session_maker()() as session:
        connects = session.scalars(select(PendingPlayerConnect)
            .where(PendingPlayerConnect.server_number == server_number)
            .order_by(PendingPlayerConnect.created_at, PendingPlayerConnect.started_event_us)
            .limit(limit + 1)).all()
        disconnects = session.scalars(select(PendingPlayerDisconnect)
            .where(PendingPlayerDisconnect.server_number == server_number)
            .order_by(PendingPlayerDisconnect.created_at, PendingPlayerDisconnect.ended_event_us)
            .limit(limit + 1)).all()
        unidentified = session.scalars(select(UnidentifiedSessionEvent)
            .where(UnidentifiedSessionEvent.server_number == server_number,
                   UnidentifiedSessionEvent.resolved_at.is_(None))
            .order_by(UnidentifiedSessionEvent.event_us, UnidentifiedSessionEvent.fingerprint)
            .limit(limit + 1)).all()
        visible_connects = connects[:limit]
        player_ids = {row.player_id for row in visible_connects}
        identity_ids = dict(session.execute(select(PlayerID.player_id, PlayerID.id).where(PlayerID.player_id.in_(player_ids))).all()) if player_ids else {}
        identities = set(identity_ids)
        candidate_map = {}
        pairs = {(row.player_id, row.started_at) for row in visible_connects}
        if pairs:
            candidates = session.execute(select(PlayerID.player_id, PlayerSession.id, PlayerSession.start, PlayerSession.end)
                .join(PlayerID, PlayerID.id == PlayerSession.player_id_id)
                .where(PlayerSession.server_number == server_number,
                       PlayerSession.start_event_us.is_(None),
                       tuple_(PlayerID.player_id, PlayerSession.start).in_(list(pairs)))
                .order_by(PlayerSession.id)).all()
            for candidate in candidates:
                candidate_map.setdefault((candidate.player_id, candidate.start), []).append(candidate)
        result = []
        for row in visible_connects:
            candidates = list(candidate_map.get((row.player_id, row.started_at), []))
            if row.player_id in identity_ids:
                ids = {candidate.id for candidate in candidates}
                candidates.extend(candidate for candidate in _legacy_connect_log_candidates(
                    session, identity_ids[row.player_id], server_number, row.started_event_us)
                    if candidate.id not in ids)
            result.append({"kind": "connect", "player_id": row.player_id,
                "event_us": str(row.started_event_us), "event_time": _event_time(row.started_event_us), "identity_exists": row.player_id in identities,
                "legacy_candidates": [{"id": candidate.id, "start": candidate.start.isoformat(),
                    "end": candidate.end.isoformat() if candidate.end else None} for candidate in candidates]})
        for row in disconnects[:limit]:
            result.append({"kind": "disconnect", "player_id": row.player_id,
                "event_us": str(row.ended_event_us), "event_time": _event_time(row.ended_event_us)})
        for row in unidentified[:limit]:
            result.append({"kind": "unidentified", "event_kind": row.event_kind,
                "fingerprint": row.fingerprint, "player_name": row.player_name, "raw": row.raw,
                "event_us": str(row.event_us), "event_time": _event_time(row.event_us)})
        return {"results": result, "more_connects": len(connects) > limit,
                "more_disconnects": len(disconnects) > limit, "more_unidentified": len(unidentified) > limit}


def resolve(server_number: int, player_id: str, event_kind: str, event_us: int,
            decision: str, reason: str, actor: str, session_id: int | None = None,
            server_name: str = "") -> bool:
    server_number, event_us = int(server_number), int(event_us)
    if not 1 <= server_number <= 32 or not player_id or not actor or not actor.strip():
        raise ValueError("Invalid server, player or operator")
    if not reason or not reason.strip() or len(reason) > 1000:
        raise ValueError("A short reason is required")
    if event_kind not in {"connect", "disconnect"}:
        raise ValueError("Unknown event type")
    if decision not in ({"link", "create", "discard"} if event_kind == "connect" else {"discard"}):
        raise ValueError("Unsupported review decision")
    with get_session_maker()() as session, session.begin():
        _lock_player_session_events(session, server_number, player_id)
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == player_id).with_for_update())
        model = PendingPlayerConnect if event_kind == "connect" else PendingPlayerDisconnect
        event_key = "started_event_us" if event_kind == "connect" else "ended_event_us"
        pending = session.get(model, {"server_number": server_number, "player_id": player_id, event_key: event_us}, with_for_update=True)
        if pending is None:
            return False
        target = None
        if decision in {"link", "create"}:
            if player is None:
                raise ValueError("Player identity is not available")
            if decision == "link":
                if session_id is None:
                    raise ValueError("A legacy session must be selected")
                target = session.get(PlayerSession, int(session_id), with_for_update=True)
                if (target is None or target.player_id_id != player.id or target.server_number != server_number
                        or target.start_event_us is not None):
                    raise ValueError("The selected legacy session does not match")
                if (target.start != pending.started_at and target.id not in {
                        candidate.id for candidate in _legacy_connect_log_candidates(session, player.id, server_number, event_us)}):
                    raise ValueError("The selected legacy session does not match")
                target.start_event_us = event_us
            else:
                existing = session.scalar(select(PlayerSession.id).where(
                    PlayerSession.player_id_id == player.id, PlayerSession.server_number == server_number,
                    PlayerSession.start_event_us == event_us))
                if existing is not None:
                    raise ValueError("The session is already recorded")
                target = PlayerSession(player=player, server_number=server_number, server_name=server_name,
                    start=pending.started_at, start_event_us=event_us)
                session.add(target)
                session.flush()
        session.delete(pending)
        session.flush()
        if target is not None:
            _reassign_overlapping_disconnects(session, player, target)
            _reconcile_pending_disconnects(session, player, server_number)
        session.add(SessionEventResolution(server_number=server_number, player_id=player_id,
            event_kind=event_kind, event_us=event_us, decision=decision, reason=reason.strip(),
            session_id=target.id if target is not None else None, actor=actor.strip()[:150],
            created_at=datetime.now(timezone.utc)))
        return True
