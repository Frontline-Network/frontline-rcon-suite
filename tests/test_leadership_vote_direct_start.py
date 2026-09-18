"""No-warning flow, private recipients and backwards-compatible safety gates."""

from copy import deepcopy

import pytest
from sqlalchemy import select

from tests.test_leadership_vote import (
    activate,
    cast,
    confirm,
    context,
    db,
    deliver,
    elapse,
    observe_for,
    report,
    roster,
    transport,
    vote,
)
from rcon.leadership_vote import service, storage
from rcon.models import LeadershipMessage, LeadershipVote
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config


@pytest.mark.parametrize("commander", [False, True])
@pytest.mark.parametrize("warning_seconds", [30, 60, 180])
def test_confirmation_immediately_queues_leaders_without_target_or_wait(
    db, commander, warning_seconds
):
    storage.configure(
        1,
        Config(enabled=True, confirmation_seconds=120, warning_seconds=warning_seconds),
        "tester",
    )
    players = roster(commander=commander)
    observe_for(db, players)
    incident = report(players, "!admin commander" if commander else "!admin able")
    vid = confirm(db, players, incident, deliver_invitations=False)
    current = vote(db, vid)
    assert current["status"] == "inviting"
    assert current["confirmed_at"] == current["started_at"] == db.clock.now
    assert current["yes"] == current["no"] == 0
    with db() as sess:
        pending = list(
            sess.scalars(
                select(LeadershipMessage).where(LeadershipMessage.status == "pending")
            )
        )
        assert {m.player_id for m in pending} == {f"v{i}" for i in range(6)}
        assert all(
            m.purpose == "invite_de" and m.created_at == db.clock.now for m in pending
        )
    api = deliver(db, players)
    assert len(api.message_player.call_args_list) == 12
    assert all(c.args[0].startswith("v") for c in api.message_player.call_args_list)
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "active"
    assert vote(db, vid)["ends_at"] == db.clock.now + 120


@pytest.mark.parametrize("commander", [False, True])
@pytest.mark.parametrize("result", ["rejected", "dry_run", "cancelled", "kicked"])
def test_target_never_receives_private_result_even_with_legacy_receipt(
    db, monkeypatch, commander, result
):
    vid, players = activate(
        db, commander=commander, mode="active" if result == "kicked" else "dry_run"
    )
    with db() as sess:
        v = sess.get(LeadershipVote, vid)
        v.payload = dict(v.payload, target_notified=True)
    api = transport()
    if result == "cancelled":
        storage.cancel(1, vid, "admin")
    else:
        if result != "rejected":
            for i in range(4):
                assert cast(db, players, f"v{i}")
        elapse(db, players, 120)
        actions = storage.advance(1, context(players))
        if result == "kicked":
            assert len(actions) == 1
            monkeypatch.setattr(service, "read_context", lambda _: context(players))
            service.execute(api, 1, actions[0])
            api.kick.assert_called_once()
        else:
            assert actions == []
            api.kick.assert_not_called()
    deliver(db, players, api)
    assert vote(db, vid)["status"] == result
    assert {c.args[0] for c in api.message_player.call_args_list} == {
        f"v{i}" for i in range(6)
    }
    with db() as sess:
        assert not list(
            sess.scalars(
                select(LeadershipMessage).where(LeadershipMessage.player_id == "target")
            )
        )


@pytest.mark.parametrize(
    "purpose",
    ["confirm", "target", "warning", "invite_de", "invite", "ballot", "result"],
)
def test_enqueue_and_dispatch_both_block_target_including_legacy_rows(db, purpose):
    vid, players = activate(db)
    with db() as sess:
        v = sess.get(LeadershipVote, vid)
        storage.notify(sess, 1, "target", "must not send", db.clock.now, v, purpose)
        sess.flush()
        assert not list(
            sess.scalars(
                select(LeadershipMessage).where(LeadershipMessage.player_id == "target")
            )
        )
        # Simulate a durable row written by an older process/version.
        item = LeadershipMessage(
            server_number=1,
            vote_id=vid,
            player_id="target",
            purpose=purpose,
            body="legacy",
            status="pending",
            created_at=db.clock.now,
        )
        sess.add(item)
        sess.flush()
        message_id = item.id
    api = deliver(db, players)
    api.message_player.assert_not_called()
    with db() as sess:
        assert sess.get(LeadershipMessage, message_id).status == "cancelled"


def test_legacy_warning_phase_is_cancelled_without_target_notice(db):
    vid, players = activate(db)
    with db() as sess:
        v = sess.get(LeadershipVote, vid)
        v.status = "warning"
        v.payload = dict(
            v.payload, warning_started_at=db.clock.now, target_notified=True
        )
    assert storage.advance(1, context(players)) == []
    assert vote(db, vid)["status"] == "cancelled"
    api = deliver(db, players)
    assert all(c.args[0] != "target" for c in api.message_player.call_args_list)


@pytest.mark.parametrize("legacy", [False, True])
def test_team_and_target_cooldowns_apply_after_confirmation(db, legacy):
    players = roster()
    observe_for(db, players)
    vid = confirm(db, players, report(players))
    if legacy:
        with db() as sess:
            v = sess.get(LeadershipVote, vid)
            p = deepcopy(v.payload)
            p["warning_started_at"] = p.pop("confirmed_at")
            v.payload = p
    storage.cancel(1, vid, "admin")
    assert not report(players)["leadership_vote"]
    # Team cooldown passes, same-player protection must still apply.
    elapse(db, players, 601)
    assert not report(players)["leadership_vote"]
    elapse(db, players, 1200)
    assert report(players)["leadership_vote"]
