"""Dry-run-first retention for the largest append-only CRCON tables."""

from __future__ import annotations

import os
from datetime import datetime, timedelta, timezone

from django.core.management.base import BaseCommand, CommandError

from rcon.models import AuditLog, LogLine, enter_session
from rcon.retention import prune_rows


def _environment_int(name: str, default: int) -> int:
    try:
        return int(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


class Command(BaseCommand):
    help = "Inspect or prune old logs and audit records in bounded batches"
    requires_system_checks = []

    def add_arguments(self, parser):
        parser.add_argument("--execute", action="store_true")
        parser.add_argument("--log-days", type=int)
        parser.add_argument("--audit-days", type=int)
        parser.add_argument("--batch-size", type=int)
        parser.add_argument("--max-batches", type=int)

    def handle(self, *args, **options):
        if os.getenv("SERVER_NUMBER", "1") != "1":
            self.stdout.write("Retention skipped: global command runs on server 1")
            return

        log_days = options.get("log_days")
        if log_days is None:
            log_days = _environment_int("HLL_LOG_RETENTION_DAYS", 0)
        audit_days = options.get("audit_days")
        if audit_days is None:
            audit_days = _environment_int("HLL_AUDIT_RETENTION_DAYS", 0)
        batch_size = options.get("batch_size") or _environment_int(
            "HLL_RETENTION_BATCH_SIZE", 1_000
        )
        max_batches = options.get("max_batches") or _environment_int(
            "HLL_RETENTION_MAX_BATCHES", 10
        )
        execute = bool(options.get("execute"))

        if log_days < 0 or audit_days < 0:
            raise CommandError("Retention days must be zero (disabled) or positive")
        if not log_days and not audit_days:
            self.stdout.write(
                "Retention disabled: set HLL_LOG_RETENTION_DAYS and/or "
                "HLL_AUDIT_RETENTION_DAYS"
            )
            return

        now_utc = datetime.now(tz=timezone.utc)
        policies = []
        if log_days:
            policies.append(
                (
                    LogLine,
                    LogLine.event_time,
                    now_utc.replace(tzinfo=None) - timedelta(days=log_days),
                )
            )
        if audit_days:
            policies.append(
                (AuditLog, AuditLog.creation_time, now_utc - timedelta(days=audit_days))
            )

        with enter_session() as session:
            for model, cutoff_column, cutoff in policies:
                result = prune_rows(
                    session,
                    model=model,
                    cutoff_column=cutoff_column,
                    cutoff=cutoff,
                    batch_size=batch_size,
                    max_batches=max_batches,
                    execute=execute,
                )
                qualifier = ">=" if result.truncated else ""
                if result.dry_run:
                    self.stdout.write(
                        f"DRY RUN {result.table}: eligible {qualifier}"
                        f"{result.eligible}, cutoff {result.cutoff.isoformat()}"
                    )
                else:
                    self.stdout.write(
                        f"EXECUTED {result.table}: deleted {result.deleted}, "
                        f"more_remaining={str(result.truncated).lower()}"
                    )
