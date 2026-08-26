#!/usr/bin/env python3
"""Estimate CRCON runtime-data retention without scanning or changing rows.

This command uses PostgreSQL catalog statistics and ``EXPLAIN`` only.  It opens
an explicitly read-only transaction, applies a short statement timeout and
always rolls the transaction back.  The reported row and byte values are
planner estimates, not exact counts or guaranteed filesystem savings.
"""

from __future__ import annotations

import argparse
import json
import os
from dataclasses import asdict, dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import Connection, text


@dataclass(frozen=True)
class Policy:
    table: str
    cutoff_column: str
    retention_days: int
    cutoff: datetime


@dataclass(frozen=True)
class TablePlan:
    table: str
    cutoff_column: str
    retention_days: int
    cutoff: str
    estimated_live_rows: int
    estimated_candidate_rows: int
    estimated_candidate_share: float
    total_bytes: int
    heap_bytes: int
    index_bytes: int
    proportional_candidate_bytes: int


@dataclass(frozen=True)
class RetentionPlan:
    generated_at: str
    read_only: bool
    estimate_only: bool
    total_estimated_candidate_rows: int
    total_proportional_candidate_bytes: int
    tables: tuple[TablePlan, ...]


_RELATION_SQL = text("""
    SELECT
        GREATEST(c.reltuples::bigint, 0) AS estimated_live_rows,
        pg_total_relation_size(c.oid) AS total_bytes,
        pg_relation_size(c.oid) AS heap_bytes,
        pg_indexes_size(c.oid) AS index_bytes
    FROM pg_class AS c
    WHERE c.oid = to_regclass(:relation_name)
    """)


def _validated_identifier(value: str) -> str:
    if not value or not value.replace("_", "").isalnum():
        raise ValueError(f"Unsafe SQL identifier: {value!r}")
    return value


def _extract_plan_rows(payload: Any) -> int:
    if isinstance(payload, str):
        payload = json.loads(payload)
    if isinstance(payload, list):
        payload = payload[0]
    if not isinstance(payload, dict) or "Plan" not in payload:
        raise ValueError("PostgreSQL returned an unexpected EXPLAIN payload")
    return max(0, int(payload["Plan"].get("Plan Rows", 0)))


def _relation_stats(connection: Connection, table: str) -> dict[str, int]:
    row = (
        connection.execute(
            _RELATION_SQL,
            {"relation_name": f"public.{_validated_identifier(table)}"},
        )
        .mappings()
        .one_or_none()
    )
    if row is None:
        raise RuntimeError(f"Relation public.{table} does not exist")
    return {key: int(row[key] or 0) for key in row.keys()}


def _estimated_candidate_rows(connection: Connection, policy: Policy) -> int:
    table = _validated_identifier(policy.table)
    column = _validated_identifier(policy.cutoff_column)
    result = connection.execute(
        text(
            f"EXPLAIN (FORMAT JSON) SELECT id FROM public.{table} "
            f"WHERE {column} < :cutoff"
        ),
        {"cutoff": policy.cutoff},
    ).scalar_one()
    return _extract_plan_rows(result)


def build_table_plan(connection: Connection, policy: Policy) -> TablePlan:
    stats = _relation_stats(connection, policy.table)
    live_rows = stats["estimated_live_rows"]
    candidate_rows = min(_estimated_candidate_rows(connection, policy), live_rows)
    share = candidate_rows / live_rows if live_rows else 0.0
    return TablePlan(
        table=policy.table,
        cutoff_column=policy.cutoff_column,
        retention_days=policy.retention_days,
        cutoff=policy.cutoff.isoformat(),
        estimated_live_rows=live_rows,
        estimated_candidate_rows=candidate_rows,
        estimated_candidate_share=share,
        total_bytes=stats["total_bytes"],
        heap_bytes=stats["heap_bytes"],
        index_bytes=stats["index_bytes"],
        proportional_candidate_bytes=round(stats["total_bytes"] * share),
    )


def build_retention_plan(
    connection: Connection,
    *,
    log_days: int,
    audit_days: int,
    now: datetime | None = None,
) -> RetentionPlan:
    if log_days <= 0 or audit_days <= 0:
        raise ValueError("Retention days must be positive")

    generated_at = now or datetime.now(timezone.utc)
    generated_at = generated_at.astimezone(timezone.utc)
    policies = (
        Policy(
            table="log_lines",
            cutoff_column="event_time",
            retention_days=log_days,
            cutoff=(generated_at - timedelta(days=log_days)).replace(tzinfo=None),
        ),
        Policy(
            table="audit_log",
            cutoff_column="creation_time",
            retention_days=audit_days,
            cutoff=generated_at - timedelta(days=audit_days),
        ),
    )
    tables = tuple(build_table_plan(connection, policy) for policy in policies)
    return RetentionPlan(
        generated_at=generated_at.isoformat(),
        read_only=True,
        estimate_only=True,
        total_estimated_candidate_rows=sum(
            table.estimated_candidate_rows for table in tables
        ),
        total_proportional_candidate_bytes=sum(
            table.proportional_candidate_bytes for table in tables
        ),
        tables=tables,
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
    print("READ-ONLY DATA RETENTION PLAN — no rows are scanned or changed")
    print(f"Generated: {plan.generated_at}")
    for table in plan.tables:
        print(
            f"{table.table}: cutoff={table.cutoff}, "
            f"estimated_candidates={table.estimated_candidate_rows:,}/"
            f"{table.estimated_live_rows:,} "
            f"({table.estimated_candidate_share:.1%}), "
            f"proportional_footprint={_human_bytes(table.proportional_candidate_bytes)}"
        )
    print(
        "Total proportional footprint (estimate, not guaranteed disk recovery): "
        f"{_human_bytes(plan.total_proportional_candidate_bytes)}"
    )
    print(
        "Normal VACUUM makes freed space reusable inside PostgreSQL; it does not shrink files."
    )


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Estimate log retention from PostgreSQL planner statistics only."
    )
    parser.add_argument("--log-days", type=int, default=90)
    parser.add_argument("--audit-days", type=int, default=365)
    parser.add_argument("--statement-timeout-ms", type=int, default=15_000)
    parser.add_argument("--json", action="store_true", dest="as_json")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if args.statement_timeout_ms <= 0:
        raise ValueError("statement timeout must be positive")

    # Delay the application import so unit tests can exercise the pure planner
    # helpers without requiring a configured database or Redis instance.
    from rcon.models import get_engine

    engine = get_engine()
    with engine.connect() as connection:
        transaction = connection.begin()
        try:
            connection.exec_driver_sql("SET TRANSACTION READ ONLY")
            connection.exec_driver_sql(
                f"SET LOCAL statement_timeout = {int(args.statement_timeout_ms)}"
            )
            plan = build_retention_plan(
                connection,
                log_days=args.log_days,
                audit_days=args.audit_days,
            )
        finally:
            transaction.rollback()

    if args.as_json:
        print(json.dumps(asdict(plan), indent=2, sort_keys=True))
    else:
        _print_text(plan)
    return os.EX_OK


if __name__ == "__main__":
    raise SystemExit(main())
