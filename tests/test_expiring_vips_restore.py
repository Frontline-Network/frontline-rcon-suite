from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest import mock

from rcon.expiring_vips.service import restore_missing_vips


def _vip(player_id, expiration, name="Player"):
    return SimpleNamespace(
        expiration=expiration,
        player=SimpleNamespace(
            player_id=player_id,
            names=[SimpleNamespace(name=name)],
        ),
    )


@mock.patch("rcon.expiring_vips.service.get_server_number", return_value="3")
@mock.patch("rcon.expiring_vips.service.enter_session")
def test_restore_missing_vips_only_adds_active_missing_records(
    enter_session, _get_server_number
):
    now = datetime.now(timezone.utc)
    active_existing = _vip("existing", now + timedelta(days=1))
    active_missing = _vip("missing", now + timedelta(days=2), "Missing Player")

    query = mock.Mock()
    query.filter.return_value.all.return_value = [active_existing, active_missing]
    session = mock.Mock()
    session.query.return_value = query
    enter_session.return_value.__enter__.return_value = session

    rcon = mock.Mock()
    rcon.get_vip_ids.return_value = [{"player_id": "existing"}]

    assert restore_missing_vips(rcon) == 1
    rcon.add_vip.assert_called_once_with(
        player_id="missing",
        description="Missing Player",
        expiration=active_missing.expiration.isoformat(),
    )


@mock.patch("rcon.expiring_vips.service.get_server_number", return_value="3")
@mock.patch("rcon.expiring_vips.service.enter_session")
def test_restore_missing_vips_keeps_going_after_one_rcon_failure(
    enter_session, _get_server_number
):
    now = datetime.now(timezone.utc)
    first = _vip("first", now + timedelta(days=1))
    second = _vip("second", now + timedelta(days=1))

    query = mock.Mock()
    query.filter.return_value.all.return_value = [first, second]
    session = mock.Mock()
    session.query.return_value = query
    enter_session.return_value.__enter__.return_value = session

    rcon = mock.Mock()
    rcon.get_vip_ids.return_value = []
    rcon.add_vip.side_effect = [RuntimeError("temporary failure"), True]

    assert restore_missing_vips(rcon) == 1
    assert rcon.add_vip.call_count == 2
