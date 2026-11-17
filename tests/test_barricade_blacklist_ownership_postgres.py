"""Synthetic provenance constraints against a disposable PostgreSQL schema."""
import pytest
import os
from contextlib import contextmanager
from sqlalchemy.exc import IntegrityError
from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
from alembic.migration import MigrationContext
from alembic.operations import Operations
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()

from rcon.barricade_blacklist_ownership import BarricadeBlacklistOwnership, is_owned
from rcon.barricade_scan_journal import BarricadeScanIntegration
from rcon.models import BlacklistRecord
from tests.test_blacklist_sync_journal_postgres import database, existing_blacklist
from api import barricade

PEER = '01234567-89ab-4def-8012-0123456789ab'
OTHER = '01234567-89ab-4def-8012-0123456789ac'


def prepare(database):
    engine = database.kw['bind']
    BarricadeScanIntegration.__table__.create(engine)
    BarricadeBlacklistOwnership.__table__.create(engine)
    with database.begin() as session:
        session.add(BarricadeScanIntegration(server_number=3, integration_id=PEER,
                                              credential_id=1, registered_at_us=1))


def test_ownership_is_exact_and_cascades_with_record(database, existing_blacklist):
    record_id, _, _ = existing_blacklist
    prepare(database)
    with database.begin() as session:
        session.add(BarricadeBlacklistOwnership(record_id=record_id, server_number=3, integration_id=PEER))
    with database() as session:
        assert is_owned(session, record_id, 3, PEER)
        assert not is_owned(session, record_id, 4, PEER)
        assert not is_owned(session, record_id, 3, OTHER)
    with database.begin() as session:
        session.delete(session.get(BlacklistRecord, record_id))
    with database() as session:
        assert not is_owned(session, record_id, 3, PEER)


def test_invalid_owner_and_transaction_abort_do_not_persist(database, existing_blacklist):
    record_id, _, _ = existing_blacklist
    prepare(database)
    with pytest.raises(IntegrityError):
        with database.begin() as session:
            session.add(BarricadeBlacklistOwnership(record_id=record_id, server_number=3, integration_id=OTHER))
    with pytest.raises(ValueError):
        with database.begin() as session:
            session.add(BarricadeBlacklistOwnership(record_id=record_id, server_number=3, integration_id=PEER))
            session.flush()
            raise ValueError('synthetic failure')
    with database() as session:
        assert not is_owned(session, record_id, 3, PEER)
        assert session.get(BlacklistRecord, record_id) is not None


def test_owned_ban_does_not_adopt_or_remove_manual_record(database, existing_blacklist, monkeypatch):
    record_id, first, second = existing_blacklist
    prepare(database)
    @contextmanager
    def session_scope():
        with database() as session:
            yield session
    monkeypatch.setattr(barricade.models, 'enter_session', session_scope)
    owner = (3, PEER, 1)
    assert barricade.ban_player.func('synthetic-player', first, 'reason', owner) is None
    assert not barricade.unban_player.func(record_id, first, owner)
    created = barricade.ban_player.func('synthetic-player', second, 'reason', owner)
    assert created and created != record_id
    assert barricade.ban_player.func('synthetic-player', second, 'reason', owner) == created
    assert not barricade.unban_player.func(created, second, (3, OTHER, 1))
    with database.begin() as session:
        session.get(BarricadeScanIntegration, (3, PEER)).credential_id = 2
    assert barricade.ban_player.func('synthetic-player', second, 'reason', owner) is None
    assert not barricade.unban_player.func(created, second, owner)
    owner = (3, PEER, 2)
    assert barricade.unban_player.func(created, second, owner)
    with database() as session:
        assert session.get(BlacklistRecord, record_id) is not None
        assert session.get(BlacklistRecord, created) is None


def test_migration_preserves_nonempty_ownership_on_downgrade(database, existing_blacklist, monkeypatch):
    record_id, _, _ = existing_blacklist
    engine = database.kw['bind']
    BarricadeScanIntegration.__table__.create(engine)
    path = Path(os.environ.get('BARRICADE_OWNERSHIP_MIGRATION') or
                Path(__file__).resolve().parents[1] / 'alembic/versions/f3980a1b2c3d_barricade_blacklist_ownership.py')
    spec = spec_from_file_location('ownership_migration_test', path)
    migration = module_from_spec(spec)
    spec.loader.exec_module(migration)
    with engine.begin() as connection:
        monkeypatch.setattr(migration, 'op', Operations(MigrationContext.configure(connection)))
        migration.upgrade()
    with database.begin() as session:
        session.add(BarricadeScanIntegration(server_number=3, integration_id=PEER,
                                              credential_id=1, registered_at_us=1))
        session.flush()
        session.add(BarricadeBlacklistOwnership(record_id=record_id, server_number=3, integration_id=PEER))
    with engine.begin() as connection:
        monkeypatch.setattr(migration, 'op', Operations(MigrationContext.configure(connection)))
        with pytest.raises(RuntimeError, match='Refusing'):
            migration.downgrade()
    with database.begin() as session:
        session.delete(session.get(BarricadeBlacklistOwnership, record_id))
    with engine.begin() as connection:
        monkeypatch.setattr(migration, 'op', Operations(MigrationContext.configure(connection)))
        migration.downgrade()
