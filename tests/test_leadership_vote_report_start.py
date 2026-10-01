"""Report-triggered invitations; no real network, players, messages or kicks."""

import pytest
from sqlalchemy import select

from rcon.leadership_vote import service, storage
from rcon.models import LeadershipMessage, LeadershipPresence
from tests.test_leadership_vote import (
    cast,
    context,
    db,
    deliver,
    elapse,
    observe_for,
    player,
    report,
    roster,
    transport,
    vote,
)


@pytest.mark.parametrize("commander", [False, True])
def test_delayed_discord_ack_starts_without_reporter_answer(db, monkeypatch, commander):
    players = roster(commander=commander)
    observe_for(db, players)
    incident = report(players, "!admin commander" if commander else "!admin able")
    vid = incident["leadership_vote"]["id"]
    monkeypatch.setattr(storage, "report_delivered", lambda *_: False)
    api = deliver(db, players)
    assert not cast(db, players)  # No ballot accepted before invitation.
    api.message_player.assert_not_called()
    with db() as sess:
        queued = list(sess.scalars(select(LeadershipMessage)))
        assert len(queued) == 6 and all(m.status == "pending" for m in queued)
        assert not any(m.purpose == "confirm" for m in queued)
    elapse(db, players, 100)
    assert storage.advance(1, context(players)) == []
    monkeypatch.setattr(storage, "report_delivered", lambda *_: True)
    deliver(db, players, api)
    storage.advance(1, context(players))
    current = vote(db, vid)
    assert current["status"] == "active"
    assert current["ends_at"] == db.clock.now + 120
    assert current["yes"] == current["no"] == 0
    assert api.message_player.call_count == 12
    assert {c.args[0] for c in api.message_player.call_args_list} == {
        f"v{i}" for i in range(6)
    }
    assert cast(db, players, "v0")
    assert vote(db, vid)["yes"] == 1  # First !yes is a ballot, never another gate.
    api.kick.assert_not_called()


def test_frozen_at_report_new_leader_never_gets_invited(db, monkeypatch):
    players = roster()
    observe_for(db, players)
    incident = report(players)
    players.append(player("late", squad="New"))
    storage.observe(1, context(players))
    api = deliver(db, players)
    current = vote(db, incident["leadership_vote"]["id"])
    assert current["participant_count"] == 6 and current["required"] == 4
    assert "late" not in current["electorate"]
    assert all(c.args[0] != "late" for c in api.message_player.call_args_list)


def test_unacknowledged_team_does_not_block_other_team(db, monkeypatch):
    players = roster() + [
        player("axis-target", squad="Able", team="axis"),
        *[player(f"a{i}", squad=f"Axis-{i}", team="axis") for i in range(3)],
    ]
    observe_for(db, players)
    first = report(players)
    second = report(players, reporter="a0")
    assert second["leadership_vote"]["target_id"] == "axis-target"
    monkeypatch.setattr(
        storage,
        "report_delivered",
        lambda sess, v: v.id != first["leadership_vote"]["id"],
    )
    api = deliver(db, players)
    assert api.message_player.call_count == 6
    assert {c.args[0] for c in api.message_player.call_args_list} == {"a0", "a1", "a2"}


def test_admin_takeover_while_waiting_for_discord_stops_all_invitations(
    db, monkeypatch
):
    players = roster()
    observe_for(db, players)
    incident = report(players)
    monkeypatch.setattr(storage, "report_delivered", lambda *_: False)
    api = deliver(db, players)
    storage.cancel(1, incident["leadership_vote"]["id"], "admin")
    monkeypatch.setattr(storage, "report_delivered", lambda *_: True)
    deliver(db, players, api)
    assert all(
        "LEADERSHIP VOTE" not in c.args[1] for c in api.message_player.call_args_list
    )
    with db() as sess:
        invitations = list(
            sess.scalars(
                select(LeadershipMessage).where(
                    LeadershipMessage.purpose.in_({"invite", "invite_de"})
                )
            )
        )
        assert all(m.status == "cancelled" for m in invitations)
    api.kick.assert_not_called()


def test_invitation_quotes_reason_without_claiming_voice_evidence(db):
    players = roster()
    observe_for(db, players)
    report(players, "!admin able teamkills")
    api = deliver(db, players)
    assert all("teamkills" in c.args[1] for c in api.message_player.call_args_list)
    assert all(
        "not communicating" not in c.args[1] for c in api.message_player.call_args_list
    )


@pytest.mark.parametrize("change", ["stale_target", "old_round"])
def test_direct_start_rejects_invalid_target_observation(db, change):
    players = roster()
    observe_for(db, players)
    with db() as sess:
        record = sess.scalar(
            select(LeadershipPresence).where(LeadershipPresence.player_id == "target")
        )
        record.payload = dict(
            record.payload,
            **(
                {"seen_at": db.clock.now - 20}
                if change == "stale_target"
                else {"round_id": "previous-round"}
            ),
        )
    assert not report(players)["leadership_vote"]
    api = deliver(db, players)
    api.message_player.assert_not_called()
