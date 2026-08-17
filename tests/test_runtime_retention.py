import os
from datetime import UTC, datetime, timedelta

from sqlalchemy import DateTime, Integer, create_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")

from rcon.retention import prune_rows


class Base(DeclarativeBase):
    pass


class RuntimeRow(Base):
    __tablename__ = "runtime_rows"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, index=True)


def _session_with_rows() -> Session:
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session = Session(engine)
    now = datetime.now(UTC).replace(tzinfo=None)
    session.add_all(
        RuntimeRow(id=index, created_at=now - timedelta(days=index))
        for index in range(1, 8)
    )
    session.commit()
    return session


def test_retention_dry_run_never_deletes_and_reports_bounded_count():
    session = _session_with_rows()
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2)

    result = prune_rows(
        session,
        model=RuntimeRow,
        cutoff_column=RuntimeRow.created_at,
        cutoff=cutoff,
        batch_size=2,
        max_batches=2,
        execute=False,
    )

    assert result.dry_run is True
    assert result.deleted == 0
    assert result.eligible == 4
    assert result.truncated is True
    assert session.query(RuntimeRow).count() == 7


def test_retention_execute_commits_small_bounded_batches():
    session = _session_with_rows()
    cutoff = datetime.now(UTC).replace(tzinfo=None) - timedelta(days=2)

    result = prune_rows(
        session,
        model=RuntimeRow,
        cutoff_column=RuntimeRow.created_at,
        cutoff=cutoff,
        batch_size=2,
        max_batches=2,
        execute=True,
    )

    assert result.dry_run is False
    assert result.deleted == 4
    assert result.truncated is True
    assert session.query(RuntimeRow).count() == 3
