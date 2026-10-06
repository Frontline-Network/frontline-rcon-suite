"""Synthetic SQLite and fake RCON only: no real messages or game actions."""

from copy import deepcopy
from datetime import timedelta
import os

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")

import pytest
from sqlalchemy import select

from rcon import (
    report_admin as service,
    report_admin_rules as rules,
    admin_incidents as incidents,
)
from rcon.models import (
    PlayerID,
    PlayerSession,
    LogLine,
    MessageTemplate,
    AdminIncident,
    AdminIncidentEvent,
)
from rcon.user_config.report_admin import ReportAdminUserConfig as Config
from tests.test_leadership_vote import db, roster, player, squads, transport, context


@pytest.fixture
def setup(db, monkeypatch):
    # Legacy migrations allow NULL for an open session; ORM annotation predates
    # Optional typing. Match the real schema without changing production models.
    monkeypatch.setattr(PlayerSession.__table__.c.end, "nullable", True)
    with db() as sess:
        for model in (PlayerID, PlayerSession, LogLine, MessageTemplate):
            model.__table__.create(sess.bind)
    monkeypatch.setattr(service, "enter_session", db)
    monkeypatch.setattr(service, "delivered", lambda *_: True)
    players = roster()
    players[0]["name"] = "BattlefieldHero"
    with db() as sess:
        for p in players:
            pid = PlayerID(player_id=p["player_id"])
            sess.add(pid)
            sess.flush()
            sess.add(
                PlayerSession(
                    player_id_id=pid.id,
                    start=service.utc(db.clock.now - 600).replace(tzinfo=None),
                    end=None,
                    server_number=1,
                    server_name="Test",
                )
            )
    service.configure(1, Config(enabled=True, mode="active"))
    ctx = {**context(players), "round_start": db.clock.now - 600}
    monkeypatch.setattr(service, "read_context", lambda _: deepcopy(ctx))
    return db, players, ctx


def report(setup, message="!admin able redet nicht", server=1):
    db, players, ctx = setup
    reporter = players[2]
    parsed = incidents.parse_chat_report(
        message,
        current_players=players,
        current_squads=squads(players),
        reporter_context=reporter,
        context_mode="enabled",
    )
    return incidents.create_incident(
        server_number=server,
        source="chat",
        reason=parsed["reason"],
        raw_message=message,
        reporter_id=reporter["player_id"],
        reporter_name=reporter["name"],
        reporter_context=reporter,
        subjects=parsed["subjects"],
        actor="system:chat",
        leadership_context=ctx,
        dedupe_seconds=-1,
    )[0]


def current(db, iid):
    with db() as sess:
        return sess.get(AdminIncident, iid).to_dict(include_events=True)


def teamkills(setup, count, *, server="1", age=30, pid="target"):
    db, _, _ = setup
    with db() as sess:
        killer = sess.scalar(select(PlayerID.id).where(PlayerID.player_id == pid))
        victim = sess.scalar(select(PlayerID.id).where(PlayerID.player_id == "member"))
        for n in range(count):
            sess.add(
                LogLine(
                    event_time=service.utc(db.clock.now - age - n).replace(tzinfo=None),
                    type="TEAM KILL",
                    player1_player_id=killer,
                    player2_player_id=victim,
                    raw=f"{server}-{pid}-{age}-{n}",
                    content="Team kill",
                    weapon="Rifle",
                    server=server,
                )
            )


@pytest.mark.parametrize(
    "message,expected",
    [
        ("!Admin Able squad keine Komms", "communication"),
        ("!admin bitte mal prüfen able redet nicht", "communication"),
        ("!admin squad lead how redet nicht", "communication"),
        ("!admin der commander redet nicht", "communication"),
        ("!admin commander is not talking", "communication"),
        ("!admin Hero teamkilling", "teamkills"),
        ("!admin Hero tk", "teamkills"),
        ("!admin Hero teamkillt", "teamkills"),
        ("!admin able", None),
        ("!admin Hero cheater", None),
        ("!admin able redet nicht mehr", None),
        ("!admin Hero keine teamkills", None),
        ("!admin Hero teamkills aus Versehen", None),
        ('!admin Hero sagt "able redet nicht"', None),
        ("!admin Hero not talking?", None),
        ("!admin Hero redet nicht und teamkillt", None),
    ],
)
def test_classification(message, expected):
    assert rules.classify(message) == expected


def test_name_is_not_a_complaint():
    assert rules.classify("!admin No Comms prüfen", [{"name": "No Comms"}]) is None


def test_defaults_off_and_no_ban_setting():
    assert Config().enabled is False and Config().mode == "dry_run"
    with pytest.raises(ValueError):
        Config(ban=True)


def test_direct_communication_kick_no_warning_or_vote(setup):
    db, _, _ = setup
    i = report(setup)
    assert i["leadership_vote"] is None
    assert i["report_admin"]["status"] == "queued"
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "target"
    api.message_player.assert_not_called()
    final = current(db, i["id"])
    assert final["status"] == "resolved" and final["report_admin"]["status"] == "kicked"


@pytest.mark.parametrize("count,kicked", [(0, False), (4, False), (5, True), (6, True)])
def test_teamkill_threshold(setup, count, kicked):
    db, _, _ = setup
    teamkills(setup, count)
    i = report(setup, "!admin BattlefieldHero teamkills")
    api = transport()
    service.tick(api, 1)
    assert api.kick.called is kicked
    assert current(db, i["id"])["report_admin"]["teamkill_count"] == count


@pytest.mark.parametrize(
    "case", ["other_server", "old", "other_player", "previous_round"]
)
def test_teamkill_wrong_evidence_does_not_count(setup, case):
    _, _, ctx = setup
    kwargs = {
        "other_server": {"server": "2"},
        "old": {"age": 301},
        "other_player": {"pid": "v0"},
        "previous_round": {},
    }[case]
    teamkills(setup, 5, **kwargs)
    if case == "previous_round":
        ctx["round_start"] = setup[0].clock.now - 5
    report(setup, "!admin BattlefieldHero teamkills")
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()


@pytest.mark.parametrize(
    "change",
    [
        "offline",
        "team",
        "role",
        "round",
        "stale",
        "reporter_offline",
        "reconnect",
        "expired",
        "config",
        "manual",
    ],
)
def test_final_checks_fail_closed(setup, change):
    db, players, ctx = setup
    i = report(setup)
    if change == "offline":
        ctx["players"] = players[1:]
    if change == "reporter_offline":
        ctx["players"] = [p for p in players if p["player_id"] != "v0"]
    if change == "team":
        players[0]["team"] = "axis"
    if change == "role":
        players[0]["role"] = "Rifleman"
    if change == "round":
        ctx["round_id"] = "different"
    if change == "stale":
        ctx["captured_at"] -= 20
    if change == "expired":
        db.clock.now += 61
    if change == "config":
        service.configure(1, Config(enabled=False))
    if change == "manual":
        with db() as sess:
            incident = sess.get(AdminIncident, i["id"])
            service.cancel_incident(sess, incident, "admin")
            incident.status, incident.assigned_to = "claimed", "admin"
    if change == "reconnect":
        with db() as sess:
            old = sess.scalar(
                select(PlayerSession)
                .join(PlayerID)
                .where(PlayerID.player_id == "target")
            )
            old.end = service.utc(db.clock.now).replace(tzinfo=None)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(db, i["id"])["report_admin"]["status"] == "manual"


@pytest.mark.parametrize("mode", ["dry_run", "unknown", "exception", "restart"])
def test_never_repeat_uncertain_kick(setup, mode):
    db, _, _ = setup
    if mode == "dry_run":
        service.configure(1, Config(enabled=True))
    i = report(setup)
    if mode == "restart":
        service.recover(1)
    api = transport()
    if mode == "unknown":
        api.kick.return_value = None
    if mode == "exception":
        api.kick.side_effect = RuntimeError("timeout")
    service.tick(api, 1)
    service.tick(api, 1)
    assert api.kick.call_count == (1 if mode in {"unknown", "exception"} else 0)
    assert current(db, i["id"])["status"] == "new"


def test_discord_delivery_required(setup, monkeypatch):
    db, _, _ = setup
    monkeypatch.setattr(service, "delivered", lambda *_: False)
    i = report(setup)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(db, i["id"])["report_admin"]["status"] == "queued"


def test_duplicate_reports_one_attempt(setup):
    report(setup)
    report(setup)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_called_once()


def test_other_complaints_no_vote_no_kick(setup):
    i = report(setup, "!admin able sabotiert")
    assert not i["report_admin"] and not i["leadership_vote"]
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()


@pytest.mark.parametrize(
    "fragment", ["BattlefielxHero", "BattlexielxHero", "BattlexielxHera"]
)
def test_long_unique_name_typos(setup, fragment):
    teamkills(setup, 5)
    i = report(setup, f"!admin {fragment} teamkills")
    api = transport()
    service.tick(api, 1)
    assert i["report_admin"]["status"] == "queued"
    primary = next(s for s in i["subjects"] if s["is_primary"])
    assert primary["match_method"] == "report_admin_validated"
    assert primary["confidence"] is None
    assert any(
        c["match_method"] == "fuzzy" and c["matched_text"].lower() == fragment.lower()
        for c in primary["snapshot"]["candidates"]
    )
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "target"


def test_two_similar_names_manual(setup):
    db, players, _ = setup
    players.append(player("twin", squad="Other"))
    players[-1]["name"] = "BattlefieldHera"
    i = report(setup, "!admin BattlefieldHere teamkills")
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert i["report_admin"]["status"] == "manual"


def test_templates_and_fallback(setup):
    db, _, _ = setup
    with db() as sess:
        template = MessageTemplate(
            title="TK",
            content="{player_name}: {teamkills} TK / {minutes} min",
            category="REASON",
            updated_by="admin",
        )
        sess.add(template)
        sess.flush()
        tid = template.id
    service.configure(1, Config(enabled=True, mode="active", teamkills_template_id=tid))
    teamkills(setup, 5)
    report(setup, "!admin BattlefieldHero teamkills")
    api = transport()
    service.tick(api, 1)
    assert api.kick.call_args.args[1] == "BattlefieldHero: 5 TK / 5 min"


@pytest.mark.parametrize(
    "role",
    [
        "Officer",
        "TankCommander",
        "Spotter",
        "HelicopterLogisticsOfficer",
        "ArmyCommander",
    ],
)
def test_supported_leadership_roles(setup, role):
    _, players, _ = setup
    if role == "ArmyCommander":
        # Replace the existing commander instead of creating an invalid team
        # with two current commanders.
        players[-1]["role"] = "Rifleman"
    players[0]["role"] = role
    i = report(setup, "!admin BattlefieldHero redet nicht")
    assert i["report_admin"]["status"] == "queued"


def test_nonleader_communication_stays_manual(setup):
    setup[1][0]["role"] = "Rifleman"
    i = report(setup, "!admin BattlefieldHero redet nicht")
    assert i["report_admin"]["status"] == "manual"


def test_final_refresh_disconnect_and_crash_marker(setup, monkeypatch):
    db, _, ctx = setup
    i = report(setup)
    api = transport()
    from unittest.mock import Mock

    monkeypatch.setattr(
        service,
        "read_context",
        Mock(side_effect=[deepcopy(ctx), RuntimeError("snapshot unavailable")]),
    )
    with pytest.raises(RuntimeError):
        service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(db, i["id"])["report_admin"]["status"] == "sending"
    service.recover(1)
    assert current(db, i["id"])["report_admin"]["status"] == "unknown"


def test_disable_between_reservation_and_send(setup, monkeypatch):
    _, _, ctx = setup
    report(setup)
    calls = []

    def fetch(_):
        calls.append(1)
        if len(calls) == 2:
            service.configure(1, Config())
        return deepcopy(ctx)

    monkeypatch.setattr(service, "read_context", fetch)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()


def test_current_session_required_on_enqueue(setup):
    db, _, _ = setup
    with db() as sess:
        row = sess.scalar(
            select(PlayerSession).join(PlayerID).where(PlayerID.player_id == "target")
        )
        row.end = service.utc(db.clock.now).replace(tzinfo=None)
    i = report(setup)
    assert i["report_admin"]["status"] == "manual"


def test_server_scope_config_and_processing(setup):
    db, _, _ = setup
    i = report(setup)
    api = transport()
    service.tick(api, 2)
    api.kick.assert_not_called()
    with db() as sess:
        assert service.config(sess, 2).enabled is False
    assert current(db, i["id"])["report_admin"]["status"] == "queued"


def test_short_name_fuzzy_not_promoted():
    assert (
        rules.conservative_name_match(
            [
                {
                    "kind": "player",
                    "state": "suggested",
                    "match_method": "fuzzy",
                    "matched_text": "Mxa",
                    "player_id": "x",
                }
            ],
            [{"player_id": "x", "name": "Max"}],
        )
        is None
    )


def test_failed_squad_reference_cannot_fall_back_to_named_leader(setup):
    setup[1][0]["unit_name"] = "Baker"
    i = report(setup, "!admin able BattlefieldHero redet nicht")
    assert i["report_admin"]["status"] == "manual"


@pytest.mark.parametrize("after_report", [False, True])
def test_duplicate_leadership_seat_prevents_name_kick(setup, after_report):
    db, players, _ = setup
    if after_report:
        i = report(setup, "!admin BattlefieldHero redet nicht")
        assert i["report_admin"]["status"] == "queued"
    duplicate = {**players[0], "player_id": "duplicate", "name": "OtherOfficer"}
    players.append(duplicate)
    if not after_report:
        i = report(setup, "!admin BattlefieldHero redet nicht")
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(db, i["id"])["report_admin"]["status"] == "manual"


@pytest.mark.parametrize("operation", ["configure", "recover", "cancel_player"])
def test_maintenance_cancels_all_pending_reports(setup, operation):
    db, _, _ = setup
    i = report(setup)
    with db() as sess:
        incident = sess.get(AdminIncident, i["id"])
        original = next(e for e in incident.events if e.event_type == "report_admin")
        for _ in range(100):
            incident.events.append(
                AdminIncidentEvent(
                    actor=service.ACTOR,
                    event_type="report_admin",
                    payload=deepcopy(original.payload),
                    created_at=original.created_at,
                )
            )
    if operation == "configure":
        service.configure(1, Config())
    elif operation == "recover":
        service.recover(1)
    else:
        with db() as sess:
            service.cancel_player(sess, 1, "target")
    with db() as sess:
        assert not service.pending(sess, 1)
