"""Session events must only affect a matching server and time interval."""
from contextlib import contextmanager
from datetime import datetime, timezone
from itertools import permutations
import os
import time
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine, delete, select
from sqlalchemy.orm import Session, sessionmaker

from rcon import player_history
from rcon import session_event_review
from rcon.models import LogLine, PendingPlayerConnect, PendingPlayerDisconnect, PlayerID, PlayerSession, SessionEventResolution, UnidentifiedSessionEvent
from rcon.session_event_journal import SessionEventJournal


@pytest.fixture
def database(monkeypatch):
    engine = create_engine("sqlite://")
    PlayerID.__table__.create(engine)
    PlayerSession.__table__.create(engine)
    LogLine.__table__.create(engine)
    PendingPlayerDisconnect.__table__.create(engine)
    PendingPlayerConnect.__table__.create(engine)
    SessionEventResolution.__table__.create(engine)
    UnidentifiedSessionEvent.__table__.create(engine)
    with Session(engine) as session:
        session.add(PlayerID(player_id="fake-console-id"))
        session.commit()
    @contextmanager
    def context():
        with Session(engine) as session:
            yield session
            session.commit()
    monkeypatch.setattr(player_history, "player_session_event_session", context)
    monkeypatch.setattr(session_event_review, "get_session_maker", lambda: sessionmaker(engine, expire_on_commit=False))
    monkeypatch.setattr(player_history.RconServerSettingsUserConfig, "load_from_db", lambda: SimpleNamespace(short_name="test"))
    yield engine
    engine.dispose()


def sessions(engine):
    with Session(engine) as session:
        return list(session.scalars(select(PlayerSession).order_by(PlayerSession.id)))


def test_equal_connect_times_on_different_servers_are_distinct(database):
    timestamp = 1_700_000_000
    player_history.save_start_player_session("fake-console-id", timestamp, server_number=1)
    player_history.save_start_player_session("fake-console-id", timestamp, server_number=2)
    assert [row.server_number for row in sessions(database)] == [1, 2]


def test_delayed_disconnect_only_closes_eligible_session_on_its_server(database, monkeypatch):
    timestamp = 1_700_000_000
    player_history.save_start_player_session("fake-console-id", timestamp, server_number=1)
    player_history.save_start_player_session("fake-console-id", timestamp + 100, server_number=2)
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    player_history.save_end_player_session("fake-console-id", timestamp + 50)
    first, second = sessions(database)
    assert first.end == datetime.fromtimestamp(timestamp + 50)
    assert second.end is None


def test_late_disconnect_finds_older_open_session_and_duplicate_is_idempotent(database, monkeypatch):
    timestamp = 1_700_000_000
    player_history.save_start_player_session("fake-console-id", timestamp, server_number=1)
    player_history.save_start_player_session("fake-console-id", timestamp + 100, server_number=1)
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    player_history.save_end_player_session("fake-console-id", timestamp + 150)
    player_history.save_end_player_session("fake-console-id", timestamp + 50)
    player_history.save_end_player_session("fake-console-id", timestamp + 50)
    first, second = sessions(database)
    assert first.end == datetime.fromtimestamp(timestamp + 50)
    assert second.end == datetime.fromtimestamp(timestamp + 150)
    assert len(sessions(database)) == 2


def test_disconnect_before_start_never_creates_negative_session(database, monkeypatch):
    timestamp = 1_700_000_000
    player_history.save_start_player_session("fake-console-id", timestamp, server_number=1)
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    player_history.save_end_player_session("fake-console-id", timestamp - 1)
    assert sessions(database)[0].end is None


def test_disconnect_arriving_before_its_connect_is_applied_later(database, monkeypatch):
    timestamp = 1_700_000_000
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    player_history.save_end_player_session("fake-console-id", timestamp + 50)
    player_history.save_start_player_session("fake-console-id", timestamp, server_number=1)
    assert sessions(database)[0].end == datetime.fromtimestamp(timestamp + 50)


def test_deferred_disconnect_survives_missing_identity_and_duplicate_event(database, monkeypatch):
    timestamp = 1_700_000_000
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    player_history.save_end_player_session("new-fake-id", timestamp + 50)
    player_history.save_end_player_session("new-fake-id", timestamp + 50)
    with Session(database) as session:
        assert len(session.scalars(select(PendingPlayerDisconnect)).all()) == 1
        session.add(PlayerID(player_id="new-fake-id"))
        session.commit()
    player_history.save_start_player_session("new-fake-id", timestamp, server_number=1)
    with Session(database) as session:
        assert session.scalars(select(PendingPlayerDisconnect)).all() == []
        result = session.scalar(select(PlayerSession))
        assert result.end == datetime.fromtimestamp(timestamp + 50)


def test_connect_without_identity_is_retained_and_replayed_safely(database):
    timestamp = 1_700_000_000
    player_history.save_start_player_session("new-fake-id", timestamp, server_number=1)
    player_history.save_start_player_session("new-fake-id", timestamp, server_number=1)
    with Session(database) as session:
        assert len(session.scalars(select(PendingPlayerConnect)).all()) == 1
        session.add(PlayerID(player_id="new-fake-id"))
        session.commit()
    player_history.save_start_player_session("new-fake-id", timestamp, server_number=1)
    with Session(database) as session:
        assert session.scalars(select(PendingPlayerConnect)).all() == []
        assert session.scalar(select(PlayerSession)).start_event_us == timestamp * 1_000_000


def test_journal_retries_missing_identity_without_replaying_other_actions(database, tmp_path, monkeypatch):
    timestamp = 1_700_000_000
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    path = tmp_path / "journal.sqlite"
    journal = SessionEventJournal(path)
    journal.remember_batch([(1, "new-fake-id", "connect", timestamp * 1_000_000),
                            (1, "new-fake-id", "disconnect", (timestamp + 50) * 1_000_000)], 0)

    def handle(server, player, kind, event_us):
        if kind == "connect":
            return player_history.save_start_player_session(player, event_us / 1_000_000, server_number=server)
        player_history.save_end_player_session(player, event_us / 1_000_000)

    assert journal.drain(handle) == 1  # disconnect retained in PostgreSQL; connect waits
    with Session(database) as session:
        assert len(session.scalars(select(PendingPlayerConnect)).all()) == 1
        assert len(session.scalars(select(PendingPlayerDisconnect)).all()) == 1
        session.add(PlayerID(player_id="new-fake-id"))
        session.commit()
    assert SessionEventJournal(path).drain(handle, retry_delay_seconds=0) == 1
    with Session(database) as session:
        saved = session.scalar(select(PlayerSession))
        assert (saved.start_event_us, saved.end_event_us) == (timestamp * 1_000_000, (timestamp + 50) * 1_000_000)
        assert session.scalars(select(PendingPlayerConnect)).all() == []
        assert session.scalars(select(PendingPlayerDisconnect)).all() == []


def test_pending_disconnect_does_not_cross_servers_or_a_later_session(database, monkeypatch):
    timestamp = 1_700_000_000
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    player_history.save_end_player_session("fake-console-id", timestamp + 150)
    player_history.save_start_player_session("fake-console-id", timestamp + 100, server_number=2)
    player_history.save_start_player_session("fake-console-id", timestamp + 200, server_number=1)
    player_history.save_start_player_session("fake-console-id", timestamp, server_number=1)
    rows = sessions(database)
    assert rows[0].end is None and rows[0].server_number == 2
    assert rows[1].end is None and rows[1].server_number == 1
    assert rows[2].end == datetime.fromtimestamp(timestamp + 150)


def test_late_intermediate_connect_reassigns_previously_matched_disconnect(database, monkeypatch):
    timestamp = 1_700_000_000
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    player_history.save_end_player_session("fake-console-id", timestamp + 150)
    player_history.save_start_player_session("fake-console-id", timestamp, server_number=1)
    player_history.save_start_player_session("fake-console-id", timestamp + 100, server_number=1)
    first, second = sessions(database)
    assert first.end is None
    assert second.end == datetime.fromtimestamp(timestamp + 150)


@pytest.mark.parametrize("events", list(permutations(("start_a", "end_a", "start_b", "end_b"))))
def test_two_sessions_converge_for_every_event_arrival_order(database, monkeypatch, events):
    timestamp = 1_700_000_000
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    actions = {
        "start_a": lambda: player_history.save_start_player_session("fake-console-id", timestamp, server_number=1),
        "end_a": lambda: player_history.save_end_player_session("fake-console-id", timestamp + 50),
        "start_b": lambda: player_history.save_start_player_session("fake-console-id", timestamp + 100, server_number=1),
        "end_b": lambda: player_history.save_end_player_session("fake-console-id", timestamp + 150),
    }
    for event in events:
        actions[event]()
    rows = sorted(sessions(database), key=lambda row: row.start)
    assert [(row.start, row.end) for row in rows] == [
        (datetime.fromtimestamp(timestamp), datetime.fromtimestamp(timestamp + 50)),
        (datetime.fromtimestamp(timestamp + 100), datetime.fromtimestamp(timestamp + 150)),
    ]
    with Session(database) as session:
        assert session.scalars(select(PendingPlayerDisconnect)).all() == []


@pytest.mark.filterwarnings("ignore:datetime.datetime.utcnow:DeprecationWarning")
def test_three_sessions_converge_for_every_event_arrival_order(database, monkeypatch):
    timestamp = 1_700_000_000
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    events = [(kind, offset) for offset in (0, 100, 200) for kind in ("start", "end")]
    for ordering in permutations(events):
        with Session(database) as session:
            session.execute(delete(PendingPlayerDisconnect))
            session.execute(delete(PlayerSession))
            session.commit()
        for kind, offset in ordering:
            if kind == "start":
                player_history.save_start_player_session("fake-console-id", timestamp + offset, server_number=1)
            else:
                player_history.save_end_player_session("fake-console-id", timestamp + offset + 50)
        rows = sorted(sessions(database), key=lambda row: row.start)
        assert [(row.start, row.end) for row in rows] == [
            (datetime.fromtimestamp(timestamp + offset), datetime.fromtimestamp(timestamp + offset + 50))
            for offset in (0, 100, 200)
        ], ordering
        with Session(database) as session:
            assert session.scalars(select(PendingPlayerDisconnect)).all() == [], ordering


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="process timezone control requires tzset")
@pytest.mark.parametrize('zone', ['UTC', 'Europe/Berlin', 'America/New_York', 'Pacific/Kiritimati'])
def test_absolute_session_duration_is_independent_of_process_timezone(database, monkeypatch, zone):
    original_tz = os.environ.get('TZ')
    monkeypatch.setenv('TZ', zone)
    time.tzset()
    try:
        monkeypatch.setattr(player_history, 'get_server_number', lambda: '1')
        start, end = 1_729_990_200, 1_729_991_400
        player_history.save_start_player_session('fake-console-id', start, server_number=1)
        player_history.save_end_player_session('fake-console-id', end)
        with Session(database) as session:
            player = session.scalar(select(PlayerID).where(PlayerID.player_id == 'fake-console-id'))
            assert player.get_total_playtime_seconds() == 1200
            assert player.sessions[0].end_event_us - player.sessions[0].start_event_us == 1_200_000_000
    finally:
        if original_tz is None:
            os.environ.pop('TZ', None)
        else:
            os.environ['TZ'] = original_tz
        time.tzset()


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="process timezone control requires tzset")
@pytest.mark.parametrize("start,end", [
    (1_729_990_200, 1_729_991_400),  # 2024-10-27 fall-back
    (1_711_846_200, 1_711_847_400),  # 2024-03-31 spring-forward
])
def test_session_crossing_dst_change_keeps_real_event_order(database, monkeypatch, start, end):
    original_tz = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "Europe/Berlin")
    time.tzset()
    try:
        monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
        player_history.save_start_player_session("fake-console-id", start, server_number=1)
        player_history.save_end_player_session("fake-console-id", end)
        result = sessions(database)[0]
        assert result.end is not None
        assert result.end_event_us - result.start_event_us == 1_200_000_000
        with Session(database) as session:
            player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
            assert player.get_total_playtime_seconds() == 1200
            serialized = player.sessions[0].to_dict()
            assert (serialized["end"] - serialized["start"]).total_seconds() == 1200
            assert serialized["start"].utcoffset().total_seconds() == 0
        active = SimpleNamespace(end=None, start=result.start, created=result.created, start_event_us=result.start_event_us)
        now = datetime.fromtimestamp(end, timezone.utc)
        assert player_history._current_playtime_seconds(active, now=now) == 1200
    finally:
        if original_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original_tz
        time.tzset()


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="process timezone control requires tzset")
def test_repeated_local_connect_time_does_not_merge_distinct_sessions(database, monkeypatch):
    original_tz = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "Europe/Berlin")
    time.tzset()
    try:
        monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
        first, second = 1_729_989_000, 1_729_992_600
        player_history.save_start_player_session("fake-console-id", first, server_number=1)
        player_history.save_end_player_session("fake-console-id", first + 300)
        player_history.save_start_player_session("fake-console-id", second, server_number=1)
        player_history.save_end_player_session("fake-console-id", second + 300)
        rows = sessions(database)
        assert len(rows) == 2 and rows[0].start == rows[1].start
        assert [row.start_event_us for row in rows] == [first * 1_000_000, second * 1_000_000]
        assert all(row.end_event_us - row.start_event_us == 300_000_000 for row in rows)
    finally:
        if original_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original_tz
        time.tzset()


def test_legacy_session_is_not_reinterpreted_without_explicit_utc_setting(database, monkeypatch):
    monkeypatch.delenv("HLL_SESSION_LEGACY_UTC", raising=False)
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
        session.add(PlayerSession(player=player, start=datetime(2024, 10, 27, 2, 50), server_number=1, server_name="legacy"))
        session.commit()
    player_history.save_end_player_session("fake-console-id", 1_729_991_400)
    with Session(database) as session:
        saved = session.scalar(select(PlayerSession))
        assert saved.start_event_us is None and saved.end is None
        assert len(session.scalars(select(PendingPlayerDisconnect)).all()) == 1


@pytest.mark.parametrize("log_count", [0, 1, 2])
def test_unverified_legacy_start_is_not_inferred_from_logs(database, monkeypatch, log_count):
    monkeypatch.delenv("HLL_SESSION_LEGACY_UTC", raising=False)
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    start = 1_700_000_000
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
        wall_time = datetime.fromtimestamp(start, timezone.utc).replace(tzinfo=None)
        session.add(PlayerSession(player=player, start=wall_time, server_number=1, server_name="legacy"))
        for index in range(log_count):
            session.add(LogLine(type="CONNECTED", server="1", player1_player_id=player.id,
                                event_time=wall_time, raw=f"[0 ms ({start})] CONNECTED fake-{index}",
                                weapon="", content=""))
        session.commit()
    player_history.save_end_player_session("fake-console-id", start + 50)
    with Session(database) as session:
        saved = session.scalar(select(PlayerSession))
        pending = session.scalars(select(PendingPlayerDisconnect)).all()
        assert saved.start_event_us is None and saved.end is None
        assert len(pending) == 1


def test_one_connect_log_does_not_choose_between_duplicate_legacy_rows(database, monkeypatch):
    monkeypatch.delenv("HLL_SESSION_LEGACY_UTC", raising=False)
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    start = 1_700_000_000
    wall_time = datetime.fromtimestamp(start, timezone.utc).replace(tzinfo=None)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
        session.add_all([PlayerSession(player=player, start=wall_time, server_number=1, server_name="legacy") for _ in range(2)])
        session.add(LogLine(type="CONNECTED", server="1", player1_player_id=player.id,
                            event_time=wall_time, raw=f"[0 ms ({start})] CONNECTED fake", weapon="", content=""))
        session.commit()
    player_history.save_end_player_session("fake-console-id", start + 50)
    with Session(database) as session:
        assert all(row.start_event_us is None and row.end is None for row in session.scalars(select(PlayerSession)).all())
        assert len(session.scalars(select(PendingPlayerDisconnect)).all()) == 1


def test_two_connect_logs_with_same_wall_time_do_not_prove_legacy_start(database, monkeypatch):
    monkeypatch.delenv("HLL_SESSION_LEGACY_UTC", raising=False)
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    start = 1_729_991_400
    wall_time = datetime.fromtimestamp(start, timezone.utc).replace(tzinfo=None)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
        session.add(PlayerSession(player=player, start=wall_time, server_number=1, server_name="legacy"))
        for epoch in (start, start - 3600):
            session.add(LogLine(type="CONNECTED", server="1", player1_player_id=player.id,
                                event_time=wall_time, raw=f"[0 ms ({epoch})] CONNECTED fake", weapon="", content=""))
        session.commit()
    player_history.save_end_player_session("fake-console-id", start + 50)
    with Session(database) as session:
        saved = session.scalar(select(PlayerSession))
        assert saved.start_event_us is None
        assert saved.end_event_us is None
        assert len(session.scalars(select(PendingPlayerDisconnect)).all()) == 1


def test_late_conflicting_connect_does_not_infer_legacy_start(database, monkeypatch):
    monkeypatch.delenv('HLL_SESSION_LEGACY_UTC', raising=False)
    monkeypatch.setattr(player_history, 'get_server_number', lambda: '1')
    start = 1_729_991_400
    wall = datetime.fromtimestamp(start, timezone.utc).replace(tzinfo=None)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == 'fake-console-id'))
        session.add(PlayerSession(player=player, start=wall, server_number=1, server_name='legacy'))
        session.add(LogLine(type='CONNECTED', server='1', player1_player_id=player.id,
                            event_time=wall, raw=f'[0 ms ({start})] CONNECTED fake', weapon='', content=''))
        session.commit()
    player_history.save_end_player_session('fake-console-id', start + 50)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == 'fake-console-id'))
        session.add(LogLine(type='CONNECTED', server='1', player1_player_id=player.id,
                            event_time=wall, raw=f'[0 ms ({start - 3600})] CONNECTED fake', weapon='', content=''))
        session.commit()
    player_history.save_end_player_session('fake-console-id', start + 50)
    with Session(database) as session:
        saved = session.scalar(select(PlayerSession))
        assert saved.start_event_us is None
        assert saved.end_event_us is None
        assert session.scalar(select(PendingPlayerConnect)) is None
        assert session.scalar(select(PendingPlayerDisconnect)) is not None


def test_previously_assigned_start_is_not_rewritten_without_provenance(database, monkeypatch):
    monkeypatch.delenv('HLL_SESSION_LEGACY_UTC', raising=False)
    monkeypatch.setattr(player_history, 'get_server_number', lambda: '1')
    start = 1_729_991_400
    wall = datetime.fromtimestamp(start, timezone.utc).replace(tzinfo=None)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == 'fake-console-id'))
        session.add(PlayerSession(player=player, start=wall, start_event_us=start * 1_000_000,
                                  end_event_us=(start + 50) * 1_000_000,
                                  end=datetime.fromtimestamp(start + 50), server_number=1))
        session.add(LogLine(type='CONNECTED', server='1', player1_player_id=player.id,
                            event_time=wall, raw=f'[0 ms ({start - 3600})] CONNECTED fake', weapon='', content=''))
        session.commit()
    player_history.save_end_player_session('fake-console-id', start + 50)
    with Session(database) as session:
        saved = session.scalar(select(PlayerSession))
        assert saved.start_event_us == start * 1_000_000
        assert saved.end_event_us == (start + 50) * 1_000_000


def test_unknown_legacy_start_prevents_ambiguous_disconnect_from_closing_new_session(database, monkeypatch):
    monkeypatch.delenv('HLL_SESSION_LEGACY_UTC', raising=False)
    monkeypatch.setattr(player_history, 'get_server_number', lambda: '1')
    start = 1_700_000_000
    player_history.save_start_player_session('fake-console-id', start, server_number=1)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == 'fake-console-id'))
        session.add(PlayerSession(player=player, start=datetime.fromtimestamp(start + 10),
                                  server_number=1, server_name='legacy'))
        session.commit()
    player_history.save_end_player_session('fake-console-id', start + 20)
    with Session(database) as session:
        rows = list(session.scalars(select(PlayerSession).order_by(PlayerSession.id)))
        assert rows[0].end_event_us is None
        assert rows[1].start_event_us is None and rows[1].end_event_us is None
        assert session.scalar(select(PendingPlayerDisconnect)) is not None


def test_closed_provably_older_legacy_session_does_not_block_new_session(database, monkeypatch):
    monkeypatch.delenv('HLL_SESSION_LEGACY_UTC', raising=False)
    monkeypatch.setattr(player_history, 'get_server_number', lambda: '1')
    start = 1_700_000_000
    player_history.save_start_player_session('fake-console-id', start, server_number=1)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == 'fake-console-id'))
        session.add(PlayerSession(player=player, start=datetime.fromtimestamp(start - 200_000),
                                  end=datetime.fromtimestamp(start - 100_000), server_number=1))
        session.commit()
    player_history.save_end_player_session('fake-console-id', start + 20)
    with Session(database) as session:
        rows = list(session.scalars(select(PlayerSession).order_by(PlayerSession.id)))
        assert rows[0].end_event_us == (start + 20) * 1_000_000
        assert session.scalar(select(PendingPlayerDisconnect)) is None


def test_open_provably_older_legacy_start_does_not_block_new_session(database, monkeypatch):
    monkeypatch.delenv('HLL_SESSION_LEGACY_UTC', raising=False)
    monkeypatch.setattr(player_history, 'get_server_number', lambda: '1')
    start = 1_700_000_000
    player_history.save_start_player_session('fake-console-id', start, server_number=1)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == 'fake-console-id'))
        session.add(PlayerSession(player=player, start=datetime.fromtimestamp(start - 100_000),
                                  end=None, server_number=1))
        session.commit()
    player_history.save_end_player_session('fake-console-id', start + 20)
    with Session(database) as session:
        rows = list(session.scalars(select(PlayerSession).order_by(PlayerSession.id)))
        assert rows[0].end_event_us == (start + 20) * 1_000_000
        assert rows[1].end_event_us is None
        assert session.scalar(select(PendingPlayerDisconnect)) is None


def test_verified_utc_history_does_not_block_definitely_earlier_closed_session(database, monkeypatch):
    monkeypatch.setattr(player_history, '_fixed_utc_timezone', lambda: True)
    monkeypatch.setattr(player_history, 'get_server_number', lambda: '1')
    start = 1_700_000_000
    player_history.save_start_player_session('fake-console-id', start, server_number=1)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == 'fake-console-id'))
        session.add(PlayerSession(player=player, start=datetime.fromtimestamp(start - 60, timezone.utc).replace(tzinfo=None),
                                  end=datetime.fromtimestamp(start - 30, timezone.utc).replace(tzinfo=None), server_number=1))
        session.commit()
    player_history.save_end_player_session('fake-console-id', start + 20)
    with Session(database) as session:
        saved = session.scalar(select(PlayerSession).where(PlayerSession.start_event_us == start * 1_000_000))
        assert saved.end_event_us == (start + 20) * 1_000_000
        assert session.scalar(select(PendingPlayerDisconnect)) is None


def test_ambiguous_legacy_connect_is_not_silently_duplicated(database, monkeypatch):
    monkeypatch.delenv("HLL_SESSION_LEGACY_UTC", raising=False)
    start = 1_700_000_000
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
        session.add(PlayerSession(player=player, start=datetime.fromtimestamp(start), server_number=1, server_name="legacy"))
        session.commit()
    player_history.save_start_player_session("fake-console-id", start, server_number=1)
    assert len(sessions(database)) == 1
    with Session(database) as session:
        assert len(session.scalars(select(PendingPlayerConnect)).all()) == 1


def test_unreviewed_legacy_connect_prevents_closing_an_older_known_session(database, monkeypatch):
    monkeypatch.delenv("HLL_SESSION_LEGACY_UTC", raising=False)
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    start = 1_700_000_000
    player_history.save_start_player_session("fake-console-id", start - 100, server_number=1)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
        session.add(PlayerSession(player=player, start=datetime.fromtimestamp(start), server_number=1, server_name="legacy"))
        session.commit()
    player_history.save_start_player_session("fake-console-id", start, server_number=1)
    player_history.save_end_player_session("fake-console-id", start + 50)
    with Session(database) as session:
        known = session.scalar(select(PlayerSession).where(PlayerSession.start_event_us.is_not(None)))
        assert known.end is None
        assert len(session.scalars(select(PendingPlayerConnect)).all()) == 1
        assert len(session.scalars(select(PendingPlayerDisconnect)).all()) == 1


def test_review_links_only_the_matching_server_player_and_legacy_session(database, monkeypatch):
    monkeypatch.delenv("HLL_SESSION_LEGACY_UTC", raising=False)
    start = 1_700_000_000
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
        legacy = PlayerSession(player=player, start=datetime.fromtimestamp(start), server_number=1, server_name="legacy")
        session.add(legacy)
        session.commit()
        legacy_id = legacy.id
    player_history.save_start_player_session("fake-console-id", start, server_number=1)
    result = session_event_review.list_pending(1)
    assert result["results"][0]["legacy_candidates"][0]["id"] == legacy_id
    assert session_event_review.list_pending(2)["results"] == []
    assert not session_event_review.resolve(2, "fake-console-id", "connect", start * 1_000_000,
                                            "link", "matched server logs", "Operator", session_id=legacy_id)
    with pytest.raises(ValueError):
        session_event_review.resolve(1, "fake-console-id", "connect", start * 1_000_000,
                                     "link", "matched server logs", "Operator", session_id=legacy_id + 999)
    assert session_event_review.resolve(1, "fake-console-id", "connect", start * 1_000_000,
                                        "link", "matched server logs", "Operator", session_id=legacy_id)
    assert not session_event_review.resolve(1, "fake-console-id", "connect", start * 1_000_000,
                                            "link", "matched server logs", "Operator", session_id=legacy_id)
    with Session(database) as session:
        assert session.get(PlayerSession, legacy_id).start_event_us == start * 1_000_000
        audit = session.scalar(select(SessionEventResolution))
        assert (audit.actor, audit.decision, audit.reason) == ("Operator", "link", "matched server logs")
        assert session.scalars(select(PendingPlayerConnect)).all() == []


def test_review_can_create_distinct_session_without_reinterpreting_legacy_data(database, monkeypatch):
    monkeypatch.delenv("HLL_SESSION_LEGACY_UTC", raising=False)
    start = 1_700_000_000
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
        session.add(PlayerSession(player=player, start=datetime.fromtimestamp(start), server_number=1, server_name="legacy"))
        session.commit()
    player_history.save_start_player_session("fake-console-id", start, server_number=1)
    assert session_event_review.resolve(1, "fake-console-id", "connect", start * 1_000_000,
                                        "create", "different event verified", "Operator", server_name="test")
    rows = sessions(database)
    assert len(rows) == 2
    assert rows[0].start_event_us is None and rows[1].start_event_us == start * 1_000_000


def test_linking_closed_legacy_session_does_not_reassign_an_unknown_end(database, monkeypatch):
    monkeypatch.delenv("HLL_SESSION_LEGACY_UTC", raising=False)
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    start = 1_700_000_000
    player_history.save_start_player_session("fake-console-id", start, server_number=1)
    player_history.save_end_player_session("fake-console-id", start + 150)
    with Session(database) as session:
        player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
        legacy = PlayerSession(player=player, start=datetime.fromtimestamp(start + 100),
            end=datetime.fromtimestamp(start + 140), server_number=1, server_name="legacy")
        session.add(legacy)
        session.commit()
        legacy_id = legacy.id
    player_history.save_start_player_session("fake-console-id", start + 100, server_number=1)
    assert session_event_review.resolve(1, "fake-console-id", "connect", (start + 100) * 1_000_000,
        "link", "start verified, end unknown", "Operator", session_id=legacy_id)
    with Session(database) as session:
        rows = session.scalars(select(PlayerSession).order_by(PlayerSession.id)).all()
        assert rows[0].end_event_us == (start + 150) * 1_000_000
        assert rows[1].end == datetime.fromtimestamp(start + 140) and rows[1].end_event_us is None
        assert len(session.scalars(select(PendingPlayerDisconnect)).all()) == 1


def test_review_discards_only_requested_unmatched_disconnect_and_records_reason(database, monkeypatch):
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    event = 1_700_000_050
    player_history.save_end_player_session("fake-console-id", event)
    with pytest.raises(ValueError):
        session_event_review.resolve(1, "fake-console-id", "disconnect", event * 1_000_000,
                                     "discard", "", "Operator")
    assert session_event_review.resolve(1, "fake-console-id", "disconnect", event * 1_000_000,
                                        "discard", "duplicate event checked", "Operator")
    # A refetched log must not undo the decision or close a later-found session.
    player_history.save_start_player_session("fake-console-id", event - 10, server_number=1)
    player_history.save_end_player_session("fake-console-id", event)
    with Session(database) as session:
        assert session.scalars(select(PendingPlayerDisconnect)).all() == []
        assert session.scalar(select(SessionEventResolution)).reason == "duplicate event checked"
        assert session.scalar(select(PlayerSession)).end is None


def test_discarded_connect_is_not_recreated_by_replay(database):
    event = 1_700_000_000
    player_history.save_start_player_session("new-fake-id", event, server_number=1)
    assert session_event_review.resolve(1, "new-fake-id", "connect", event * 1_000_000,
                                        "discard", "invalid event checked", "Operator")
    with Session(database) as session:
        session.add(PlayerID(player_id="new-fake-id"))
        session.commit()
    player_history.save_start_player_session("new-fake-id", event, server_number=1)
    player_history.save_start_player_session("new-fake-id", event, server_number=2)
    with Session(database) as session:
        assert session.scalars(select(PendingPlayerConnect)).all() == []
        assert [row.server_number for row in session.scalars(select(PlayerSession))] == [2]


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="process timezone control requires tzset")
def test_explicit_fixed_utc_setting_allows_active_legacy_session_to_close(database, monkeypatch):
    original_tz = os.environ.get("TZ")
    monkeypatch.setenv("TZ", "UTC")
    monkeypatch.setenv("HLL_SESSION_LEGACY_UTC", "true")
    monkeypatch.setattr(player_history, "get_server_number", lambda: "1")
    time.tzset()
    try:
        start, end = 1_700_000_000, 1_700_000_050
        with Session(database) as session:
            player = session.scalar(select(PlayerID).where(PlayerID.player_id == "fake-console-id"))
            session.add(PlayerSession(player=player, start=datetime.fromtimestamp(start), server_number=1, server_name="legacy"))
            session.commit()
        player_history.save_end_player_session("fake-console-id", end)
        saved = sessions(database)[0]
        assert (saved.start_event_us, saved.end_event_us) == (start * 1_000_000, end * 1_000_000)
    finally:
        if original_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original_tz
        time.tzset()
