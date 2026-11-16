from contextlib import contextmanager
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime, timedelta, timezone

import django
import pytest
from sqlalchemy import select

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
