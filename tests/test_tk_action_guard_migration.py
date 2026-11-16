"""The teamkill guard migration must not discard or silently accept data."""
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations


path = Path(__file__).parents[1] / 'alembic/versions/e4430a1b2c3d_teamkill_ban_guard.py'
spec = importlib.util.spec_from_file_location('teamkill_guard_migration', path)
migration = importlib.util.module_from_spec(spec)
spec.loader.exec_module(migration)


def call(connection, function):
    with Operations.context(MigrationContext.configure(connection)):
        function()


def test_create_staged_validation_and_empty_rollback():
    engine = sa.create_engine('sqlite://')
    with engine.begin() as connection:
        call(connection, migration.upgrade)
        assert sa.inspect(connection).has_table('teamkill_ban_guard')
        call(connection, migration.upgrade)
        call(connection, migration.downgrade)
        assert not sa.inspect(connection).has_table('teamkill_ban_guard')


def test_partial_staging_is_refused():
    engine = sa.create_engine('sqlite://')
    with engine.begin() as connection:
        connection.execute(sa.text('CREATE TABLE teamkill_ban_guard (id INTEGER)'))
        with pytest.raises(RuntimeError, match='incomplete'):
            call(connection, migration.upgrade)


def test_nonempty_rollback_is_refused():
    engine = sa.create_engine('sqlite://')
    with engine.begin() as connection:
        call(connection, migration.upgrade)
        connection.execute(sa.text('INSERT INTO teamkill_ban_cutover (server_number, event_ms) VALUES (3, 1000)'))
        with pytest.raises(RuntimeError, match='contains data'):
            call(connection, migration.downgrade)
        assert sa.inspect(connection).has_table('teamkill_ban_guard')


def test_postgres_staging_validation_and_rollback():
    dsn = os.environ.get('TEST_POSTGRES_DSN')
    if not dsn:
        pytest.skip('requires disposable PostgreSQL')
    root = sa.create_engine(dsn)
    schema = 'tk_migration_' + uuid4().hex
    with root.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    engine = sa.create_engine(dsn, connect_args={'options': f'-csearch_path={schema}'})
    try:
        with engine.begin() as connection:
            call(connection, migration.upgrade)
            call(connection, migration.upgrade)
            call(connection, migration.downgrade)
            assert not sa.inspect(connection).has_table('teamkill_ban_guard')
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()
