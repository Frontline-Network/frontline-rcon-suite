import pytest
from concurrent.futures import ThreadPoolExecutor
import os
import sqlite3
import stat

from rcon.session_event_journal import SessionEventJournal
from rcon.session_event_journal_cli import inspect_unidentified


def test_unacknowledged_event_survives_restart_and_handler_failure(tmp_path):
    path = tmp_path / "events.sqlite"
    journal = SessionEventJournal(path)
    journal.remember(3, "console-1", "disconnect", 123000)
    journal.remember(3, "console-1", "disconnect", 123000)

    def fail(*event):
        raise RuntimeError("database unavailable")

    with pytest.raises(RuntimeError):
        journal.drain(fail)
    received = []
    recovered = SessionEventJournal(path)
    assert recovered.drain(lambda *event: received.append(event)) == 1
    assert received == [(3, "console-1", "disconnect", 123000)]
    recovered.remember(3, "console-1", "disconnect", 123000)
    assert recovered.drain(lambda *event: received.append(event)) == 0


def test_acknowledgement_failure_replays_only_session_handler(tmp_path, monkeypatch):
    journal = SessionEventJournal(tmp_path / "events.sqlite")
    journal.remember(3, "console-1", "connect", 123000)
    seen = []

    def interrupted(*event):
        seen.append(event)
        raise RuntimeError("process interrupted before acknowledgement")

    with pytest.raises(RuntimeError):
        journal.drain(interrupted)
    assert journal.drain(lambda *event: seen.append(event)) == 1
    assert seen == [(3, "console-1", "connect", 123000)] * 2


def test_pruning_never_removes_pending_events(tmp_path):
    journal = SessionEventJournal(tmp_path / "events.sqlite")
    journal.remember(3, "console-1", "connect", 1000)
    journal.remember(3, "console-1", "disconnect", 2000)
    assert journal.drain(lambda *event: None, limit=1) == 1
    assert journal.prune_completed(2**40) == 1
    remaining = []
    assert journal.drain(lambda *event: remaining.append(event)) == 1
    assert remaining == [(3, "console-1", "disconnect", 2000)]


def test_cutover_persists_and_batch_is_atomic_and_idempotent(tmp_path):
    path = tmp_path / "events.sqlite"
    journal = SessionEventJournal(path)
    assert journal.cutover_us(2000) == 2000
    assert SessionEventJournal(path).cutover_us(9000) == 2000
    with pytest.raises(ValueError):
        journal.remember_batch([(3, "console-1", "connect", 2000), (3, "", "connect", 3000)], 2000)
    events = [(3, "console-1", "connect", 1000), (3, "console-1", "connect", 2000)]
    assert journal.remember_batch(events, 2000) == 1
    assert journal.remember_batch(events, 2000) == 0
    received = []
    assert journal.drain(lambda *event: received.append(event)) == 1
    assert received == [events[1]]


def test_deferred_identity_does_not_block_other_players(tmp_path):
    journal = SessionEventJournal(tmp_path / "events.sqlite")
    journal.remember_batch([(3, "missing", "connect", 1000), (3, "ready", "connect", 2000)], 0)
    received = []

    def handle(server, player, kind, event_us):
        if player == "missing":
            return False
        received.append(player)

    assert journal.drain(handle) == 1
    assert received == ["ready"]
    assert journal.drain(lambda *event: received.append(event[1]), retry_delay_seconds=0) == 1
    assert received == ["ready", "missing"]


def test_more_deferred_events_than_batch_limit_do_not_starve_later_events(tmp_path):
    journal = SessionEventJournal(tmp_path / "events.sqlite")
    journal.remember_batch([(3, f"missing-{i}", "connect", i) for i in range(100)] +
                           [(3, "ready", "connect", 100)], 0)
    received = []

    def handle(server, player, kind, event_us):
        if player != "ready":
            return False
        received.append(player)

    assert journal.drain(handle) == 0
    assert journal.drain(handle) == 1
    assert received == ["ready"]


def test_deferred_identity_is_retried_after_cooldown(tmp_path, monkeypatch):
    journal = SessionEventJournal(tmp_path / "events.sqlite")
    journal.remember(3, "missing", "connect", 1000)
    now_ns = [100_000_000_000]
    monkeypatch.setattr("rcon.session_event_journal.time.time_ns", lambda: now_ns[0])
    attempts = []

    def defer(*event):
        attempts.append(event)
        return False

    assert journal.drain(defer) == 0
    assert journal.drain(defer) == 0
    assert len(attempts) == 1
    now_ns[0] += 30_000_000_000
    assert journal.drain(defer) == 0
    assert len(attempts) == 2


def test_unidentified_events_are_retained_without_guessing_player_identity(tmp_path):
    path = tmp_path / "events.sqlite"
    journal = SessionEventJournal(path)
    unknown = [(3, "disconnect", 2000, "same-name", "DISCONNECTED same-name ()"),
               (3, "disconnect", 3000, "", "DISCONNECTED ()")]
    assert journal.remember_batch([], 1000, unknown) == 2
    assert journal.remember_batch([], 1000, unknown) == 0
    recovered = SessionEventJournal(path)
    assert recovered.list_unidentified(3) == [(kind, event, name, raw) for _, kind, event, name, raw in unknown]
    assert recovered.list_unidentified(4) == []
    assert recovered.drain(lambda *event: pytest.fail("unidentified event must not modify a session")) == 0
    result = inspect_unidentified(str(path), 3)
    assert [item["raw"] for item in result] == [row[4] for row in unknown]
    assert result[0]["event_time"] == "1970-01-01T00:00:00.002000+00:00"
    assert inspect_unidentified(str(path), 4) == []


def test_read_only_inspection_does_not_create_a_missing_journal(tmp_path):
    path = tmp_path / "missing.sqlite"
    with pytest.raises(FileNotFoundError):
        inspect_unidentified(str(path), 3)
    assert not path.exists()


def test_concurrent_writers_keep_one_copy_and_journal_is_private(tmp_path):
    path = tmp_path / "events.sqlite"
    journal = SessionEventJournal(path)
    event = (3, "console-1", "connect", 2000)
    with ThreadPoolExecutor(max_workers=8) as pool:
        results = list(pool.map(lambda _: journal.remember_batch([event], 1000), range(32)))
    assert sum(results) == 1
    received = []
    assert journal.drain(lambda *value: received.append(value)) == 1
    assert received == [event]
    if os.name == "posix":
        assert stat.S_IMODE(path.stat().st_mode) == 0o600


def test_unidentified_review_is_server_scoped_audited_and_survives_replay(tmp_path):
    path = tmp_path / "events.sqlite"
    journal = SessionEventJournal(path)
    event = (3, "disconnect", 2000, "", "DISCONNECTED ()")
    journal.remember_batch([], 1000, [event])
    event_id = inspect_unidentified(str(path), 3)[0]["id"]
    with pytest.raises(ValueError):
        journal.discard_unidentified(3, event_id, "Operator", " ")
    assert not journal.discard_unidentified(4, event_id, "Operator", "not our server")
    assert journal.discard_unidentified(3, event_id, " Operator ", " verified anonymous event ")
    assert not journal.discard_unidentified(3, event_id, "Operator", "second decision")
    journal.remember_batch([], 1000, [event])
    assert inspect_unidentified(str(path), 3) == []
    audit = inspect_unidentified(str(path), 3, include_resolved=True)[0]
    assert (audit["resolved_by"], audit["resolution_reason"]) == ("Operator", "verified anonymous event")
    assert audit["resolved_at"] is not None


def test_existing_unidentified_rows_survive_audit_schema_upgrade(tmp_path):
    path = tmp_path / "old.sqlite"
    with sqlite3.connect(path) as db:
        db.execute("CREATE TABLE unidentified_session_events (server INTEGER NOT NULL, kind TEXT NOT NULL, "
                   "event_us INTEGER NOT NULL, player_name TEXT NOT NULL, raw TEXT NOT NULL, "
                   "PRIMARY KEY (server, kind, event_us, player_name, raw))")
        db.execute("INSERT INTO unidentified_session_events VALUES (3, 'disconnect', 2000, '', 'DISCONNECTED ()')")
    SessionEventJournal(path)
    assert inspect_unidentified(str(path), 3)[0]["raw"] == "DISCONNECTED ()"
