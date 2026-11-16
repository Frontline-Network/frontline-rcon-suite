#!/usr/bin/env python3
"""Back up PostgreSQL and session journals under shared session-table locks."""
from __future__ import annotations

import argparse
import fcntl
import hashlib
import importlib.util
import json
import os
import re
import select
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

try:
    from session_event_backup import copy_snapshot
except ModuleNotFoundError as exc:
    if exc.name != "session_event_backup":
        raise
    # When run from a source checkout, the helper lives in the rcon package;
    # on the host both verified files are installed together.
    source = Path(__file__).resolve().parent.parent / "rcon" / "session_event_backup.py"
    spec = importlib.util.spec_from_file_location("session_event_backup", source)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    copy_snapshot = module.copy_snapshot


LOCK_SQL = """
BEGIN;
SET LOCAL lock_timeout = '5s';
DO $$
DECLARE name text;
BEGIN
  IF to_regclass('public.player_sessions') IS NULL THEN
    RAISE EXCEPTION 'Required player_sessions table is missing';
  END IF;
  FOREACH name IN ARRAY ARRAY['player_sessions', 'pending_player_connect',
    'pending_player_disconnect', 'session_event_resolution', 'unidentified_session_event']
  LOOP
    IF to_regclass('public.' || name) IS NOT NULL THEN
      EXECUTE format('LOCK TABLE public.%I IN SHARE MODE', name);
    END IF;
  END LOOP;
END $$;
SELECT 'SESSION_LOCKS_ACQUIRED|' || CASE WHEN to_regclass('public.unidentified_session_event') IS NULL THEN '0' ELSE '1' END;
"""


def command(container: str, program: str) -> list[str]:
    return ["docker", "exec", "-i", container, "sh", "-c", program]


def digest(path: Path) -> str:
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(chunk)
    return value.hexdigest()


def read_marker(process: subprocess.Popen, prefix: str) -> str:
    ready, _, _ = select.select([process.stdout], [], [], 20)
    line = process.stdout.readline().strip() if ready else ""
    if not line.startswith(prefix):
        raise RuntimeError(f"Could not establish {prefix}")
    return line[len(prefix):]


def close_psql(process: subprocess.Popen | None) -> None:
    if process is None:
        return
    if process.poll() is None:
        try:
            process.stdin.write("ROLLBACK;\n\\q\n")
            process.stdin.flush()
            process.wait(timeout=10)
        except (BrokenPipeError, subprocess.TimeoutExpired):
            process.kill()
            process.wait(timeout=10)
    for stream in (process.stdin, process.stdout, process.stderr):
        if stream:
            stream.close()


def run_backup(container: str, journal_dir: Path, destination: Path) -> Path:
    os.umask(0o077)
    destination.mkdir(mode=0o700, parents=True, exist_ok=True)
    if shutil.disk_usage(destination).free < 10 * 1024**3:
        raise RuntimeError("Less than 10 GiB free at the backup destination")
    with (destination / ".backup.lock").open("a+") as lock:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        now = datetime.now(timezone.utc)
        run_dir = destination / now.strftime("%Y%m%dT%H%M%S.%fZ")
        run_dir.mkdir(mode=0o700)
        (run_dir / "INCOMPLETE").write_text("Backup not yet verified\n", encoding="utf-8")
        lock_cmd = command(container, 'exec psql -X -qAt -v ON_ERROR_STOP=1 -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}"')
        process = subprocess.Popen(lock_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, text=True, bufsize=1)
        exporter = None
        try:
            process.stdin.write(LOCK_SQL)
            process.stdin.flush()
            marker = read_marker(process, "SESSION_LOCKS_ACQUIRED|")
            if marker not in {"0", "1"}:
                raise RuntimeError("Could not acquire the session-table locks")
            exporter = subprocess.Popen(lock_cmd, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                                        stderr=subprocess.PIPE, text=True, bufsize=1)
            exporter.stdin.write("BEGIN ISOLATION LEVEL REPEATABLE READ READ ONLY;\nSELECT 'EXPORTED_SNAPSHOT|' || pg_export_snapshot();\n")
            exporter.stdin.flush()
            snapshot_id = read_marker(exporter, "EXPORTED_SNAPSHOT|")
            if not re.fullmatch(r"[0-9A-Fa-f-]+", snapshot_id):
                raise RuntimeError("Invalid exported snapshot identifier")
            snapshot_started = datetime.now(timezone.utc).isoformat()
            journal_names = []
            if journal_dir.exists():
                if not journal_dir.is_dir() or journal_dir.is_symlink():
                    raise ValueError("Journal directory must be a real directory")
                for journal in sorted(journal_dir.glob("server-*.sqlite3")):
                    if journal.is_symlink() or not journal.is_file():
                        raise ValueError("Journal must be a regular file")
                    target = run_dir / journal.name
                    copy_snapshot(journal, target)
                    journal_names.append(target.name)
            if marker == "1" and "server-3.sqlite3" not in journal_names:
                raise RuntimeError("Session schema is present but the RCON3 journal is missing")
            if process.poll() is not None or exporter.poll() is not None:
                raise RuntimeError("Session-table lock connection ended during the snapshot")
            snapshot_finished = datetime.now(timezone.utc).isoformat()
            # Keep the exported MVCC snapshot alive, but release write locks
            # before the potentially long pg_dump and verification phases.
            close_psql(process)
            process = None
            dump = run_dir / "postgres.dump"
            dump_cmd = command(container, 'exec pg_dump -U "${POSTGRES_USER:-postgres}" -d "${POSTGRES_DB:-postgres}" -Fc --snapshot=' + snapshot_id)
            with dump.open("xb") as output:
                subprocess.run(dump_cmd, stdout=output, check=True, timeout=7200)
                output.flush()
                os.fsync(output.fileno())
            if exporter.poll() is not None:
                raise RuntimeError("Exported snapshot connection ended during the dump")
        finally:
            close_psql(process)
            close_psql(exporter)
        restore_cmd = ["docker", "exec", "-i", container, "pg_restore", "-f", "/dev/null"]
        with dump.open("rb") as stream:
            subprocess.run(restore_cmd, stdin=stream, check=True, timeout=7200)
        files = [dump.name, *journal_names]
        manifest = {"created_utc": now.isoformat(), "snapshot_started_utc": snapshot_started,
                    "snapshot_finished_utc": snapshot_finished, "postgres_container": container,
                    "journals": journal_names, "sha256": {name: digest(run_dir / name) for name in files}}
        manifest_path = run_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
        with manifest_path.open("rb") as stream:
            os.fsync(stream.fileno())
        (run_dir / "INCOMPLETE").unlink()
        dir_fd = os.open(str(run_dir), os.O_RDONLY | getattr(os, "O_DIRECTORY", 0))
        try:
            os.fsync(dir_fd)
        finally:
            os.close(dir_fd)
        return run_dir


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--postgres-container", required=True)
    parser.add_argument("--journal-dir", required=True, type=Path)
    parser.add_argument("--destination", required=True, type=Path)
    args = parser.parse_args()
    try:
        result = run_backup(args.postgres_container, args.journal_dir, args.destination)
    except Exception as exc:
        print(f"RCON backup failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        raise SystemExit(1) from exc
    print(f"Verified RCON backup: {result}")


if __name__ == "__main__":
    main()
