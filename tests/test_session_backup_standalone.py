"""The backup helper can snapshot a valid journal without the session rollout."""
import sqlite3

import pytest

from rcon.session_event_backup import copy_snapshot


def test_verified_snapshot_retains_rows_and_never_overwrites(tmp_path):
    source, target = tmp_path / "source.sqlite", tmp_path / "backup.sqlite"
    with sqlite3.connect(source) as db:
        db.execute("CREATE TABLE journal_metadata (key TEXT, value INTEGER)")
        db.execute("CREATE TABLE session_events (player TEXT)")
        db.execute("CREATE TABLE unidentified_session_events (raw TEXT)")
        db.execute("INSERT INTO session_events VALUES ('synthetic-player')")
    copy_snapshot(source, target)
    with sqlite3.connect(target) as db:
        assert db.execute("SELECT player FROM session_events").fetchall() == [("synthetic-player",)]
        assert db.execute("PRAGMA integrity_check").fetchone() == ("ok",)
    before = target.read_bytes()
    with pytest.raises(FileExistsError):
        copy_snapshot(source, target)
    assert target.read_bytes() == before


def test_invalid_database_is_not_published_as_backup(tmp_path):
    source, target = tmp_path / "invalid.sqlite", tmp_path / "backup.sqlite"
    source.write_bytes(b"not a sqlite database")
    with pytest.raises(sqlite3.DatabaseError):
        copy_snapshot(source, target)
    assert not target.exists()
