"""Create a verified SQLite snapshot without overwriting an existing file.

This only makes the journal internally consistent. A coordinated application
backup must also quiesce all session writers and include PostgreSQL.
"""
from __future__ import annotations

import argparse
import os
import sqlite3
import tempfile
from contextlib import closing
from pathlib import Path


def copy_snapshot(source: str | Path, destination: str | Path) -> None:
    source_path = Path(source).resolve(strict=True)
    destination = Path(destination)
    target = destination.parent.resolve(strict=True) / destination.name
    if not destination.name or target.exists() or target.is_symlink():
        raise FileExistsError("Snapshot destination must not already exist")
    temp_fd, temp_name = tempfile.mkstemp(prefix=".session-snapshot-", dir=target.parent)
    temp_path = Path(temp_name)
    try:
        if hasattr(os, "fchmod"):
            os.fchmod(temp_fd, 0o600)
        os.close(temp_fd)
        temp_fd = -1
        with closing(sqlite3.connect(source_path.as_uri() + "?mode=ro", uri=True, timeout=10)) as original:
            with closing(sqlite3.connect(temp_path, timeout=10)) as snapshot:
                original.backup(snapshot)
                if snapshot.execute("PRAGMA integrity_check").fetchall() != [("ok",)]:
                    raise ValueError("Journal integrity check failed")
                tables = {row[0] for row in snapshot.execute("SELECT name FROM sqlite_master WHERE type='table'")}
                if not {"journal_metadata", "session_events", "unidentified_session_events"} <= tables:
                    raise ValueError("Snapshot is not a complete session journal")
        with temp_path.open("rb") as verified:
            os.fsync(verified.fileno())
        # Both paths are in the same directory. The hard link creates the final
        # name atomically and fails if another process created it meanwhile.
        os.link(temp_path, target)
        if os.name == "posix":
            directory_fd = os.open(str(target.parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
    finally:
        if temp_fd >= 0:
            os.close(temp_fd)
        temp_path.unlink(missing_ok=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", help="Existing journal or verified journal snapshot")
    parser.add_argument("destination", help="New snapshot or restoration path; must not exist")
    args = parser.parse_args()
    copy_snapshot(args.source, args.destination)
    print("Verified session journal snapshot created")


if __name__ == "__main__":
    main()
