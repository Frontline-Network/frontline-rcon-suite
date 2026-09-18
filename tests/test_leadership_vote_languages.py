"""Separate private invitations, using only synthetic players and mocked RCON."""

from collections import defaultdict

import pytest
from sqlalchemy import select

from tests.test_leadership_vote import (
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
from rcon.leadership_vote import domain, service, storage
from rcon.models import LeadershipMessage


def queued(db, commander=False):
    players = roster(commander=commander)
    observe_for(db, players)
    incident = report(players, "!admin commander" if commander else "!admin able")
    vid = confirm(db, players, incident)
    elapse(db, players, 60)
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "inviting"
    # German-only pending rows must keep the delivery phase open.
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "inviting"
    return vid, players, transport()


def language(body):
    return "de" if "FÜHRUNGSABSTIMMUNG" in body else "en"


@pytest.mark.parametrize("commander", [False, True])
def test_each_eligible_leader_gets_german_then_english_once(db, commander):
    vid, players, api = queued(db, commander)
    deliver(db, players, api)
    deliver(db, players, api)
    recipients = defaultdict(list)
    for call in api.message_player.call_args_list:
        pid, body = call.args
        recipients[pid].append(language(body))
    assert dict(recipients) == {f"v{i}": ["de", "en"] for i in range(6)}
    with db() as sess:
        rows = list(
            sess.scalars(
                select(LeadershipMessage).where(
                    LeadershipMessage.vote_id == vid,
                    LeadershipMessage.purpose.in_(domain.INVITATIONS),
                )
            )
        )
    assert len(rows) == 12
    assert all(row.status == "sent" for row in rows)
    storage.advance(1, context(players))
    current = vote(db, vid)
    assert current["status"] == "active"
    assert current["participant_count"] == 6 and current["required"] == 4
    assert current["yes"] == 0 and current["no"] == 0
    api.kick.assert_not_called()


@pytest.mark.parametrize(
    "de,en",
    [
        (True, True),
        (True, False),
        (False, True),
        (False, False),
        ("timeout", True),
        (True, "timeout"),
    ],
)
def test_language_failure_never_retries_or_counts_a_person_twice(db, de, en):
    vid, players, api = queued(db)
    attempts = defaultdict(list)

    def send(pid, body):
        lang = language(body)
        attempts[pid].append(lang)
        result = de if lang == "de" else en
        if result == "timeout":
            raise TimeoutError("Synthetic uncertain delivery")
        return result

    api.message_player.side_effect = send
    deliver(db, players, api)
    deliver(db, players, api)
    assert dict(attempts) == {f"v{i}": ["de", "en"] for i in range(6)}
    storage.advance(1, context(players))
    current = vote(db, vid)
    assert current["required"] == 4
    assert current["status"] == ("active" if de is True or en is True else "cancelled")
    assert sum(m["invited_at"] is not None for m in current["electorate"].values()) == (
        6 if de is True or en is True else 0
    )
    api.kick.assert_not_called()


def first_german_for_reporter(db, players, api):
    for _ in range(100):
        assert service.dispatch_one(api, 1, context(players))
        pid, body = api.message_player.call_args.args
        if pid == "v0" and language(body) == "de":
            return
    pytest.fail("No German invitation for reporter")


def test_ballot_after_german_survives_english_and_gets_full_duration(db):
    vid, players, api = queued(db)
    first_german_for_reporter(db, players, api)
    first_delivery = vote(db, vid)["electorate"]["v0"]["invited_at"]
    assert cast(db, players, "v0")
    elapse(db, players, 3)
    deliver(db, players, api)
    storage.advance(1, context(players))
    current = vote(db, vid)
    assert current["status"] == "active" and current["yes"] == 1
    assert current["electorate"]["v0"]["invited_at"] == first_delivery
    assert current["electorate"]["v0"]["last_invited_at"] > first_delivery
    assert current["ends_at"] == db.clock.now + 120
    assert len(current["ballots"]) == 1


@pytest.mark.parametrize("change", ["admin", "restart", "team", "role"])
def test_pending_english_keeps_takeover_restart_and_identity_guards(db, change):
    vid, players, api = queued(db)
    first_german_for_reporter(db, players, api)
    if change == "admin":
        storage.cancel(1, vid, "admin")
    elif change == "restart":
        storage.recover(1)
    else:
        reporter = next(p for p in players if p["player_id"] == "v0")
        reporter["team" if change == "team" else "role"] = (
            "axis" if change == "team" else "Rifleman"
        )
        storage.observe(1, context(players))
    api.message_player.reset_mock()
    deliver(db, players, api)
    assert not any(
        c.args[0] == "v0" and "LEADERSHIP VOTE" in c.args[1]
        for c in api.message_player.call_args_list
    )
    api.kick.assert_not_called()


def test_receipt_failure_does_not_duplicate_first_language_or_enqueue_followup(
    db, monkeypatch
):
    vid, players, api = queued(db)
    with monkeypatch.context() as patch:

        def fail(*args, **kwargs):
            raise RuntimeError("Synthetic DB failure")

        patch.setattr(storage, "notify", fail)
        with pytest.raises(RuntimeError, match="Synthetic DB failure"):
            service.dispatch_one(api, 1, context(players))
    assert api.message_player.call_count == 1
    with db() as sess:
        assert not list(
            sess.scalars(
                select(LeadershipMessage).where(
                    LeadershipMessage.vote_id == vid,
                    LeadershipMessage.purpose == "invite",
                )
            )
        )
    storage.recover(1)
    api.message_player.reset_mock()
    deliver(db, players, api)
    assert not any(
        "FÜHRUNGSABSTIMMUNG" in c.args[1] or "LEADERSHIP VOTE" in c.args[1]
        for c in api.message_player.call_args_list
    )
    assert vote(db, vid)["status"] == "cancelled"


@pytest.mark.parametrize("commander", [False, True])
def test_german_invitation_has_commands_deadline_majority_and_dry_run(db, commander):
    vid, players, api = queued(db, commander)
    deliver(db, players, api)
    texts = [
        c.args[1]
        for c in api.message_player.call_args_list
        if language(c.args[1]) == "de"
    ]
    assert len(texts) == 6
    assert all("PROBELAUF — kein automatischer Kick" in t for t in texts)
    assert all("!yes = Für den Kick\n!no = Gegen den Kick" in t for t in texts)
    assert all("120 Sekunden" in t and "4 Ja-Stimmen bei 6" in t for t in texts)
    assert all("Person-target" in t and "TEAM- oder SQUADCHAT" in t for t in texts)
    assert all(
        ("Commander Person-target" if commander else "Squad Able") in t for t in texts
    )
