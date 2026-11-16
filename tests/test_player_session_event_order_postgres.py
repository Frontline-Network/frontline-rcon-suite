"""Verify session-event serialization with real PostgreSQL row locks."""
import os
import time
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import datetime, timezone
from threading import Barrier
from types import SimpleNamespace
from uuid import uuid4

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.orm import sessionmaker

from rcon import player_history, session_event_review
from rcon.models import LogLine, PendingPlayerConnect, PendingPlayerDisconnect, PlayerID, PlayerSession, SessionEventResolution, UnidentifiedSessionEvent
from rcon.session_event_journal import SessionEventJournal


@pytest.fixture
def database(monkeypatch):
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "session_event_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"}, pool_size=8)
    PlayerID.__table__.create(engine)
    PlayerSession.__table__.create(engine)
    LogLine.__table__.create(engine)
    PendingPlayerDisconnect.__table__.create(engine)
    PendingPlayerConnect.__table__.create(engine)
    SessionEventResolution.__table__.create(engine)
    UnidentifiedSessionEvent.__table__.create(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    with maker.begin() as session:
        session.add(PlayerID(player_id="synthetic-id"))
    @contextmanager
    def context():
        with maker() as session:
            yield session
            session.commit()
    monkeypatch.setattr(player_history, "player_session_event_session", context)
    monkeypatch.setattr(session_event_review, "get_session_maker", lambda: maker)
    monkeypatch.setattr(player_history, "get_server_number", lambda: "3")
    monkeypatch.setattr(player_history.RconServerSettingsUserConfig, "load_from_db", lambda: SimpleNamespace(short_name="test"))
    try:
        yield maker
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def run_parallel(function):
    barrier = Barrier(2)
    def invoke():
        barrier.wait(timeout=10)
        function()
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(invoke) for _ in range(2)]
        for future in futures:
            future.result(timeout=20)


def test_concurrent_duplicate_connect_creates_one_session(database):
    run_parallel(lambda: player_history.save_start_player_session("synthetic-id", 1_700_000_000, server_number=3))
    with database() as session:
        assert len(session.scalars(select(PlayerSession)).all()) == 1


def test_unidentified_transfer_is_idempotent_and_review_is_server_scoped(database, tmp_path):
    journal = SessionEventJournal(tmp_path / "events.sqlite")
    event = (3, "disconnect", 1_700_000_000_000_000, "", "DISCONNECTED ()")
    journal.remember_batch([], 0, [event])

    def commit_then_crash(*values):
        session_event_review.record_unidentified(*values)
        raise RuntimeError("interrupted before local acknowledgement")

    with pytest.raises(RuntimeError):
        journal.publish_unidentified(commit_then_crash)
    assert journal.publish_unidentified(session_event_review.record_unidentified) == 1
    with database() as session:
        records = session.scalars(select(UnidentifiedSessionEvent)).all()
        assert len(records) == 1
        fingerprint = records[0].fingerprint
    assert session_event_review.list_pending(4)["results"] == []
    assert not session_event_review.discard_unidentified(4, fingerprint, "verified", "operator")
    assert session_event_review.discard_unidentified(3, fingerprint, "verified", "operator")
    assert not session_event_review.discard_unidentified(3, fingerprint, "replay", "operator")
    assert session_event_review.record_unidentified(*event) == fingerprint
    assert session_event_review.list_pending(3)["results"] == []
    with database() as session:
        record = session.get(UnidentifiedSessionEvent, fingerprint)
        assert (record.resolved_by, record.resolution_reason) == ("operator", "verified")


def test_journal_replay_after_postgres_commit_is_idempotent(database, tmp_path):
    path = tmp_path / "session-events.sqlite"
    event_us = 1_700_000_000_000_000
    journal = SessionEventJournal(path)
    journal.remember(3, "synthetic-id", "connect", event_us)

    def commit_then_crash(server, player, kind, event):
        assert player_history.save_start_player_session(player, event / 1_000_000, server_number=server)
        raise RuntimeError("process exited before local acknowledgement")

    with pytest.raises(RuntimeError):
        journal.drain(commit_then_crash)
    recovered = SessionEventJournal(path)
    assert recovered.drain(lambda server, player, kind, event:
                           player_history.save_start_player_session(player, event / 1_000_000, server_number=server)) == 1
    with database() as session:
        rows = session.scalars(select(PlayerSession)).all()
        assert len(rows) == 1 and rows[0].start_event_us == event_us


def test_concurrent_connects_without_identity_are_retained_once(database):
    run_parallel(lambda: player_history.save_start_player_session("unknown-id", 1_700_000_000, server_number=3))
    with database() as session:
        assert len(session.scalars(select(PendingPlayerConnect)).all()) == 1


def test_concurrent_duplicate_disconnect_does_not_close_older_session(database):
    player_history.save_start_player_session("synthetic-id", 1_700_000_000, server_number=3)
    player_history.save_start_player_session("synthetic-id", 1_700_000_100, server_number=3)
    run_parallel(lambda: player_history.save_end_player_session("synthetic-id", 1_700_000_150))
    with database() as session:
        older, newer = session.scalars(select(PlayerSession).order_by(PlayerSession.start)).all()
        assert older.end is None
        assert newer.end is not None


def test_postgres_legacy_open_session_is_matched_only_with_absolute_log(database, monkeypatch):
    monkeypatch.delenv("HLL_SESSION_LEGACY_UTC", raising=False)
    start = 1_700_000_000
    with database.begin() as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "synthetic-id"))
        wall_time = datetime.fromtimestamp(start, timezone.utc).replace(tzinfo=None)
        session.add(PlayerSession(player=player, start=wall_time, server_number=3, server_name="legacy"))
        session.add(LogLine(type="CONNECTED", server="3", player1_player_id=player.id,
                            event_time=wall_time, raw=f"[0 ms ({start})] CONNECTED fake", weapon="", content=""))
    player_history.save_end_player_session("synthetic-id", start + 50)
    with database() as session:
        saved = session.scalar(select(PlayerSession))
        assert (saved.start_event_us, saved.end_event_us) == (start * 1_000_000, (start + 50) * 1_000_000)


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="process timezone control requires tzset")
def test_postgres_fall_back_records_absolute_event_duration(database, monkeypatch):
    old_tz = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "Europe/Berlin")
    time.tzset()
    try:
        start, end = 1_729_990_200, 1_729_991_400
        player_history.save_start_player_session("synthetic-id", start, server_number=3)
        player_history.save_end_player_session("synthetic-id", end)
        with database() as session:
            saved = session.scalar(select(PlayerSession))
            assert saved.end_event_us - saved.start_event_us == 1_200_000_000
            assert (saved.to_dict()["end"] - saved.to_dict()["start"]).total_seconds() == 1200
    finally:
        if old_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = old_tz
        time.tzset()


def test_concurrent_review_records_one_decision(database):
    start_us = 1_700_000_000_000_000
    with database.begin() as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "synthetic-id"))
        legacy = PlayerSession(player=player, start=datetime.fromtimestamp(start_us / 1_000_000), server_number=3, server_name="test")
        session.add(legacy)
        session.add(PendingPlayerConnect(server_number=3, player_id="synthetic-id", started_event_us=start_us,
                                         started_at=datetime.fromtimestamp(start_us / 1_000_000)))
        session.flush()
        legacy_id = legacy.id
    barrier = Barrier(2)
    def review():
        barrier.wait(timeout=10)
        return session_event_review.resolve(3, "synthetic-id", "connect", start_us, "link",
                                            "verified with logs", "Operator", session_id=legacy_id)
    with ThreadPoolExecutor(max_workers=2) as executor:
        futures = [executor.submit(review) for _ in range(2)]
        assert sorted(future.result(timeout=20) for future in futures) == [False, True]
    with database() as session:
        assert len(session.scalars(select(SessionEventResolution)).all()) == 1
