"""Additive schema smoke test; no existing incident content may be replaced."""

import importlib.util
from pathlib import Path

from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text


def test_migration_preserves_existing_incident_and_removes_only_own_fields(monkeypatch):
    spec = importlib.util.spec_from_file_location(
        "leadership_migration",
        Path(__file__).resolve().parents[1]
        / "alembic/versions/e3a8b1c5d209_leadership_votes.py",
    )
    migration = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(migration)
    engine = create_engine("sqlite://")
    with engine.begin() as connection:
        connection.execute(
            text("CREATE TABLE admin_incident (id TEXT PRIMARY KEY, reason TEXT)")
        )
        connection.execute(
            text(
                "INSERT INTO admin_incident VALUES ('old-report', 'Preserve this report')"
            )
        )
        monkeypatch.setattr(
            migration, "op", Operations(MigrationContext.configure(connection))
        )
        migration.upgrade()
        names = inspect(connection).get_table_names()
        assert {"leadership_vote", "leadership_message", "leadership_presence"} <= set(names)
        assert (
            connection.scalar(
                text("SELECT reason FROM admin_incident WHERE id='old-report'")
            )
            == "Preserve this report"
        )
        migration.downgrade()
        assert inspect(connection).get_table_names() == ["admin_incident"]
        assert (
            connection.scalar(
                text("SELECT reason FROM admin_incident WHERE id='old-report'")
            )
            == "Preserve this report"
        )
    engine.dispose()
