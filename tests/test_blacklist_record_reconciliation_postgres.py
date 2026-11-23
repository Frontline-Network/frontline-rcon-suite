"""Individual record changes reconciled through the durable journal on PostgreSQL."""
from datetime import datetime, timedelta, timezone

import pytest
from sqlalchemy import select

from rcon import blacklist
from rcon import blacklist_sync_journal as journal
from rcon.models import BlacklistRecord, PlayerID
from rcon.types import BlacklistSyncMethod, GameEnum
from tests.test_blacklist_sync_journal_postgres import database, existing_blacklist
from tests.test_blacklist_list_reconciliation_postgres import EOS, deliver, receiver


def setup_record(db, record_id, *, temporary=False):
    record = db.get(BlacklistRecord, record_id)
    record.created_at -= timedelta(minutes=30)
    record.player.player_id = EOS
    record.blacklist.servers = 4
    if temporary:
        record.expires_at = datetime.now(timezone.utc) + timedelta(hours=4, minutes=30)
    return record


def orders():
    return select(journal.BlacklistSyncDelivery).where(
        journal.BlacklistSyncDelivery.server_number == 3
    ).order_by(journal.BlacklistSyncDelivery.id)


@pytest.mark.parametrize("temporary", [True, False])
@pytest.mark.parametrize("operation", ["expire", "move_server", "delete"])
def test_delayed_change_preserves_later_manual_ban(database, existing_blacklist, receiver, temporary, operation):
    record_id, _, other_list = existing_blacklist
    with database.begin() as db:
        setup_record(db, record_id, temporary=temporary)
    if operation == "expire":
        blacklist.edit_record_from_blacklist(record_id, expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    elif operation == "move_server":
        blacklist.edit_record_from_blacklist(record_id, blacklist_id=other_list)
    else:
        blacklist.remove_record_from_blacklist(record_id)
    assert deliver(receiver, ready=False) == "deferred"
    with database() as db:
        stamp = db.scalars(orders()).one().created_at + timedelta(seconds=5)
    ctl = receiver.rcon
    reader = ctl.get_temp_bans if temporary else ctl.get_perma_bans
    reader.return_value = [{"player_id": EOS, "by": "Moderator", "ban_time": stamp.isoformat()}]
    assert deliver(receiver) == "done"
    assert deliver(receiver) == "empty"
    ctl.remove_temp_ban.assert_not_called()
    ctl.remove_perma_ban.assert_not_called()
    with database() as db:
        assert db.scalars(orders()).one().reason == "Newer game ban preserved"


@pytest.mark.parametrize("owner", ["ours", "absent", "manual"])
@pytest.mark.parametrize("delta", [-2, 5])
def test_adjust_verified_temporary_ban(database, existing_blacklist, receiver, owner, delta):
    record_id, _, unrelated = existing_blacklist
    with database.begin() as db:
        record = setup_record(db, record_id, temporary=True)
        actor = blacklist._blacklist_ban_actor(record)
        stamp = record.created_at + timedelta(minutes=1)
        expires = record.expires_at + timedelta(hours=delta)
    blacklist.edit_record_from_blacklist(record_id, expires_at=expires)
    ctl = receiver.rcon
    live = {}
    if owner != "absent":
        live[EOS] = {"player_id": EOS, "by": actor if owner == "ours" else "Moderator", "ban_time": stamp.isoformat()}
    ctl.get_temp_bans.side_effect = lambda: list(live.values())
    ctl.remove_temp_ban.side_effect = lambda pid: live.pop(pid, None) is not None
    ctl.temp_ban.return_value = True
    result = deliver(receiver)
    blacklist.edit_blacklist(unrelated, servers=[3])
    if owner == "manual":
        assert result == deliver(receiver) == "review"
        ctl.remove_temp_ban.assert_not_called()
        ctl.temp_ban.assert_not_called()
        with database() as db:
            assert [row.status for row in db.scalars(orders())] == ["review", "queued"]
    else:
        assert result == deliver(receiver) == "done"
        assert deliver(receiver) == "empty"
        assert ctl.remove_temp_ban.call_count == int(owner == "ours")
        ctl.temp_ban.assert_called_once()
        assert ctl.temp_ban.call_args.kwargs["duration_hours"] == 4 + delta
        assert ctl.temp_ban.call_args.kwargs["by"] == actor


@pytest.mark.parametrize("same_time", [False, True])
@pytest.mark.parametrize("removed_id, remaining_id", [(EOS, EOS), (EOS, EOS.upper()), (EOS.upper(), EOS)])
def test_delete_uses_remaining_vietnam_record(database, existing_blacklist, receiver, removed_id, remaining_id, same_time):
    record_id, _, other_list = existing_blacklist
    with database.begin() as db:
        record = setup_record(db, record_id)
        record.player.player_id = removed_id
        account = record.player
        if remaining_id != removed_id:
            account = PlayerID(player_id=remaining_id)
            db.add(account)
            db.flush()
        other = BlacklistRecord(player_id_id=account.id, blacklist_id=other_list, reason="Remaining", admin_name="Fixture",
                                created_at=record.created_at if same_time else record.created_at - timedelta(minutes=1))
        db.add(other)
        db.flush()
        other.blacklist.servers = 4
        actor = blacklist._blacklist_ban_actor(record)
        remaining_actor = blacklist._blacklist_ban_actor(other)
        stamp = record.created_at + timedelta(minutes=1)
    blacklist.remove_record_from_blacklist(record_id)
    ctl = receiver.rcon
    ctl.get_perma_bans.return_value = [{"player_id": removed_id, "by": actor, "ban_time": stamp.isoformat()}]
    ctl.remove_perma_ban.return_value = ctl.perma_ban.return_value = True
    assert deliver(receiver) == "done"
    ctl.remove_perma_ban.assert_called_once_with(removed_id)
    ctl.perma_ban.assert_called_once()
    assert ctl.perma_ban.call_args.kwargs["by"] == remaining_actor
    assert ctl.perma_ban.call_args.kwargs["player_id"] == EOS
    assert deliver(receiver) == "empty"


@pytest.mark.parametrize("result", ["accepted", "removal_rejected", "replacement_rejected", "legacy"])
def test_offline_active_temp_ban_update(database, existing_blacklist, receiver, result):
    record_id, _, _ = existing_blacklist
    with database.begin() as db:
        record = setup_record(db, record_id, temporary=True)
        record.blacklist.sync = BlacklistSyncMethod.BAN_ON_CONNECT
        actor = blacklist._blacklist_ban_actor(record)
        stamp = record.created_at + timedelta(minutes=1)
        expires = record.expires_at + timedelta(hours=2)
    blacklist.edit_record_from_blacklist(record_id, expires_at=expires)
    if result == "legacy":
        with database.begin() as db:
            row = db.scalars(orders()).one()
            command = blacklist.BlacklistCommand.decode(row.command)
            del command.payload["requested_at"]
            row.command = command.encode()
    ctl = receiver.rcon
    live = {EOS: {"player_id": EOS, "by": actor, "ban_time": stamp.isoformat()}}
    ctl.get_temp_bans.side_effect = lambda: list(live.values())
    ctl.get_detailed_player_info.side_effect = blacklist.HLLCommandFailedError("offline")
    def remove(pid):
        return result != "removal_rejected" and live.pop(pid, None) is not None
    ctl.remove_temp_ban.side_effect = remove
    ctl.temp_ban.return_value = result == "accepted"
    expected = "done" if result == "accepted" else "review"
    assert deliver(receiver) == expected
    assert deliver(receiver) == ("empty" if result == "accepted" else "review")
    assert ctl.remove_temp_ban.call_count == int(result != "legacy")
    assert ctl.temp_ban.call_count == int(result in ("accepted", "replacement_rejected"))


@pytest.mark.parametrize("vietnam", [True, False])
def test_record_edit_respects_game_identity_for_pending_action(database, existing_blacklist, receiver, vietnam):
    record_id, _, _ = existing_blacklist
    with database.begin() as db:
        record = setup_record(db, record_id)
        actor = blacklist._blacklist_ban_actor(record)
        stamp = record.created_at + timedelta(minutes=1)
    if not vietnam:
        receiver.rcon.game_profile.game = GameEnum.HLL_WW2
    token = blacklist.action_guard.reserve(3, EOS.upper(), [blacklist.BLACKLIST_ACTION_GUARD_RULE], "ban")
    assert token is not None
    blacklist.edit_record_from_blacklist(record_id, expires_at=datetime.now(timezone.utc) - timedelta(minutes=1))
    ctl = receiver.rcon
    ctl.get_perma_bans.return_value = [{"player_id": EOS, "by": actor, "ban_time": stamp.isoformat()}]
    ctl.remove_perma_ban.return_value = True
    assert deliver(receiver) == ("review" if vietnam else "done")
    assert ctl.remove_perma_ban.call_count == int(not vietnam)
