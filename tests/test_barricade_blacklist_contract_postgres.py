from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone
import os

import django
import pytest
from sqlalchemy import select

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'rconweb.rconweb.test_settings')
django.setup()
from api import barricade
from rcon import blacklist_sync_journal as journal
from rcon.models import BlacklistRecord
from tests.test_blacklist_sync_journal_postgres import database, existing_blacklist


def test_real_list_scope_expiry_and_durable_delivery(database, existing_blacklist, monkeypatch):
    record_id, first, second = existing_blacklist

    @contextmanager
    def session_scope():
        with database() as session:
            yield session

    monkeypatch.setattr(barricade.models, 'enter_session', session_scope)
    with pytest.raises(barricade.BarricadeRequestError):
        barricade.assert_blacklist_exists.func(999999)
    barricade.assert_blacklist_exists.func(second)

    created = barricade.ban_player.func('synthetic-player', second, 'test')
    assert created != record_id
    assert barricade.ban_player.func('synthetic-player', second, 'test') == created
    with database() as session:
        assert session.get(BlacklistRecord, created).blacklist_id == second
        deliveries = session.scalars(select(journal.BlacklistSyncDelivery)).all()
        assert len(deliveries) == 1
        assert deliveries[0].server_number == 2

    with database() as session, session.begin():
        session.get(BlacklistRecord, created).expires_at = datetime.now(timezone.utc) - timedelta(seconds=1)
    replacement = barricade.ban_player.func('synthetic-player', second, 'test')
    assert replacement not in (record_id, created)


def test_concurrent_requests_create_one_record_and_one_delivery(database, existing_blacklist, monkeypatch):
    _, _, second = existing_blacklist

    @contextmanager
    def session_scope():
        with database() as session:
            yield session

    monkeypatch.setattr(barricade.models, 'enter_session', session_scope)
    with ThreadPoolExecutor(max_workers=2) as executor:
        first = executor.submit(barricade.ban_player.func, 'synthetic-player', second, 'test')
        duplicate = executor.submit(barricade.ban_player.func, 'synthetic-player', second, 'test')
        first_id, duplicate_id = first.result(timeout=20), duplicate.result(timeout=20)
    assert first_id is not None and first_id == duplicate_id
    with database() as session:
        records = session.scalars(select(BlacklistRecord).where(BlacklistRecord.blacklist_id == second)).all()
        assert len(records) == 1
        assert len(session.scalars(select(journal.BlacklistSyncDelivery)).all()) == 1


def test_unban_cannot_remove_record_from_another_list(database, existing_blacklist):
    record_id, first, second = existing_blacklist
    assert barricade.unban_player.func(record_id, second) is False
    with database() as session:
        assert session.get(BlacklistRecord, record_id).blacklist_id == first
        assert session.scalars(select(journal.BlacklistSyncDelivery)).all() == []
    assert barricade.unban_player.func(record_id, first) is True
    with database() as session:
        assert session.get(BlacklistRecord, record_id) is None
        deliveries = session.scalars(select(journal.BlacklistSyncDelivery)).all()
        assert len(deliveries) == 1 and deliveries[0].server_number == 1
    assert barricade.unban_player.func(record_id, first) is False


def test_concurrent_list_move_cannot_delete_record_from_new_list(database, existing_blacklist):
    record_id, first, second = existing_blacklist
    with ThreadPoolExecutor(max_workers=1) as executor:
        with database() as session, session.begin():
            record = session.get(BlacklistRecord, record_id, with_for_update=True)
            record.blacklist_id = second
            unban = executor.submit(barricade.unban_player.func, record_id, first)
        assert unban.result(timeout=15) is False
    with database() as session:
        assert session.get(BlacklistRecord, record_id).blacklist_id == second
        assert session.scalars(select(journal.BlacklistSyncDelivery)).all() == []
