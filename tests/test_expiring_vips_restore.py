from datetime import datetime, timedelta, timezone
from contextlib import nullcontext
from types import SimpleNamespace
from unittest import mock

import pytest

from rcon.expiring_vips.service import restore_missing_vips


@pytest.fixture(autouse=True)
def action_reservations(monkeypatch):
    from rcon.automods import action_guard
    monkeypatch.setattr(action_guard, 'reserve', lambda *_args, **_kwargs: 'fake-token')
    monkeypatch.setattr(action_guard, 'finish', lambda *_args, **_kwargs: 1)


def _vip(player_id, expiration, name="Player"):
    return SimpleNamespace(
        expiration=expiration,
        player=SimpleNamespace(
            player_id=player_id,
            names=[SimpleNamespace(name=name)],
        ),
    )


@mock.patch("rcon.vip_rewards.locking.vip_lock", side_effect=lambda _: nullcontext())
@mock.patch("rcon.expiring_vips.service.get_server_number", return_value="3")
@mock.patch("rcon.expiring_vips.service.enter_session")
def test_restore_missing_vips_only_adds_active_missing_records(
    enter_session, _get_server_number, _lock
):
    now = datetime.now(timezone.utc)
    active_existing = _vip("existing", now + timedelta(days=1))
    active_missing = _vip("missing", now + timedelta(days=2), "Missing Player")

    query = mock.Mock()
    query.filter.return_value.all.return_value = [active_existing, active_missing]
    query.join.return_value.filter.return_value.with_for_update.return_value.one_or_none.return_value = active_missing
    session = mock.Mock()
    session.query.return_value = query
    enter_session.return_value.__enter__.return_value = session

    rcon = mock.Mock()
    rcon.get_vip_ids.return_value = [{"player_id": "existing"}]
    rcon.without_retries.return_value = nullcontext()
    rcon.add_vip.return_value = True

    assert restore_missing_vips(rcon) == 1
    rcon.add_vip.assert_called_once_with(
        player_id="missing",
        description="Missing Player",
        expiration=active_missing.expiration.isoformat(),
    )


@mock.patch("rcon.vip_rewards.locking.vip_lock", side_effect=lambda _: nullcontext())
@mock.patch("rcon.expiring_vips.service.get_server_number", return_value="3")
@mock.patch("rcon.expiring_vips.service.enter_session")
def test_restore_missing_vips_keeps_going_after_one_rcon_failure(
    enter_session, _get_server_number, _lock
):
    now = datetime.now(timezone.utc)
    first = _vip("first", now + timedelta(days=1))
    second = _vip("second", now + timedelta(days=1))

    query = mock.Mock()
    query.filter.return_value.all.return_value = [first, second]
    query.join.return_value.filter.return_value.with_for_update.return_value.one_or_none.side_effect = [first, second]
    session = mock.Mock()
    session.query.return_value = query
    enter_session.return_value.__enter__.return_value = session

    rcon = mock.Mock()
    rcon.get_vip_ids.return_value = []
    rcon.without_retries.side_effect = nullcontext
    rcon.add_vip.side_effect = [RuntimeError("temporary failure"), True]

    assert restore_missing_vips(rcon) == 1
    assert rcon.add_vip.call_count == 2


@mock.patch("rcon.vip_rewards.locking.vip_lock", side_effect=lambda _: nullcontext())
@mock.patch("rcon.expiring_vips.service.get_server_number", return_value="3")
@mock.patch("rcon.expiring_vips.service.enter_session")
def test_removed_or_expired_vip_is_not_recreated(enter_session, _server, _lock):
    active = _vip("removed", datetime.now(timezone.utc) + timedelta(days=1))
    also_active = _vip("expired", datetime.now(timezone.utc) + timedelta(days=1))
    expired_now = _vip("expired", datetime.now(timezone.utc) - timedelta(seconds=1))
    session = enter_session.return_value.__enter__.return_value
    query = session.query.return_value
    query.filter.return_value.all.return_value = [active, also_active]
    query.join.return_value.filter.return_value.with_for_update.return_value.one_or_none.side_effect = [None, expired_now]
    rcon = mock.Mock()
    rcon.get_vip_ids.return_value = []
    assert restore_missing_vips(rcon) == 0
    rcon.add_vip.assert_not_called()


@mock.patch("rcon.vip_rewards.locking.vip_lock", side_effect=lambda _: nullcontext())
@mock.patch("rcon.expiring_vips.service.get_server_number", return_value="3")
@mock.patch("rcon.expiring_vips.service.enter_session")
def test_rechecks_extension_and_counts_only_confirmation(enter_session, _server, _lock):
    initial = _vip("player", datetime.now(timezone.utc) + timedelta(days=1))
    extended = _vip("player", datetime.now(timezone.utc) + timedelta(days=10))
    query = enter_session.return_value.__enter__.return_value.query.return_value
    query.filter.return_value.all.return_value = [initial]
    query.join.return_value.filter.return_value.with_for_update.return_value.one_or_none.return_value = extended
    rcon = mock.Mock()
    rcon.get_vip_ids.return_value = []
    rcon.without_retries.return_value = nullcontext()
    rcon.add_vip.return_value = False
    assert restore_missing_vips(rcon) == 0
    assert rcon.add_vip.call_args.kwargs['expiration'] == extended.expiration.isoformat()


@mock.patch("rcon.vip_rewards.locking.vip_lock", side_effect=lambda _: nullcontext())
@mock.patch("rcon.expiring_vips.service.get_server_number", return_value="3")
@mock.patch("rcon.expiring_vips.service.enter_session")
def test_fresh_game_snapshot_prevents_duplicate_add(enter_session, _server, _lock):
    active = _vip("player", datetime.now(timezone.utc) + timedelta(days=1))
    query = enter_session.return_value.__enter__.return_value.query.return_value
    query.filter.return_value.all.return_value = [active]
    query.join.return_value.filter.return_value.with_for_update.return_value.one_or_none.return_value = active
    rcon = mock.Mock()
    rcon.get_vip_ids.side_effect = [[], [{"player_id": "player"}]]
    assert restore_missing_vips(rcon) == 0
    rcon.add_vip.assert_not_called()
