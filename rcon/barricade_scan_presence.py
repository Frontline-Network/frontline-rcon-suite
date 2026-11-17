"""Experimental, bounded evidence for a Barricade scan candidate.

Used only by the opt-in consumer. A fresh log poll is not a guarantee that the
game server has already exposed every event; an unobserved reconnect remains
possible.
"""
import time

from sqlalchemy import select

from rcon.models import PlayerSession, UnidentifiedSessionEvent, get_session_maker
from rcon.player_presence import MAX_SNAPSHOT_AGE_SECONDS, read_observations, redis_time
from rcon.report_admin import session_token
from rcon.session_journal_observation import read as read_journal_observation


def observed_players(red, *, scope: str, server_number: int):
    """Bounded roster evidence for operator review, not session identity."""
    if type(server_number) is not int or not 1 <= server_number <= 32:
        return None
    try:
        if abs(redis_time(red) - time.time()) > 2:
            return None
        sightings, available = read_observations(red, scope=scope, server_numbers=[server_number])
        if server_number not in available:
            return None
        return frozenset(sightings)
    except Exception:
        return None


def player_is_currently_observed(red, *, scope: str, server_number: int, player_id: str):
    if not isinstance(player_id, str) or not player_id or len(player_id) > 100:
        return None
    players = observed_players(red, scope=scope, server_number=server_number)
    return player_id in players if players is not None else None


def session_has_bounded_evidence(red, *, scope: str, server_number: int, session_id: int, player_id: str):
    """True means observed evidence is consistent, not that unseen logs cannot exist.

    False means a fresh roster does not contain the player. None means the
    available evidence is missing or ambiguous. No player action is taken.
    """
    if (type(server_number) is not int or not 1 <= server_number <= 32 or
            type(session_id) is not int or session_id <= 0 or
            not isinstance(player_id, str) or not player_id or len(player_id) > 100):
        return None
    try:
        if abs(redis_time(red) - time.time()) > 2:
            return None
        sightings, available = read_observations(red, scope=scope, server_numbers=[server_number])
        if server_number not in available:
            return None
        window = sightings.get(player_id)
        if window is None:
            return False
        observation = read_journal_observation(red, scope=scope, server_number=server_number)
        if (observation is None or observation.pending or observation.unpublished_anonymous or
                observation.poll_started_at < window.latest):
            return None
        with get_session_maker()() as session:
            if session_token(session, server_number, player_id, window.earliest) != session_id:
                return None
            row = session.get(PlayerSession, session_id)
            if row is None or row.start_event_us is None:
                return None
            # An unresolved identity-free event could belong to this player.
            ambiguous = session.scalar(select(UnidentifiedSessionEvent.fingerprint).where(
                UnidentifiedSessionEvent.server_number == server_number,
                UnidentifiedSessionEvent.resolved_at.is_(None),
                UnidentifiedSessionEvent.event_us >= row.start_event_us).limit(1))
            if ambiguous is not None:
                return None
        # A newer roster may contradict the snapshot while the database is
        # being read. Never use a superseded sighting as proof of presence.
        latest_sightings, latest_available = read_observations(red, scope=scope, server_numbers=[server_number])
        if server_number not in latest_available or latest_sightings.get(player_id) != window:
            return None
        # Reject evidence that expired during database work or was replaced.
        now = redis_time(red)
        if (abs(now - time.time()) > 2 or not 0 <= now - window.earliest <= MAX_SNAPSHOT_AGE_SECONDS or
                read_journal_observation(red, scope=scope, server_number=server_number) != observation):
            return None
        return True
    except Exception:
        # DB, Redis and malformed configuration are unknown, never presence.
        return None
