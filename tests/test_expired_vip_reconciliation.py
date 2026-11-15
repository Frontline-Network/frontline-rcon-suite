"""Reconcile absent expired VIPs without deleting a later extension."""
from contextlib import contextmanager, nullcontext
from concurrent.futures import ThreadPoolExecutor, TimeoutError as FutureTimeout
from datetime import datetime, timedelta, timezone
import os
from threading import Event
from unittest.mock import Mock
from uuid import uuid4

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from rcon.expiring_vips import service
from rcon.models import PlayerID, PlayerName, PlayerVIP
from rcon.vip_rewards import locking, service as vip_service


@pytest.fixture(params=["sqlite", "postgres"])
def db(monkeypatch, request):
    root = None
    schema = None
    if request.param == "postgres":
        dsn = os.environ.get("TEST_POSTGRES_DSN")
        if not dsn:
            pytest.skip("requires disposable PostgreSQL")
        root = create_engine(dsn)
        schema = "vip_expiry_" + uuid4().hex
        with root.begin() as conn:
            conn.exec_driver_sql(f'CREATE SCHEMA "{schema}"')
        engine = create_engine(dsn, connect_args={"options": f"-csearch_path={schema}"})
    else:
        engine = create_engine("sqlite://")
    for model in (PlayerID, PlayerName, PlayerVIP):
        model.__table__.create(engine)
    maker = sessionmaker(engine, expire_on_commit=False)
    @contextmanager
    def session():
        with maker.begin() as sess:
            yield sess
    monkeypatch.setattr(service, "enter_session", session)
    monkeypatch.setattr(service, "get_server_number", lambda: 1)
    monkeypatch.setattr(locking, "vip_lock", lambda _player_id: nullcontext())
    expiry = datetime.now(timezone.utc) - timedelta(days=1)
    with maker.begin() as sess:
        player = PlayerID(player_id="fake", created=datetime.now())
        sess.add(player)
        sess.flush()
        sess.add(PlayerName(player_id_id=player.id, name="Fake", created=datetime.now(), last_seen=datetime.now()))
        sess.add(PlayerVIP(player_id_id=player.id, server_number=1, expiration=expiry))
    yield maker, expiry
    engine.dispose()
    if root is not None:
        with root.begin() as conn:
            conn.exec_driver_sql(f'DROP SCHEMA "{schema}" CASCADE')
        root.dispose()


def test_missing_server_vip_clears_only_the_old_local_record(db, monkeypatch):
    maker, expiry = db
    monkeypatch.setattr(vip_service, "current_vip", lambda *_args: None)
    rcon = Mock()
    assert service._resolve_expired_vip(rcon, "fake", expiry) == "orphan_cleaned"
    assert service._resolve_expired_vip(rcon, "fake", expiry) == "already_clean"
    with maker() as sess:
        assert sess.query(PlayerVIP).count() == 0
    rcon.remove_vip.assert_not_called()


def test_extended_record_is_not_deleted_after_stale_scan(db, monkeypatch):
    maker, expiry = db
    monkeypatch.setattr(vip_service, "current_vip", lambda *_args: None)
    with maker.begin() as sess:
        sess.query(PlayerVIP).one().expiration = datetime.now(timezone.utc) + timedelta(days=2)
    assert service._resolve_expired_vip(Mock(), "fake", expiry) == "changed"
    with maker() as sess:
        assert sess.query(PlayerVIP).count() == 1


def test_server_rejection_keeps_record_and_is_not_reported_as_removed(db, monkeypatch):
    maker, expiry = db
    monkeypatch.setattr(vip_service, "current_vip", lambda *_args: {"player_id": "fake"})
    rcon = Mock()
    rcon.remove_vip.return_value = False
    assert service._resolve_expired_vip(rcon, "fake", expiry) == "changed"
    with maker() as sess:
        assert sess.query(PlayerVIP).count() == 1


def test_failed_server_lookup_never_deletes_the_record(db, monkeypatch):
    maker, expiry = db
    def fail(*_args):
        raise TimeoutError("server unavailable")
    monkeypatch.setattr(vip_service, "current_vip", fail)
    with pytest.raises(TimeoutError):
        service._resolve_expired_vip(Mock(), "fake", expiry)
    with maker() as sess:
        assert sess.query(PlayerVIP).count() == 1


def test_concurrent_extension_wins_before_orphan_cleanup(db, monkeypatch):
    maker, expiry = db
    if maker.kw["bind"].dialect.name != "postgresql":
        pytest.skip("requires PostgreSQL row locks")
    monkeypatch.setattr(vip_service, "current_vip", lambda *_args: None)
    started = Event()
    def cleanup():
        started.set()
        return service._resolve_expired_vip(Mock(), "fake", expiry)
    with maker() as extending, ThreadPoolExecutor(max_workers=1) as pool:
        tx = extending.begin()
        try:
            row = extending.query(PlayerVIP).with_for_update().one()
            row.expiration = datetime.now(timezone.utc) + timedelta(days=2)
            extending.flush()
            future = pool.submit(cleanup)
            assert started.wait(3)
            with pytest.raises(FutureTimeout):
                future.result(timeout=0.3)
            tx.commit()
        finally:
            if tx.is_active:
                tx.rollback()
        assert future.result(timeout=5) == "changed"
    with maker() as sess:
        assert sess.query(PlayerVIP).count() == 1


def test_worker_audits_orphan_once_and_never_claims_server_removal(db, monkeypatch):
    maker, _expiry = db
    monkeypatch.setattr(vip_service, "current_vip", lambda *_args: None)
    audit = Mock()
    monkeypatch.setattr(service, "send_to_discord_audit", audit)
    rcon = Mock()
    rcon.get_vip_ids.return_value = []
    service.remove_expired_vips(rcon)
    service.remove_expired_vips(rcon)
    audit.assert_called_once()
    assert "already absent on server" in audit.call_args.kwargs["message"]
    rcon.remove_vip.assert_not_called()
    with maker() as sess:
        assert sess.query(PlayerVIP).count() == 0


@pytest.mark.parametrize("accepted", [True, False])
def test_worker_audits_only_confirmed_server_removals(db, monkeypatch, accepted):
    monkeypatch.setattr(vip_service, "current_vip", lambda *_args: {"player_id": "fake"})
    audit = Mock()
    monkeypatch.setattr(service, "send_to_discord_audit", audit)
    rcon = Mock()
    rcon.get_vip_ids.return_value = []
    rcon.remove_vip.return_value = accepted
    service.remove_expired_vips(rcon)
    assert audit.call_count == (1 if accepted else 0)
    if accepted:
        assert audit.call_args.kwargs["message"].startswith("Removed VIP")
