"""Bounded, opt-in retention primitives for high-volume runtime tables."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from typing import Any

from sqlalchemy import delete, select
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class RetentionResult:
    table: str
    cutoff: datetime
    eligible: int
    deleted: int
    truncated: bool
    dry_run: bool


def prune_rows(
    session: Session,
    *,
    model: Any,
    cutoff_column: Any,
    cutoff: datetime,
    batch_size: int,
    max_batches: int,
    execute: bool,
) -> RetentionResult:
    """Inspect or delete a bounded number of old rows in deterministic batches."""

    batch_size = max(1, min(int(batch_size), 10_000))
    max_batches = max(1, min(int(max_batches), 1_000))
    limit = batch_size * max_batches
    table_name = str(model.__table__.name)

    if not execute:
        sampled = list(
            session.execute(
                select(model.id)
                .where(cutoff_column < cutoff)
                .order_by(cutoff_column.asc(), model.id.asc())
                .limit(limit + 1)
            ).scalars()
        )
        return RetentionResult(
            table=table_name,
            cutoff=cutoff,
            eligible=min(len(sampled), limit),
            deleted=0,
            truncated=len(sampled) > limit,
            dry_run=True,
        )

    deleted_count = 0
    truncated = False
    for _ in range(max_batches):
        row_ids = list(
            session.execute(
                select(model.id)
                .where(cutoff_column < cutoff)
                .order_by(cutoff_column.asc(), model.id.asc())
                .limit(batch_size)
            ).scalars()
        )
        if not row_ids:
            break
        session.execute(
            delete(model)
            .where(model.id.in_(row_ids))
            .execution_options(synchronize_session=False)
        )
        session.commit()
        deleted_count += len(row_ids)
        if len(row_ids) == batch_size:
            truncated = True
        else:
            truncated = False
            break

    return RetentionResult(
        table=table_name,
        cutoff=cutoff,
        eligible=deleted_count,
        deleted=deleted_count,
        truncated=truncated,
        dry_run=False,
    )
