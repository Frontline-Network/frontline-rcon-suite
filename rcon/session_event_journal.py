"""Local crash-recoverable inbox for session-only log processing.

This journal must live on a persistent, private filesystem. It deliberately
does not invoke general log hooks, which may have external side effects.
"""
from __future__ import annotations

import os
import sqlite3
import stat
import time
from contextlib import contextmanager
from pathlib import Path
from typing import Callable


class SessionEventJournal:
    def __init__(self, path: str | Path):
        self.path = str(path)
        flags = os.O_RDWR | os.O_CREAT | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags, 0o600)
        try:
            if not stat.S_ISREG(os.fstat(fd).st_mode):
                raise ValueError("Session journal must be a regular file")
            if hasattr(os, "fchmod"):
                os.fchmod(fd, 0o600)
        finally:
            os.close(fd)
        with self._connect() as db:
            db.execute("BEGIN IMMEDIATE")
            db.execute("""CREATE TABLE IF NOT EXISTS session_events (
                server INTEGER NOT NULL, player TEXT NOT NULL,
                kind TEXT NOT NULL CHECK (kind IN ('connect', 'disconnect')),
                event_us INTEGER NOT NULL, completed_at INTEGER, last_attempt_ns INTEGER,
                PRIMARY KEY (server, player, kind, event_us)
            )""")
            db.execute("CREATE TABLE IF NOT EXISTS journal_metadata (key TEXT PRIMARY KEY, value INTEGER NOT NULL)")
            db.execute("""CREATE TABLE IF NOT EXISTS unidentified_session_events (
                server INTEGER NOT NULL, kind TEXT NOT NULL,
                event_us INTEGER NOT NULL, player_name TEXT NOT NULL,
                raw TEXT NOT NULL, resolved_at INTEGER, resolved_by TEXT, resolution_reason TEXT, published_at INTEGER,
                PRIMARY KEY (server, kind, event_us, player_name, raw)
            )""")
            columns = {row[1] for row in db.execute("PRAGMA table_info(unidentified_session_events)")}
            for name, column_type in (("resolved_at", "INTEGER"), ("resolved_by", "TEXT"),
                                      ("resolution_reason", "TEXT"), ("published_at", "INTEGER")):
                if name not in columns:
                    db.execute(f"ALTER TABLE unidentified_session_events ADD COLUMN {name} {column_type}")
        if os.name == "posix":
            directory = os.open(str(Path(self.path).parent), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
            try:
                os.fsync(directory)
            finally:
                os.close(directory)

    @contextmanager
    def _connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        # Commit must reach the backing volume before the log can be marked
        # processed elsewhere. Redis snapshots do not provide that guarantee.
        try:
            db.execute("PRAGMA synchronous=FULL")
            with db:
                yield db
        finally:
            db.close()

    def remember(self, server: int, player: str, kind: str, event_us: int):
        if server < 1 or not player or kind not in ("connect", "disconnect") or event_us < 0:
            raise ValueError("Invalid session event")
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO session_events (server, player, kind, event_us) VALUES (?, ?, ?, ?)",
                       (server, player, kind, event_us))

    def cutover_us(self, now_us: int) -> int:
        """Keep the first activation time across subsequent process restarts."""
        if now_us < 0:
            raise ValueError("Invalid cutover time")
        with self._connect() as db:
            db.execute("INSERT OR IGNORE INTO journal_metadata (key, value) VALUES ('cutover_us', ?)", (now_us,))
            return db.execute("SELECT value FROM journal_metadata WHERE key = 'cutover_us'").fetchone()[0]

    def remember_batch(self, events: list[tuple[int, str, str, int]], cutover_us: int,
                       unidentified: list[tuple[int, str, int, str, str]] | None = None) -> int:
        """Atomically retain eligible events before dispatching their log batch."""
        for server, player, kind, event_us in events:
            if server < 1 or not player or kind not in ("connect", "disconnect") or event_us < 0:
                raise ValueError("Invalid session event")
        unidentified = unidentified or []
        for server, kind, event_us, name, raw in unidentified:
            if (server < 1 or kind not in ("connect", "disconnect") or event_us < 0
                    or not isinstance(name, str) or not isinstance(raw, str)):
                raise ValueError("Invalid unidentified session event")
        eligible = [event for event in events if event[3] >= cutover_us]
        eligible_unidentified = [event for event in unidentified if event[2] >= cutover_us]
        with self._connect() as db:
            before = db.total_changes
            db.executemany("INSERT OR IGNORE INTO session_events (server, player, kind, event_us) VALUES (?, ?, ?, ?)", eligible)
            db.executemany("INSERT OR IGNORE INTO unidentified_session_events "
                           "(server, kind, event_us, player_name, raw) VALUES (?, ?, ?, ?, ?)", eligible_unidentified)
            return db.total_changes - before

    def list_unidentified(self, server: int, limit: int = 100):
        if server < 1 or not 1 <= limit <= 1000:
            raise ValueError("Invalid server or limit")
        with self._connect() as db:
            return db.execute("SELECT kind, event_us, player_name, raw FROM unidentified_session_events "
                              "WHERE server = ? AND resolved_at IS NULL ORDER BY event_us, kind, player_name LIMIT ?",
                              (server, limit)).fetchall()

    def discard_unidentified(self, server: int, event_id: int, actor: str, reason: str) -> bool:
        """Record an explicit decision without guessing a player identity."""
        if (server < 1 or event_id < 1 or not actor or not actor.strip() or len(actor) > 150
                or not reason or not reason.strip() or len(reason) > 1000):
            raise ValueError("A valid server, event, operator and reason are required")
        with self._connect() as db:
            result = db.execute("UPDATE unidentified_session_events SET resolved_at = ?, resolved_by = ?, "
                                "resolution_reason = ? WHERE rowid = ? AND server = ? AND resolved_at IS NULL AND published_at IS NULL",
                                (int(time.time()), actor.strip(), reason.strip(), event_id, server))
            return result.rowcount == 1

    def publish_unidentified(self, handler: Callable[[int, str, int, str, str], None], limit: int = 100) -> int:
        """Transfer unresolved anonymous events to the shared review store."""
        if limit < 1:
            raise ValueError("Invalid batch limit")
        processed = 0
        for _ in range(limit):
            with self._connect() as db:
                # Serialize local reviews with transfer. If PostgreSQL commits
                # but this transaction rolls back, its idempotent handler is
                # called again on the next pass.
                db.execute("BEGIN IMMEDIATE")
                row = db.execute("SELECT rowid, server, kind, event_us, player_name, raw "
                                 "FROM unidentified_session_events WHERE published_at IS NULL AND resolved_at IS NULL "
                                 "ORDER BY event_us, rowid LIMIT 1").fetchone()
                if row is None:
                    break
                row_id, server, kind, event_us, name, raw = row
                handler(server, kind, event_us, name, raw)
                db.execute("UPDATE unidentified_session_events SET published_at = ? WHERE rowid = ?",
                           (int(time.time()), row_id))
            processed += 1
        return processed

    def drain(self, handler: Callable[[int, str, str, int], None], limit: int = 100,
              retry_delay_seconds: int = 30) -> int:
        if limit < 1 or retry_delay_seconds < 0:
            raise ValueError("Invalid batch limit or retry delay")
        retry_before = time.time_ns() - retry_delay_seconds * 1_000_000_000
        with self._connect() as db:
            events = db.execute("SELECT server, player, kind, event_us FROM session_events "
                                "WHERE completed_at IS NULL AND (last_attempt_ns IS NULL OR last_attempt_ns <= ?) "
                                "ORDER BY last_attempt_ns NULLS FIRST, event_us, server, player, kind LIMIT ?",
                                (retry_before, limit)).fetchall()
        processed = 0
        for event in events:
            # If the handler raises, leave this and all subsequent entries for
            # retry. If the process dies after the handler commits but before
            # this acknowledgement, the handler must be idempotent.
            if handler(*event) is False:
                # A missing identity may become available later. Do not block
                # unrelated players, and keep this event pending for retry.
                with self._connect() as db:
                    db.execute("UPDATE session_events SET last_attempt_ns = ? WHERE server = ? AND player = ? "
                               "AND kind = ? AND event_us = ? AND completed_at IS NULL", (time.time_ns(), *event))
                continue
            with self._connect() as db:
                db.execute("UPDATE session_events SET completed_at = ? WHERE server = ? AND player = ? "
                           "AND kind = ? AND event_us = ? AND completed_at IS NULL",
                           (int(time.time()), *event))
            processed += 1
        return processed

    def prune_completed(self, before: int) -> int:
        with self._connect() as db:
            return db.execute("DELETE FROM session_events WHERE completed_at IS NOT NULL AND completed_at < ?",
                              (before,)).rowcount
