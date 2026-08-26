#!/usr/bin/env python3
"""Build a read-only retention plan for CRCON deployment backups.

The planner never removes or moves files.  It exists so operators can review a
deterministic Grandfather-Father-Son style selection before any destructive
maintenance is implemented or approved.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable


@dataclass(frozen=True)
class Backup:
    path: Path
    size_bytes: int
    modified_at: datetime
    has_checksum: bool


@dataclass(frozen=True)
class PlanEntry:
    path: str
    size_bytes: int
    modified_at: str
    decision: str
    reasons: tuple[str, ...]
    has_checksum: bool


@dataclass(frozen=True)
class UnmanagedEntry:
    path: str
    size_bytes: int
    kind: str


@dataclass(frozen=True)
class RetentionPlan:
    backup_dir: str
    total_count: int
    total_bytes: int
    keep_count: int
    keep_bytes: int
    candidate_count: int
    candidate_bytes: int
    missing_checksum_count: int
    checksum_count: int
    checksum_bytes: int
    unmanaged_count: int
    unmanaged_bytes: int
    observed_bytes: int
    entries: tuple[PlanEntry, ...]
    unmanaged_entries: tuple[UnmanagedEntry, ...]


def _utc_datetime(timestamp: float) -> datetime:
    return datetime.fromtimestamp(timestamp, tz=timezone.utc)


def load_backups(backup_dir: Path) -> list[Backup]:
    resolved = backup_dir.resolve(strict=True)
    if not resolved.is_dir():
        raise ValueError(f"Backup path is not a directory: {resolved}")

    backups = []
    for path in resolved.glob("postgres-*.dump"):
        if path.is_symlink() or not path.is_file():
            continue
        stat = path.stat()
        checksum_path = path.with_name(path.name + ".sha256")
        backups.append(
            Backup(
                path=path.resolve(),
                size_bytes=stat.st_size,
                modified_at=_utc_datetime(stat.st_mtime),
                has_checksum=(
                    checksum_path.is_file() and not checksum_path.is_symlink()
                ),
            )
        )
    return sorted(backups, key=lambda backup: backup.modified_at, reverse=True)


def _entry_size(path: Path) -> int:
    if path.is_symlink():
        return path.lstat().st_size
    if path.is_file():
        return path.stat().st_size
    if not path.is_dir():
        return 0

    total = 0
    for root, directories, files in os.walk(path, followlinks=False):
        root_path = Path(root)
        directories[:] = [
            name for name in directories if not (root_path / name).is_symlink()
        ]
        for name in files:
            file_path = root_path / name
            try:
                total += (
                    file_path.lstat().st_size
                    if file_path.is_symlink()
                    else file_path.stat().st_size
                )
            except FileNotFoundError:
                # A concurrently completed deployment may move a temporary
                # artifact between directory enumeration and stat().
                continue
    return total


def load_unmanaged_entries(
    backup_dir: Path, backups: Iterable[Backup]
) -> tuple[tuple[UnmanagedEntry, ...], int, int]:
    backup_root = backup_dir.resolve(strict=True)
    managed_paths = {backup.path for backup in backups}
    checksum_paths = {
        backup.path.with_name(backup.path.name + ".sha256")
        for backup in backups
        if backup.has_checksum
    }
    checksum_bytes = sum(path.stat().st_size for path in checksum_paths)

    unmanaged = []
    for path in backup_root.iterdir():
        resolved = path.resolve(strict=False)
        if resolved in managed_paths or resolved in checksum_paths:
            continue
        kind = (
            "symlink"
            if path.is_symlink()
            else "directory" if path.is_dir() else "file"
        )
        unmanaged.append(
            UnmanagedEntry(
                path=str(path.absolute()),
                size_bytes=_entry_size(path),
                kind=kind,
            )
        )

    entries = tuple(sorted(unmanaged, key=lambda entry: entry.path))
    return entries, len(checksum_paths), checksum_bytes


def load_state_references(state_dir: Path, backup_dir: Path) -> set[Path]:
    if not state_dir.exists():
        return set()

    backup_root = backup_dir.resolve(strict=True)
    references: set[Path] = set()
    for state_file in state_dir.glob("*.env"):
        if not state_file.is_file():
            continue
        for line in state_file.read_text(encoding="utf-8").splitlines():
            if not line.startswith("DATABASE_BACKUP="):
                continue
            value = line.split("=", 1)[1].strip()
            if not value:
                continue
            candidate = Path(value)
            if not candidate.is_absolute():
                candidate = backup_root.parent / candidate
            try:
                resolved = candidate.resolve(strict=False)
                resolved.relative_to(backup_root)
            except ValueError:
                continue
            references.add(resolved)
    return references


def _take_first_per_period(
    backups: Iterable[Backup], period_limit: int, period_key
) -> set[Path]:
    if period_limit == 0:
        return set()

    selected: set[Path] = set()
    seen_periods: set[object] = set()
    for backup in backups:
        key = period_key(backup.modified_at)
        if key in seen_periods:
            continue
        seen_periods.add(key)
        selected.add(backup.path)
        if len(seen_periods) >= period_limit:
            break
    return selected


def build_retention_plan(
    backup_dir: Path,
    state_dir: Path,
    *,
    keep_latest: int,
    keep_weekly: int,
    keep_monthly: int,
) -> RetentionPlan:
    for label, value in (
        ("keep_latest", keep_latest),
        ("keep_weekly", keep_weekly),
        ("keep_monthly", keep_monthly),
    ):
        if value < 0:
            raise ValueError(f"{label} must not be negative")

    backups = load_backups(backup_dir)
    unmanaged_entries, checksum_count, checksum_bytes = load_unmanaged_entries(
        backup_dir, backups
    )
    references = load_state_references(state_dir, backup_dir)
    reasons: dict[Path, set[str]] = {backup.path: set() for backup in backups}

    for backup in backups[:keep_latest]:
        reasons[backup.path].add("latest")

    weekly = _take_first_per_period(
        backups,
        keep_weekly,
        lambda value: value.isocalendar()[:2],
    )
    for path in weekly:
        reasons[path].add("weekly")

    monthly = _take_first_per_period(
        backups,
        keep_monthly,
        lambda value: (value.year, value.month),
    )
    for path in monthly:
        reasons[path].add("monthly")

    for backup in backups:
        if backup.path in references:
            reasons[backup.path].add("deployment-state")

    entries = tuple(
        PlanEntry(
            path=str(backup.path),
            size_bytes=backup.size_bytes,
            modified_at=backup.modified_at.isoformat(),
            decision="keep" if reasons[backup.path] else "candidate",
            reasons=tuple(sorted(reasons[backup.path])),
            has_checksum=backup.has_checksum,
        )
        for backup in backups
    )
    keep_entries = [entry for entry in entries if entry.decision == "keep"]
    candidate_entries = [entry for entry in entries if entry.decision == "candidate"]
    return RetentionPlan(
        backup_dir=str(backup_dir.resolve()),
        total_count=len(entries),
        total_bytes=sum(entry.size_bytes for entry in entries),
        keep_count=len(keep_entries),
        keep_bytes=sum(entry.size_bytes for entry in keep_entries),
        candidate_count=len(candidate_entries),
        candidate_bytes=sum(entry.size_bytes for entry in candidate_entries),
        missing_checksum_count=sum(not entry.has_checksum for entry in entries),
        checksum_count=checksum_count,
        checksum_bytes=checksum_bytes,
        unmanaged_count=len(unmanaged_entries),
        unmanaged_bytes=sum(entry.size_bytes for entry in unmanaged_entries),
        observed_bytes=(
            sum(entry.size_bytes for entry in entries)
            + checksum_bytes
            + sum(entry.size_bytes for entry in unmanaged_entries)
        ),
        entries=entries,
        unmanaged_entries=unmanaged_entries,
    )


def _human_bytes(value: int) -> str:
    units = ("B", "KiB", "MiB", "GiB", "TiB")
    amount = float(value)
    for unit in units:
        if amount < 1024 or unit == units[-1]:
            return f"{amount:.2f} {unit}"
        amount /= 1024
    raise AssertionError("unreachable")


def _print_text(plan: RetentionPlan) -> None:
    print("READ-ONLY STORAGE PLAN — no files are changed")
    print(f"Backup directory: {plan.backup_dir}")
    print(
        f"Managed database dumps: {plan.total_count} / "
        f"{_human_bytes(plan.total_bytes)}"
    )
    print(f"Keep: {plan.keep_count} backups / {_human_bytes(plan.keep_bytes)}")
    print(
        f"Candidates: {plan.candidate_count} backups / "
        f"{_human_bytes(plan.candidate_bytes)}"
    )
    print(f"Missing checksum sidecars: {plan.missing_checksum_count}")
    print(
        f"Unmanaged (never candidates): {plan.unmanaged_count} entries / "
        f"{_human_bytes(plan.unmanaged_bytes)}"
    )
    print(f"Observed storage: {_human_bytes(plan.observed_bytes)}")
    for entry in plan.entries:
        reasons = ",".join(entry.reasons) if entry.reasons else "not-selected"
        print(
            f"{entry.decision.upper()}|{entry.modified_at}|{entry.size_bytes}|"
            f"checksum={str(entry.has_checksum).lower()}|{reasons}|{entry.path}"
        )
    for entry in plan.unmanaged_entries:
        print(f"UNMANAGED|{entry.kind}|{entry.size_bytes}|{entry.path}")


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan CRCON backup retention without changing any files."
    )
    parser.add_argument(
        "--backup-dir",
        type=Path,
        default=Path(".deploy-backups"),
        help="Backup directory (default: .deploy-backups)",
    )
    parser.add_argument(
        "--state-dir",
        type=Path,
        default=Path(".deploy-state"),
        help="Deployment state directory (default: .deploy-state)",
    )
    parser.add_argument("--keep-latest", type=int, default=8)
    parser.add_argument("--keep-weekly", type=int, default=8)
    parser.add_argument("--keep-monthly", type=int, default=6)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    plan = build_retention_plan(
        args.backup_dir,
        args.state_dir,
        keep_latest=args.keep_latest,
        keep_weekly=args.keep_weekly,
        keep_monthly=args.keep_monthly,
    )
    if args.as_json:
        print(json.dumps(asdict(plan), indent=2, sort_keys=True))
    else:
        _print_text(plan)
    return os.EX_OK


if __name__ == "__main__":
    raise SystemExit(main())
