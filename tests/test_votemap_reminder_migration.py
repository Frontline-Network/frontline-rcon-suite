"""Validate clean and staged reminder migrations without production data."""
import importlib.util
import os
from pathlib import Path
import uuid

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, inspect, text
from sqlalchemy.schema import CreateSchema, DropSchema


def migration():
    path = Path(__file__).resolve().parents[1] / "alembic/versions/d3330a1b2c3d_votemap_reminder_delivery.py"
    spec = importlib.util.spec_from_file_location("votemap_reminder_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def test_clean_and_staged_migration_and_safe_downgrade():
    engine = create_engine("sqlite://")
    mod = migration()
    with engine.begin() as connection:
        mod.op = Operations(MigrationContext.configure(connection))
        mod.upgrade()
        mod.upgrade()
        assert inspect(connection).has_table("votemap_reminder_delivery")
        connection.execute(text("INSERT INTO votemap_reminder_batch VALUES (3, 'periodic', 'batch', 'sig', 'message', 'open', 1, NULL)"))
        with pytest.raises(RuntimeError, match="open Votemap"):
            mod.downgrade()
        connection.execute(text("UPDATE votemap_reminder_batch SET status = 'completed', completed_at = 2"))
        connection.execute(text("INSERT INTO votemap_reminder_delivery VALUES (3, 'batch', 'fake', 'token', 'unknown', 1, 2, 2)"))
        with pytest.raises(RuntimeError, match="uncertain"):
            mod.downgrade()
        connection.execute(text("UPDATE votemap_reminder_delivery SET status = 'sent'"))
        mod.downgrade()
        assert not inspect(connection).has_table("votemap_reminder_batch")
    engine.dispose()


def test_partial_staging_is_rejected():
    engine = create_engine("sqlite://")
    mod = migration()
    with engine.begin() as connection:
        connection.execute(text("CREATE TABLE votemap_reminder_clock (server_number integer primary key)"))
        mod.op = Operations(MigrationContext.configure(connection))
        with pytest.raises(RuntimeError, match="incomplete"):
            mod.upgrade()
    engine.dispose()


@pytest.mark.skipif(not os.environ.get("RCON_VOTEMAP_TEST_DATABASE"), reason="requires isolated PostgreSQL")
def test_postgres_staged_schema_validation_and_drift_rejection():
    engine = create_engine(os.environ["RCON_VOTEMAP_TEST_DATABASE"])
    schema = "votemap_migration_" + uuid.uuid4().hex
    with engine.begin() as connection:
        connection.execute(CreateSchema(schema))
    try:
        with engine.begin() as connection:
            connection.execute(text(f'SET LOCAL search_path TO "{schema}"'))
            mod = migration()
            mod.op = Operations(MigrationContext.configure(connection))
            mod.upgrade()
            mod.upgrade()
            connection.execute(text("ALTER TABLE votemap_reminder_delivery ADD COLUMN unexpected integer"))
            with pytest.raises(RuntimeError, match="columns"):
                mod.upgrade()
    finally:
        with engine.begin() as connection:
            connection.execute(DropSchema(schema, cascade=True))
        engine.dispose()
