import sqlite3
from concurrent.futures import ThreadPoolExecutor

import pytest

from rcon.session_event_backup import copy_snapshot
from rcon.session_event_journal import SessionEventJournal
from rcon.session_event_journal_cli import inspect_unidentified


def test_snapshot_and_restore_preserve_pending_cutover_and_audit(tmp_path):
    source, backup, restored = (tmp_path / name for name in ("source.sqlite", "backup.sqlite", "restored.sqlite"))
    journal = SessionEventJournal(source)
    journal.cutover_us(1000)
    journal.remember_batch([(3, "console-1", "connect", 2000)], 1000,
                           [(3, "disconnect", 3000, "", "DISCONNECTED ()")])
    event_id = inspect_unidentified(str(source), 3)[0]["id"]
    assert journal.discard_unidentified(3, event_id, "operator", "reviewed")
    copy_snapshot(source, backup)
    copy_snapshot(backup, restored)
    recovered = SessionEventJournal(restored)
    assert recovered.cutover_us(9999) == 1000
    received = []
    assert recovered.drain(lambda *event: received.append(event)) == 1
    assert received == [(3, "console-1", "connect", 2000)]
    assert inspect_unidentified(str(restored), 3, include_resolved=True)[0]["resolution_reason"] == "reviewed"


def test_snapshot_does_not_replace_existing_files_or_accept_wrong_database(tmp_path):
    journal = SessionEventJournal(tmp_path / "source.sqlite")
    destination = tmp_path / "existing.sqlite"
    destination.write_bytes(b"existing data")
    with pytest.raises(FileExistsError):
        copy_snapshot(journal.path, destination)
    assert destination.read_bytes() == b"existing data"
    wrong = tmp_path / "wrong.sqlite"
    with sqlite3.connect(wrong) as db:
        db.execute("CREATE TABLE unrelated (id INTEGER)")
    with pytest.raises(ValueError):
        copy_snapshot(wrong, tmp_path / "invalid-copy.sqlite")
    assert not (tmp_path / "invalid-copy.sqlite").exists()
    corrupt = tmp_path / "corrupt.sqlite"
    corrupt.write_bytes(b"not a sqlite database")
    with pytest.raises(sqlite3.DatabaseError):
        copy_snapshot(corrupt, tmp_path / "corrupt-copy.sqlite")
    assert not (tmp_path / "corrupt-copy.sqlite").exists()
    assert not list(tmp_path.glob(".session-snapshot-*"))


def test_snapshot_is_consistent_during_concurrent_writes(tmp_path):
    journal = SessionEventJournal(tmp_path / "source.sqlite")
    journal.cutover_us(1000)

    def write_events():
        for event in range(100):
            journal.remember(3, f"console-{event}", "connect", event + 1000)

    with ThreadPoolExecutor(max_workers=2) as executor:
        task = executor.submit(write_events)
        copy_snapshot(journal.path, tmp_path / "backup.sqlite")
        task.result()
    with sqlite3.connect(tmp_path / "backup.sqlite") as db:
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
        assert db.execute("SELECT value FROM journal_metadata WHERE key='cutover_us'").fetchone() == (1000,)
        assert 0 <= db.execute("SELECT count(*) FROM session_events").fetchone()[0] <= 100
