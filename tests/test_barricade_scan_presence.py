"""Synthetic bounded evidence; not a claim about unseen game-server logs."""
import asyncio
import time
from datetime import datetime
from unittest.mock import Mock

from sqlalchemy.orm import Session, sessionmaker

from rcon import barricade_scan_presence as candidate
from rcon.models import PlayerID, PlayerSession, PendingPlayerDisconnect, UnidentifiedSessionEvent
from rcon.player_presence import PresenceWindow
from rcon.session_journal_observation import JournalObservation
from tests.test_report_session_selection import database


def test_only_consistent_bounded_evidence_accepts_current_session(database, monkeypatch):
    UnidentifiedSessionEvent.__table__.create(database)
    now = time.time()
    start = now - 60
    with Session(database) as session, session.begin():
        player = PlayerID(player_id='synthetic-eos')
        session.add(player)
        session.flush()
        row = PlayerSession(player_id_id=player.id, server_number=3,
            start=datetime.fromtimestamp(start), start_event_us=int(start * 1_000_000))
        session.add(row)
        session.flush()
        session_id = row.id
    maker = sessionmaker(database, expire_on_commit=False)
    monkeypatch.setattr(candidate, 'get_session_maker', lambda: maker)
    monkeypatch.setattr(candidate, 'redis_time', lambda _red: now)
    monkeypatch.setattr(candidate.time, 'time', lambda: now)
    seen = {'synthetic-eos': PresenceWindow(now - 10, now - 9)}
    roster = Mock(return_value=(seen, {3}))
    status = Mock(return_value=JournalObservation(now - 8, now - 7, now - 6, now - 5, 0, 0))
    monkeypatch.setattr(candidate, 'read_observations', roster)
    monkeypatch.setattr(candidate, 'read_journal_observation', status)
    def check():
        return candidate.session_has_bounded_evidence(object(), scope='synthetic', server_number=3,
                                                       session_id=session_id, player_id='synthetic-eos')
    assert check() is True
    def check_after(barrier):
        return candidate.session_has_bounded_evidence(object(), scope='synthetic', server_number=3,
            session_id=session_id, player_id='synthetic-eos', min_poll_started_at=barrier)
    # A readable but pre-barrier observation must not prove the collector is
    # currently connected to Redis. Equality is also insufficient.
    assert check_after(now - 7) is None
    assert check_after(now - 8) is None
    assert check_after(now - 9) is True
    roster.side_effect = [(seen, {3}), ({}, {3})]
    assert check() is None
    roster.side_effect = [(seen, {3}), ({'synthetic-eos': PresenceWindow(now - 2, now - 1)}, {3})]
    assert check() is None
    roster.side_effect = [(seen, {3}), OSError('synthetic redis outage')]
    assert check() is None
    roster.side_effect = None
    status.side_effect = [JournalObservation(now - 8, now - 7, now - 6, now - 5, 0, 0),
                          JournalObservation(now - 4, now - 3, now - 2, now - 1, 1, 0)]
    assert check() is None
    status.side_effect = None
    status.return_value = JournalObservation(now - 8, now - 7, now - 6, now - 5, 1, 0)
    assert check() is None
    status.return_value = JournalObservation(now - 11, now - 7, now - 6, now - 5, 0, 0)
    assert check() is None
    status.return_value = JournalObservation(now - 8, now - 7, now - 6, now - 5, 0, 0)
    roster.return_value = ({}, {3})
    assert check() is False
    roster.side_effect = OSError('synthetic redis outage')
    assert check() is None
    roster.side_effect = None
    roster.return_value = ({'synthetic-eos': PresenceWindow(now - 31, now - 30)}, {3})
    assert check() is None
    roster.return_value = (seen, set())
    assert check() is None
    roster.return_value = (seen, {3})
    with maker.begin() as session:
        session.add(PendingPlayerDisconnect(server_number=3, player_id='synthetic-eos',
            ended_at=datetime.fromtimestamp(now - 1), ended_event_us=int((now - 1) * 1_000_000)))
    assert check() is None
    with maker.begin() as session:
        session.query(PendingPlayerDisconnect).delete()
        session.add(UnidentifiedSessionEvent(fingerprint='x' * 64, server_number=3,
            event_kind='disconnect', event_us=int((now - 1) * 1_000_000), player_name='', raw='synthetic'))
    assert check() is None


def test_fresh_poll_barrier_defers_stale_observations_and_accepts_new_poll(monkeypatch):
    monkeypatch.setattr(candidate, 'redis_time', lambda _red: 123.0)
    check = Mock(return_value=None)
    monkeypatch.setattr(candidate, 'session_has_bounded_evidence', check)
    kwargs = dict(scope='synthetic', server_number=3, session_id=1, player_id='synthetic-eos')
    assert asyncio.run(candidate.confirm_with_fresh_poll(object(), timeout=0, **kwargs)) is None
    assert check.call_args.kwargs['min_poll_started_at'] == 123.0
    check.side_effect = [None, True]
    assert asyncio.run(candidate.confirm_with_fresh_poll(object(), timeout=2, **kwargs)) is True
    assert check.call_count == 3
    check.side_effect = None
    check.return_value = False
    assert asyncio.run(candidate.confirm_with_fresh_poll(object(), timeout=2, **kwargs)) is False
    monkeypatch.setattr(candidate, 'redis_time', Mock(side_effect=OSError('partition')))
    assert asyncio.run(candidate.confirm_with_fresh_poll(object(), timeout=0, **kwargs)) is None
