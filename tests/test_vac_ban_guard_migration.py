"""Verify staged ban support, replay and safe downgrade on isolated databases."""
import importlib.util
import os
from pathlib import Path
from uuid import uuid4
import pytest
import sqlalchemy as sa
from alembic.migration import MigrationContext
from alembic.operations import Operations

root = Path(__file__).parents[1] / 'alembic/versions'


def load(name):
    spec = importlib.util.spec_from_file_location(name, root / f'{name}.py')
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


original = load('a3170a1b2c3d_automod_action_guard')
switch = load('f5550a1b2c3d_autobalancer_switch_guard')
ban = load('f6660a1b2c3d_automod_ban_guard')


def call(connection, function):
    with Operations.context(MigrationContext.configure(connection)):
        function()


def exercise(connection):
    call(connection, original.upgrade)
    call(connection, switch.upgrade)
    call(connection, ban.upgrade)
    call(connection, ban.upgrade)
    call(connection, switch.upgrade)  # Replay after staging must not narrow.
    if connection.dialect.name == 'postgresql':
        call(connection, original.upgrade)  # Shared revision can still replay the staged schema.
    connection.execute(sa.text("""INSERT INTO automod_action_guard
        (server_number, player_id, rule, action, token, state, updated_at)
        VALUES (3, 'fake', 'VacHistory', 'ban', 'token', 'pending', CURRENT_TIMESTAMP)"""))
    with pytest.raises(RuntimeError, match='Ban reservations exist'):
        call(connection, ban.downgrade)
    assert connection.execute(sa.text('SELECT COUNT(*) FROM automod_action_guard')).scalar_one() == 1
    connection.execute(sa.text("DELETE FROM automod_action_guard WHERE player_id = 'fake'"))
    call(connection, ban.downgrade)
    checks = sa.inspect(connection).get_check_constraints('automod_action_guard')
    sql = next(c['sqltext'] for c in checks if c['name'] == ban.CONSTRAINT)
    assert "'ban'" not in sql and "'switch'" in sql


def test_sqlite_upgrade_replay_and_safe_downgrade():
    engine = sa.create_engine('sqlite://')
    with engine.begin() as connection:
        exercise(connection)


def test_postgres_upgrade_replay_and_safe_downgrade():
    dsn = os.environ.get('TEST_POSTGRES_DSN')
    if not dsn:
        pytest.skip('requires disposable PostgreSQL')
    root_engine = sa.create_engine(dsn)
    schema = 'vac_ban_migration_' + uuid4().hex
    with root_engine.begin() as connection:
        connection.execute(sa.text(f'CREATE SCHEMA "{schema}"'))
    engine = sa.create_engine(dsn, connect_args={'options': f'-csearch_path={schema}'})
    try:
        with engine.begin() as connection:
            exercise(connection)
    finally:
        engine.dispose()
        with root_engine.begin() as connection:
            connection.execute(sa.text(f'DROP SCHEMA "{schema}" CASCADE'))
        root_engine.dispose()
