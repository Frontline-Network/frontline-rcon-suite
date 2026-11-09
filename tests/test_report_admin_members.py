"""Opt-in member reports: synthetic rosters, database and fake game transport."""

import pytest
from sqlalchemy import select

from tests.test_report_admin import setup, db, report, current, service, transport
from tests.test_report_reason import decision, complete
from rcon.report_admin_rules import communication_identity
from rcon.models import PlayerID, PlayerSession
from rcon.user_config.report_admin import ReportAdminUserConfig as Config


def enable(setup, *, mode="active", reason_mode="ai"):
    service.configure(
        1,
        Config(
            enabled=True,
            mode=mode,
            reason_mode=reason_mode,
            communication_squad_members=True,
        ),
    )
    member = next(p for p in setup[1] if p["player_id"] == "member")
    member.update(name="FriendlySoldier", unit_id=0)
    return member


def reported(setup, fragment="FriendlySoldier", reason_mode="ai"):
    i = report(setup, f"!admin {fragment} redet nicht")
    if reason_mode == "ai":
        complete(setup, i["id"], decision(target=fragment, excerpt="redet nicht"))
    return i


@pytest.mark.parametrize("reason_mode", ["rules", "ai"])
@pytest.mark.parametrize("fragment", ["FriendlySoldier", "FrienxlySoldier"])
def test_named_member_one_kick_and_receipt(setup, reason_mode, fragment):
    enable(setup, reason_mode=reason_mode)
    i = reported(setup, fragment, reason_mode)
    api = transport()
    for _ in range(4):
        service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "member"
    assert "leadership" not in str(api.kick.call_args)
    assert "Reported lack of communication" in str(api.kick.call_args)
    assert current(setup[0], i["id"])["report_admin"]["status"] == "kicked"
    assert api.message_player.call_args.args[0] == "v0"
    assert "FriendlySoldier was kicked" in api.message_player.call_args.args[1]


@pytest.mark.parametrize("stage", ["analysis", "queued"])
@pytest.mark.parametrize(
    "change",
    [
        "team",
        "squad",
        "unit",
        "role",
        "offline",
        "reconnect",
        "config",
        "takeover",
        "map",
        "stale",
        "twin",
    ],
)
def test_members_keep_all_live_safety_guards(setup, stage, change):
    member = enable(setup)
    i = reported(setup)
    api = transport()
    if stage == "queued":
        service.tick(api, 1)
        assert current(setup[0], i["id"])["report_admin"]["status"] == "queued"
    if change == "team":
        member["team"] = "axis"
    if change == "squad":
        member["unit_name"] = "Baker"
    if change == "unit":
        member["unit_id"] = 2
    if change == "role":
        member["role"] = "Medic"
    if change == "offline":
        member["online"] = False
    if change == "twin":
        setup[1].append(dict(member))
    if change == "map":
        setup[2]["round_id"] = "new-map"
    if change == "stale":
        setup[2]["captured_at"] -= 20
    if change == "config":
        service.configure(1, Config())
    if change == "takeover":
        with setup[0]() as sess:
            service.cancel_player(sess, 1, "member")
    if change == "reconnect":
        with setup[0]() as sess:
            row = sess.scalar(
                select(PlayerSession)
                .join(PlayerID)
                .where(PlayerID.player_id == "member")
            )
            row.end = service.utc(setup[0].clock.now).replace(tzinfo=None)
            sess.add(
                PlayerSession(
                    player_id_id=row.player_id_id,
                    start=service.utc(setup[0].clock.now + 1).replace(tzinfo=None),
                    end=None,
                    server_number=1,
                    server_name="Test",
                )
            )
        setup[0].clock.now += 2
    for _ in range(3):
        service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(setup[0], i["id"])["report_admin"]["status"] == "manual"


@pytest.mark.parametrize("mode", ["dry_run", "active"])
def test_scope_defaults_and_server_isolation(setup, mode):
    enable(setup, mode=mode)
    with setup[0]() as sess:
        assert service.config(sess, 1).communication_squad_members
        assert not service.config(sess, 2).communication_squad_members
    if mode == "active":
        service.configure(1, Config(enabled=True, mode=mode, reason_mode="ai"))
    i = reported(setup)
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(setup[0], i["id"])["report_admin"]["status"] == (
        "dry_run" if mode == "dry_run" else "manual"
    )


@pytest.mark.parametrize(
    "reference,kind,pid",
    [("able", "squad", "target"), ("commander", "commander", "v5")],
)
def test_member_opt_in_does_not_change_squad_or_commander_target(
    setup, reference, kind, pid
):
    enable(setup)
    i = report(setup, f"!admin {reference} redet nicht")
    complete(
        setup,
        i["id"],
        decision(target=reference, target_kind=kind, excerpt="redet nicht"),
    )
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == pid


def test_squad_without_leader_never_selects_a_member(setup):
    enable(setup)
    setup[1][0]["role"] = "Rifleman"
    i = report(setup, "!admin able redet nicht")
    complete(
        setup,
        i["id"],
        decision(target="able", target_kind="squad", excerpt="redet nicht"),
    )
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    api.kick.assert_not_called()


@pytest.mark.parametrize("name", ["Able", "MyCustomSquad"])
def test_member_named_like_squad_is_not_a_safe_target(setup, name):
    member = enable(setup)
    member["name"] = name
    setup[1][0].update(unit_name=name, role="Rifleman")
    reported(setup, name)
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    api.kick.assert_not_called()


@pytest.mark.parametrize(
    "field,value",
    [
        ("role", "unset"),
        ("role", ""),
        ("unit_name", "unassigned"),
        ("unit_name", ""),
        ("team", "unset"),
        ("online", False),
    ],
)
def test_incomplete_members_fail_closed(setup, field, value):
    member = enable(setup)
    member[field] = value
    assert communication_identity(member, True) is None


def test_members_sharing_same_role_and_squad_are_not_competing_leaders(setup):
    member = enable(setup)
    setup[1][0].update(role=member["role"], unit_id=member["unit_id"])
    i = reported(setup)
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "member"
