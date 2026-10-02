"""Reporting and voting are separate permissions; all game actions are mocked."""

from copy import deepcopy

import pytest

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
    squads,
    vote,
)
from rcon import admin_incidents as incidents
from rcon.leadership_vote import domain, service, storage
from rcon.models import LeadershipVote
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config


@pytest.mark.parametrize("commander", [False, True])
@pytest.mark.parametrize("own_squad", [False, True])
@pytest.mark.parametrize("mode", ["dry_run", "active"])
@pytest.mark.parametrize(
    "roles",
    [
        ("Officer", "Commander", "Rifleman"),
        ("squadleader", "armycommander", "rifleman"),
    ],
    ids=["hll", "hllv"],
)
def test_member_report_invites_only_leaders_and_completes_vote(
    db, monkeypatch, commander, own_squad, mode, roles
):
    storage.configure(1, Config(enabled=True, mode=mode), "tester")
    players = roster(3, commander=commander)
    officer, commander_role, member_role = roles
    for p in players:
        p["role"] = {
            "Officer": officer,
            "ArmyCommander": commander_role,
            "Rifleman": member_role,
        }[p["role"]]
    players[1]["unit_name"] = "Able" if own_squad else "Other"
    observe_for(db, players)
    with db() as sess:
        assert "member" not in storage.presence(sess, 1)
    incident = report(
        players,
        text=(
            "!admin der commander redet nicht"
            if commander
            else "!Admin Able squad keine Komms"
        ),
        reporter="member",
    )
    vid = incident["leadership_vote"]["id"]
    current = vote(db, vid)
    assert current["status"] == "inviting"
    assert current["participant_count"] == 3 and current["required"] == 2
    assert set(current["electorate"]) == {"v0", "v1", "v2"}
    assert current["yes"] == current["no"] == 0
    api = deliver(db, players)
    assert api.message_player.call_count == 6
    assert {call.args[0] for call in api.message_player.call_args_list} == {
        "v0",
        "v1",
        "v2",
    }
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "active"
    assert not cast(db, players, "member")
    assert not cast(db, players, "member", yes=False)
    assert not cast(db, players, "target")
    assert vote(db, vid)["status"] == "active"
    assert vote(db, vid)["yes"] == vote(db, vid)["no"] == 0
    assert cast(db, players, "v0") and cast(db, players, "v1")
    elapse(db, players, 119)
    assert storage.advance(1, context(players)) == []
    api.kick.assert_not_called()
    elapse(db, players, 1)
    actions = storage.advance(1, context(players))
    monkeypatch.setattr(service, "read_context", lambda _: context(players))
    if mode == "active":
        assert len(actions) == 1
        service.execute(api, 1, actions[0])
        service.execute(api, 1, actions[0])
        assert api.kick.call_count == 1
        assert vote(db, vid)["status"] == "kicked"
    else:
        assert actions == []
        assert vote(db, vid)["status"] == "dry_run"
        api.kick.assert_not_called()


@pytest.mark.parametrize("count", [1, 2])
def test_members_never_count_toward_minimum_voters(db, count):
    players = roster(count) + [
        player(f"member-{i}", "Rifleman", "Other") for i in range(10)
    ]
    observe_for(db, players)
    assert not report(players, reporter="member")["leadership_vote"]


@pytest.mark.parametrize("pid", ["v0", "v5"])
def test_recent_leader_can_report_but_does_not_gain_a_vote_later(db, pid):
    players = roster()
    reporter = next(p for p in players if p["player_id"] == pid)
    leadership = deepcopy(reporter)
    reporter.update(role="Rifleman", unit_name="Other")
    observe_for(db, players)
    reporter.update(leadership)
    storage.observe(1, context(players))
    elapse(db, players, 295)
    incident = report(players, reporter=pid)
    vid = incident["leadership_vote"]["id"]
    assert pid not in vote(db, vid)["electorate"]
    deliver(db, players)
    storage.advance(1, context(players))
    elapse(db, players, 10)
    assert not cast(db, players, pid)
    assert pid not in vote(db, vid)["electorate"]


@pytest.mark.parametrize("pid", ["v0", "v5"])
def test_eligible_reporting_leader_keeps_their_vote(db, pid):
    players = roster()
    observe_for(db, players)
    incident = report(players, reporter=pid)
    vid = incident["leadership_vote"]["id"]
    assert pid in vote(db, vid)["electorate"]
    assert vote(db, vid)["yes"] == 0
    deliver(db, players)
    storage.advance(1, context(players))
    assert cast(db, players, pid)
    assert vote(db, vid)["yes"] == 1


@pytest.mark.parametrize(
    "invalid",
    [
        "self",
        "enemy",
        "unknown_team",
        "offline",
        "missing",
        "duplicate",
        "no_squad",
        "unassigned",
        "command_nonleader",
    ],
)
def test_reporting_requires_unique_live_member_in_target_team(invalid):
    players = roster()
    target = dict(domain.identity(players[0]), player_id="target")
    reporter_id = "member"
    if invalid == "self":
        reporter_id = "target"
    elif invalid == "enemy":
        players[1]["team"] = "axis"
    elif invalid == "unknown_team":
        players[1]["team"] = None
    elif invalid == "offline":
        players[1]["online"] = False
    elif invalid == "missing":
        players.pop(1)
    elif invalid == "duplicate":
        players.append(dict(players[1]))
    else:
        players[1]["unit_name"] = {
            "no_squad": "  ",
            "unassigned": "Unassigned",
            "command_nonleader": "command",
        }[invalid]
    assert not domain.may_report(players, reporter_id, target)


@pytest.mark.parametrize("gate", ["global", "stale", "no_squad", "offline"])
def test_member_report_preserves_channel_freshness_and_membership_guards(db, gate):
    players = roster()
    observe_for(db, players)
    if gate == "no_squad":
        players[1]["unit_name"] = "unassigned"
    if gate == "offline":
        players[1]["online"] = False
    incident = report(
        players,
        reporter="member",
        private=gate != "global",
        stamp=db.clock.now - 31 if gate == "stale" else None,
    )
    assert not incident["leadership_vote"]
    assert incident["status"] == "new"


def test_member_report_preserves_team_lock_admin_takeover_and_cooldown(db):
    players = roster()
    observe_for(db, players)
    incident = report(players, reporter="member")
    vid = incident["leadership_vote"]["id"]
    assert not report(players)["leadership_vote"]
    api = deliver(db, players)
    storage.advance(1, context(players))
    storage.cancel(1, vid, "admin")
    assert vote(db, vid)["status"] == "cancelled"
    assert storage.advance(1, context(players)) == []
    assert not report(players, reporter="member")["leadership_vote"]
    api.kick.assert_not_called()


def test_member_promoted_during_vote_cannot_join_frozen_electorate(db):
    players = roster()
    observe_for(db, players)
    vid = report(players, reporter="member")["leadership_vote"]["id"]
    deliver(db, players)
    storage.advance(1, context(players))
    players[1].update(role="Officer", unit_name="New")
    storage.observe(1, context(players))
    assert not cast(db, players, "member")
    assert "member" not in vote(db, vid)["electorate"]


def test_legacy_confirmation_rechecks_live_reporter_team(db):
    players = roster()
    observe_for(db, players)
    vid = report(players, reporter="member")["leadership_vote"]["id"]
    with db() as sess:
        v = sess.get(LeadershipVote, vid)
        v.status = "confirming"
        v.payload = dict(v.payload, confirm_invited_at=db.clock.now)
    players[1]["team"] = "axis"
    assert cast(db, players, "member")
    assert vote(db, vid)["status"] == "cancelled"


@pytest.mark.parametrize("change", ["team", "squad", "disconnect"])
def test_saved_reporter_context_cannot_replace_current_membership(db, change):
    players = roster()
    observe_for(db, players)
    current = deepcopy(players)
    if change == "team":
        current[1]["team"] = "axis"
    elif change == "squad":
        current[1]["unit_name"] = "unassigned"
    else:
        current.pop(1)
    incident, created = incidents.create_incident_from_chat(
        dict(
            action="CHAT[Allies][Team]",
            player_id_1="member",
            player_name_1="Person-member",
            sub_content="!admin able",
            timestamp_ms=db.clock.now * 1000,
        ),
        current_players=players,
        current_squads=squads(players),
        trigger_words=("!admin",),
        leadership_context=context(current),
    )
    assert created and incident["reporter_context"]["team"] == "allies"
    assert not incident["leadership_vote"]
