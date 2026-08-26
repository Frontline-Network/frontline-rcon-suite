import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from scripts.plan_storage_hygiene import build_retention_plan


def _backup(backup_dir: Path, name: str, when: datetime, *, checksum=True) -> Path:
    path = backup_dir / f"postgres-{name}.dump"
    path.write_bytes(name.encode("utf-8"))
    timestamp = when.replace(tzinfo=timezone.utc).timestamp()
    os.utime(path, (timestamp, timestamp))
    if checksum:
        path.with_name(path.name + ".sha256").write_text("test checksum\n")
    return path.resolve()


def test_plan_is_read_only_and_protects_tiers_and_deployment_state(tmp_path):
    backup_dir = tmp_path / ".deploy-backups"
    state_dir = tmp_path / ".deploy-state"
    backup_dir.mkdir()
    state_dir.mkdir()

    backups = [
        _backup(
            backup_dir,
            f"2026{i:02d}",
            datetime(2026, month, day, tzinfo=timezone.utc),
        )
        for i, (month, day) in enumerate(
            [(8, 26), (8, 25), (8, 18), (8, 11), (7, 28), (7, 1), (6, 1), (5, 1)],
            start=1,
        )
    ]
    referenced = backups[-1]
    state_dir.joinpath("deploy.env").write_text(
        f"DATABASE_BACKUP={referenced}\n", encoding="utf-8"
    )
    before = sorted(path.name for path in backup_dir.iterdir())

    plan = build_retention_plan(
        backup_dir,
        state_dir,
        keep_latest=2,
        keep_weekly=2,
        keep_monthly=2,
    )

    after = sorted(path.name for path in backup_dir.iterdir())
    assert before == after
    assert plan.total_count == 8
    assert plan.keep_count < plan.total_count
    entry_by_path = {Path(entry.path): entry for entry in plan.entries}
    assert "latest" in entry_by_path[backups[0]].reasons
    assert "weekly" in entry_by_path[backups[2]].reasons
    assert "monthly" in entry_by_path[backups[4]].reasons
    assert "deployment-state" in entry_by_path[referenced].reasons
    assert entry_by_path[referenced].decision == "keep"


def test_plan_reports_missing_checksum(tmp_path):
    backup_dir = tmp_path / ".deploy-backups"
    backup_dir.mkdir()
    missing = _backup(
        backup_dir,
        "missing-checksum",
        datetime(2026, 8, 26, tzinfo=timezone.utc),
        checksum=False,
    )

    plan = build_retention_plan(
        backup_dir,
        tmp_path / ".deploy-state",
        keep_latest=1,
        keep_weekly=0,
        keep_monthly=0,
    )

    assert plan.missing_checksum_count == 1
    assert Path(plan.entries[0].path) == missing


@pytest.mark.parametrize("argument", ["keep_latest", "keep_weekly", "keep_monthly"])
def test_plan_rejects_negative_limits(tmp_path, argument):
    backup_dir = tmp_path / ".deploy-backups"
    backup_dir.mkdir()
    values = {"keep_latest": 1, "keep_weekly": 1, "keep_monthly": 1}
    values[argument] = -1

    with pytest.raises(ValueError, match="must not be negative"):
        build_retention_plan(
            backup_dir,
            tmp_path / ".deploy-state",
            **values,
        )


def test_cli_declares_read_only_and_outputs_candidates(tmp_path):
    backup_dir = tmp_path / ".deploy-backups"
    backup_dir.mkdir()
    _backup(
        backup_dir,
        "new",
        datetime(2026, 8, 26, tzinfo=timezone.utc),
    )
    _backup(
        backup_dir,
        "old",
        datetime(2025, 1, 1, tzinfo=timezone.utc),
    )

    result = subprocess.run(
        [
            sys.executable,
            "scripts/plan_storage_hygiene.py",
            "--backup-dir",
            str(backup_dir),
            "--state-dir",
            str(tmp_path / ".deploy-state"),
            "--keep-latest",
            "1",
            "--keep-weekly",
            "0",
            "--keep-monthly",
            "0",
        ],
        cwd=Path(__file__).resolve().parents[1],
        check=True,
        capture_output=True,
        text=True,
    )

    assert "READ-ONLY STORAGE PLAN" in result.stdout
    assert "Candidates: 1 backups" in result.stdout
    assert (backup_dir / "postgres-new.dump").exists()
    assert (backup_dir / "postgres-old.dump").exists()
