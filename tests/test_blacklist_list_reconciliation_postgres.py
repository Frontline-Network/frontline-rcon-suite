"""List mutation through the outbox, with PostgreSQL and a simulated game server."""
from contextlib import nullcontext
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from rcon import blacklist, blacklist_sync_journal as journal
from rcon.models import BlacklistRecord, PlayerID
from rcon.types import BlacklistSyncMethod, GameEnum
from tests.test_blacklist_sync_journal_postgres import database, existing_blacklist


EOS = "abcdef0123456789abcdef0123456789"


@pytest.fixture
def receiver(monkeypatch):
    monkeypatch.setattr(blacklist, "SERVER_NUMBER", 3)
    monkeypatch.setattr(blacklist, "send_to_discord_audit", Mock())
    handler = blacklist.BlacklistCommandHandler.__new__(blacklist.BlacklistCommandHandler)
    ctl = handler.rcon = Mock()
    ctl.game_profile = SimpleNamespace(game=GameEnum.HLL_VIETNAM)
    ctl.without_retries.side_effect = nullcontext
    ctl.get_temp_bans.return_value = []
    ctl.get_perma_bans.return_value = []
    ctl.get_detailed_player_info.return_value = {"name": "Fixture"}
    return handler


def deliver(handler, ready=True):
    return journal.process_one(3, handler.dispatch, is_ready=lambda: ready,
                               game=GameEnum.HLL_VIETNAM, prepare=handler._prepare_delivery)


@pytest.mark.parametrize("operation", ["delete", "remove_server", "switch_to_kick"])
@pytest.mark.parametrize("temporary", [True, False])
@pytest.mark.parametrize("live", ["later_manual", "older_manual", "ours", "absent"])
def test_list_removal_preserves_independent_ban(database, existing_blacklist, receiver, operation, temporary, live):
    record_id, list_id, _ = existing_blacklist
    with database.begin() as db:
        record = db.get(BlacklistRecord, record_id)
        record.player.player_id = EOS
        record.blacklist.servers = 4
        record.blacklist.sync = BlacklistSyncMethod.BAN_ON_CONNECT
        if temporary:
            record.expires_at = datetime.now(timezone.utc) + timedelta(days=1)
        owner = blacklist._blacklist_ban_actor(record)

    if operation == "delete":
        assert blacklist.delete_blacklist(list_id)
    elif operation == "remove_server":
        blacklist.edit_blacklist(list_id, servers=[4])
    else:
        blacklist.edit_blacklist(list_id, sync=BlacklistSyncMethod.KICK_ONLY)
    assert deliver(receiver, ready=False) == "deferred"
    with database() as db:
        row = db.scalar(select(journal.BlacklistSyncDelivery).where(journal.BlacklistSyncDelivery.server_number == 3))
        reference = row.created_at
    ctl = receiver.rcon
    if live != "absent":
        stamp = reference + timedelta(seconds=5 if live == "later_manual" else -5)
        reader = ctl.get_temp_bans if temporary else ctl.get_perma_bans
        reader.return_value = [{"player_id": EOS.upper(), "ban_time": stamp.isoformat(),
                                "by": owner if live == "ours" else "Moderator"}]
    ctl.remove_temp_ban.return_value = ctl.remove_perma_ban.return_value = True
    assert deliver(receiver) == ("review" if live == "older_manual" else "done")
    if live == "ours":
        remove = ctl.remove_temp_ban if temporary else ctl.remove_perma_ban
        remove.assert_called_once_with(EOS.upper())
    assert ctl.remove_temp_ban.call_count + ctl.remove_perma_ban.call_count == int(live == "ours")
    ctl.perma_ban.assert_not_called()
    ctl.temp_ban.assert_not_called()
    if live == "later_manual":
        with database() as db:
            row = db.scalar(select(journal.BlacklistSyncDelivery).where(journal.BlacklistSyncDelivery.server_number == 3))
            assert row.reason == "Newer game ban preserved"


@pytest.mark.parametrize("alias", [False, True])
@pytest.mark.parametrize("second_wins", [False, True])
def test_list_activation_applies_winner_once(database, existing_blacklist, receiver, alias, second_wins):
    record_id, list_id, unrelated = existing_blacklist
    with database.begin() as db:
        first = db.get(BlacklistRecord, record_id)
        first.player.player_id = EOS
        first.blacklist.servers = 8
        other_player = first.player
        if alias:
            other_player = PlayerID(player_id=EOS.upper())
            db.add(other_player)
            db.flush()
        second = BlacklistRecord(player_id_id=other_player.id, blacklist_id=list_id, reason="Second",
                                 admin_name="Other", created_at=first.created_at + timedelta(minutes=1 if second_wins else -1))
        db.add(second)
        db.flush()
        winner = second if second_wins else first
        owner = blacklist._blacklist_ban_actor(winner)
        target = winner.player.player_id

    blacklist.edit_blacklist(list_id, servers=[4, 3])
    ctl = receiver.rcon
    ctl.perma_ban.side_effect = [True, False]
    assert deliver(receiver) == "done"
    ctl.perma_ban.assert_called_once()
    assert ctl.perma_ban.call_args.kwargs["by"] == owner
    assert ctl.perma_ban.call_args.kwargs["player_id"] == target
    blacklist.edit_blacklist(unrelated, servers=[3])
    assert deliver(receiver) == "done"
    assert deliver(receiver) == "empty"
    ctl.perma_ban.assert_called_once()


@pytest.mark.parametrize("operation", ["delete", "edit"])
def test_old_payload_cannot_remove_existing_ban(database, existing_blacklist, receiver, operation):
    record_id, list_id, _ = existing_blacklist
    with database.begin() as db:
        record = db.get(BlacklistRecord, record_id)
        record.player.player_id = EOS
        record.blacklist.servers = 4
        owner = blacklist._blacklist_ban_actor(record)
    if operation == "delete":
        blacklist.delete_blacklist(list_id)
    else:
        blacklist.edit_blacklist(list_id, servers=[4])
    with database.begin() as db:
        row = db.scalar(select(journal.BlacklistSyncDelivery).where(journal.BlacklistSyncDelivery.server_number == 3))
        command = blacklist.BlacklistCommand.decode(row.command)
        command.payload.pop("requested_at")
        command.payload.pop("record_ids", None)
        row.command = command.encode()
        stamp = (row.created_at - timedelta(seconds=10)).isoformat()
    ctl = receiver.rcon
    ctl.get_perma_bans.return_value = [{"player_id": EOS, "ban_time": stamp, "by": owner}]
    assert deliver(receiver) == "review"
    assert deliver(receiver) == "review"
    ctl.remove_perma_ban.assert_not_called()
    ctl.perma_ban.assert_not_called()


@pytest.mark.parametrize("operation", ["delete", "edit"])
def test_replaces_owned_ban_with_other_lists_record(database, existing_blacklist, receiver, operation):
    record_id, list_id, other_id = existing_blacklist
    with database.begin() as db:
        record = db.get(BlacklistRecord, record_id)
        record.player.player_id = EOS
        record.blacklist.servers = 4
        owner = blacklist._blacklist_ban_actor(record)
        other_player = PlayerID(player_id=EOS.upper())
        db.add(other_player)
        db.flush()
        other = BlacklistRecord(player_id_id=other_player.id, blacklist_id=other_id, reason="Remaining",
                                admin_name="Another", created_at=record.created_at - timedelta(days=1))
        db.add(other)
        db.flush()
        other.blacklist.servers = 4
        remaining_owner = blacklist._blacklist_ban_actor(other)
    if operation == "delete":
        blacklist.delete_blacklist(list_id)
    else:
        blacklist.edit_blacklist(list_id, servers=[4])
    ctl = receiver.rcon
    earlier = (datetime.now(timezone.utc) - timedelta(seconds=10)).isoformat()
    ctl.get_perma_bans.return_value = [{"player_id": EOS, "ban_time": earlier, "by": owner}]
    ctl.remove_perma_ban.return_value = True
    ctl.perma_ban.return_value = True
    assert deliver(receiver) == "done"
    ctl.remove_perma_ban.assert_called_once_with(EOS)
    ctl.perma_ban.assert_called_once()
    assert ctl.perma_ban.call_args.kwargs["by"] == remaining_owner
    assert deliver(receiver) == "empty"
