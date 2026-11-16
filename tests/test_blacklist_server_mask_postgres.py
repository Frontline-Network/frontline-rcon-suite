"""Server-mask schema and wire compatibility on a disposable PostgreSQL schema."""
import importlib.util
import os
from pathlib import Path
from uuid import uuid4

import pytest
from alembic.migration import MigrationContext
from alembic.operations import Operations
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DataError
from sqlalchemy.orm import Session

from rcon.blacklist import BlacklistCommand, BlacklistCommandType
from rcon.models import Blacklist
from rcon.types import BlacklistSyncMethod


@pytest.fixture
def database():
    dsn = os.environ.get("TEST_POSTGRES_DSN")
    if not dsn:
        pytest.skip("requires disposable PostgreSQL")
    root = create_engine(dsn)
    schema = "blacklist_mask_" + uuid4().hex
    with root.begin() as connection:
        connection.execute(text(f'CREATE SCHEMA "{schema}"'))
    engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    try:
        with engine.begin() as connection:
            connection.execute(text("CREATE TABLE blacklist (id integer PRIMARY KEY, name varchar NOT NULL, sync varchar NOT NULL, servers integer)"))
            connection.execute(text("INSERT INTO blacklist VALUES (1, 'old', 'KICK_ONLY', 1073741825), (2, 'all', 'KICK_ONLY', NULL)"))
        yield engine
    finally:
        engine.dispose()
        with root.begin() as connection:
            connection.execute(text(f'DROP SCHEMA "{schema}" CASCADE'))
        root.dispose()


def migrate(connection, method):
    path = Path(__file__).resolve().parents[1] / "alembic/versions/b3530a1b2c3d_blacklist_server_mask_bigint.py"
    spec = importlib.util.spec_from_file_location("blacklist_mask_migration", path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.op = Operations(MigrationContext.configure(connection))
    getattr(module, method)()


def test_migration_preserves_old_rows_and_supports_server_32_and_wire(database):
    with database.begin() as connection:
        migrate(connection, "upgrade")
    with Session(database) as session, session.begin():
        old = session.get(Blacklist, 1)
        assert old.get_server_numbers() == {1, 31}
        assert session.get(Blacklist, 2).get_server_numbers() is None
        for ident, numbers in enumerate(([32], [1, 32], list(range(1, 33))), 3):
            item = Blacklist(id=ident, name=str(ident), sync=BlacklistSyncMethod.KICK_ONLY)
            item.set_server_numbers(numbers)
            session.add(item)
        session.flush()
        server_32 = session.scalars(select(Blacklist.id).where(Blacklist.servers.bitwise_and(1 << 31) != 0)).all()
        assert set(server_32) == {3, 4, 5}
        for ident in (3, 4, 5):
            item = session.get(Blacklist, ident)
            cmd = BlacklistCommand(command=BlacklistCommandType.EXPIRE_ALL, server_mask=item.servers, payload={"player_id": "synthetic"})
            assert BlacklistCommand.decode(cmd.encode()).server_mask == item.servers
        all_servers = BlacklistCommand(command=BlacklistCommandType.EXPIRE_ALL, server_mask=None, payload={"player_id": "synthetic"})
        assert BlacklistCommand.decode(all_servers.encode()).server_mask == 2**32 - 1

    # Downgrade must not silently corrupt server-32 selections.
    with pytest.raises(DataError):
        with database.begin() as connection:
            migrate(connection, "downgrade")
    with database.begin() as connection:
        assert connection.execute(text("SELECT servers FROM blacklist WHERE id=3")).scalar_one() == 1 << 31
        connection.execute(text("DELETE FROM blacklist WHERE id >= 3"))
        migrate(connection, "downgrade")
        assert connection.execute(text("SELECT servers FROM blacklist WHERE id=1")).scalar_one() == 1073741825
