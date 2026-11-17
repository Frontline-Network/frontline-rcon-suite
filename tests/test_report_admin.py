"""Synthetic SQLite and fake RCON only: no real messages or game actions."""

from copy import deepcopy
from datetime import datetime, timedelta, timezone
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
from tests.test_leadership_vote_notifications import controller


@pytest.fixture
def setup(db, monkeypatch):
    # Legacy migrations allow NULL for an open session; ORM annotation predates
    # Optional typing. Match the real schema without changing production models.
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
                    start_event_us=int((db.clock.now - 600) * 1_000_000),
                    end=None,
                    server_number=1,
                    server_name="Test",
                )
            )
    service.configure(1, Config(enabled=True, mode="active"))
    ctx = {**context(players), "round_start": db.clock.now - 600}
    monkeypatch.setattr(service, "read_context", lambda _: deepcopy(ctx))

    def live_logs(_):
        with db() as sess:
            rows = sess.scalars(select(LogLine).where(LogLine.server == "1")).all()
            logs = [
                {
                    "timestamp_ms": row.event_time.replace(
                        tzinfo=service.timezone.utc
                    ).timestamp()
                    * 1000,
                    "action": row.type,
                    "player_id_1": row.player_1.player_id if row.player_1 else None,
                    "player_id_2": row.player_2.player_id if row.player_2 else None,
                    "player_name_1": row.player1_name,
                    "player_name_2": row.player2_name,
                    "weapon": row.weapon,
                    "sub_content": (
                        service.evidence_rules.chat_body(
                            row.content, row.player1_name, row.player_1.player_id
                        )
                        if row.player_1
                        else None
                    ),
                }
                for row in rows
            ]
        return {"logs": logs, "captured_at": db.clock.now, "game": 1}

    monkeypatch.setattr(service.evidence_rules, "fresh_logs", live_logs)
    monkeypatch.setattr(service, "role_history", lambda _: [])
    return db, players, ctx


def report(setup, message="!admin able redet nicht", server=1, reporter_id="v0"):
    db, players, ctx = setup
    reporter = next(p for p in players if p["player_id"] == reporter_id)
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


def test_report_session_token_uses_absolute_connect_time_across_dst(setup):
    db = setup[0]
    old = datetime(2026, 10, 25, 0, 59, 58, tzinfo=timezone.utc)
    current = datetime(2026, 10, 25, 1, 0, 1, tzinfo=timezone.utc)
    with db() as sess:
        player = PlayerID(player_id='synthetic-dst-report')
        sess.add(player)
        sess.flush()
        newer = PlayerSession(player_id_id=player.id, server_number=1,
            start=datetime(2026, 10, 25, 2, 0, 1), start_event_us=int(current.timestamp() * 1_000_000),
            created=datetime(2026, 10, 25, 1, 0, 1))
        older_delayed = PlayerSession(player_id_id=player.id, server_number=1,
            start=datetime(2026, 10, 25, 2, 59, 58), start_event_us=int(old.timestamp() * 1_000_000),
            created=datetime(2026, 10, 25, 1, 0, 2))
        sess.add_all([newer, older_delayed])
        sess.flush()
        assert service.session_token(sess, 1, player.player_id, current.timestamp() + 3) == newer.id
        newer.end_event_us = int((current.timestamp() + 2) * 1_000_000)
        sess.flush()
        assert service.session_token(sess, 1, player.player_id, current.timestamp() + 3) is None


def test_report_session_token_rejects_unverified_legacy_session(setup):
    db = setup[0]
    with db() as sess:
        player = PlayerID(player_id='synthetic-legacy-report')
        sess.add(player)
        sess.flush()
        sess.add(PlayerSession(player_id_id=player.id, server_number=1,
            start=datetime(2026, 1, 1, 12), created=datetime(2026, 1, 1, 12)))
        sess.flush()
        assert service.session_token(sess, 1, player.player_id, datetime(2026, 1, 1, 13, tzinfo=timezone.utc).timestamp()) is None


def test_report_session_token_rejects_a_later_unverified_record(setup):
    db = setup[0]
    start = datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    with db() as sess:
        player = PlayerID(player_id='synthetic-ambiguous-report')
        sess.add(player)
        sess.flush()
        sess.add_all([
            PlayerSession(player_id_id=player.id, server_number=1,
                start=start.replace(tzinfo=None), start_event_us=int(start.timestamp() * 1_000_000),
                created=start.replace(tzinfo=None)),
            PlayerSession(player_id_id=player.id, server_number=1,
                start=datetime(2026, 1, 1, 12, 5), created=datetime(2026, 1, 1, 12, 5)),
        ])
        sess.flush()
        assert service.session_token(sess, 1, player.player_id, start.timestamp() + 600) is None


def test_confirmed_report_admin_target_retains_own_live_statistics(setup):
    db, players, _ = setup
    target = next(p for p in players if p["player_id"] == "target")
    target.update(
        kills=12,
        deaths=4,
        team_kills=0,
        combat=190,
        kills_streak=5,
        map_playtime_seconds=600,
    )
    other = next(p for p in players if p["player_id"] == "v0")
    other.update(kills=99, team_kills=99, combat=9999)
    incident = report(setup)
    snapshot = current(db, incident["id"])["primary_subject"]["snapshot"]
    assert snapshot["player_id"] == "target"
    assert snapshot["kills"] == 12
    assert snapshot["deaths"] == 4
    assert snapshot["combat"] == 190
    assert snapshot["teamkills"] == 0
    assert snapshot["kills_streak"] == 5
    assert snapshot["map_playtime_seconds"] == 600
    assert snapshot["rule"] == "communication"
    assert "candidates" in snapshot


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


def chat(setup, body, *, age=0, pid="target", server="1"):
    db, players, _ = setup
    name = next(p["name"] for p in players if p["player_id"] == pid)
    with db() as sess:
        actor = sess.scalar(select(PlayerID.id).where(PlayerID.player_id == pid))
        sess.add(
            LogLine(
                event_time=service.utc(db.clock.now - age).replace(tzinfo=None),
                type="CHAT[Allies][Team]",
                player1_name=name,
                player1_player_id=actor,
                raw=f"chat-{pid}-{server}-{age}-{body}",
                content=f"{name}: {body} ({pid})",
                weapon="",
                server=server,
            )
        )


def admitted_teamkill(setup, count=1):
    teamkills(setup, count, age=75)
    chat(setup, "I teamkilled him on purpose", age=70)


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
        ("!admin Hero cheater", "cheating"),
        ("!admin able redet nicht mehr", None),
        ("!admin Hero keine teamkills", "teamkills"),
        ("!admin Hero teamkills aus Versehen", "teamkills"),
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
    assert Config().allow_self_reports is False
    with pytest.raises(ValueError):
        Config(ban=True)


@pytest.mark.parametrize("allowed", [False, True])
@pytest.mark.parametrize("kind", ["squadleader", "commander", "teamkills"])
def test_self_report_requires_explicit_server_option(setup, allowed, kind):
    db, players, _ = setup
    service.configure(
        1, Config(enabled=True, mode="active", allow_self_reports=allowed)
    )
    message = "!admin able redet nicht"
    if kind == "commander":
        players[-1]["role"] = "Rifleman"
        players[0].update(role="ArmyCommander", unit_name="")
        message = "!admin commander is not talking"
    if kind == "teamkills":
        admitted_teamkill(setup)
        message = "!admin BattlefieldHero teamkills"
    i = report(setup, message, reporter_id="target")
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    assert api.kick.call_count == int(allowed)
    if allowed:
        assert api.kick.call_args.args[0] == "target"
    assert current(db, i["id"])["report_admin"]["status"] == (
        "kicked" if allowed else "manual"
    )
    api.message_player.assert_not_called()


@pytest.mark.parametrize(
    "change", ["dry_run", "nonleader", "stale", "session", "disabled", "no_delivery"]
)
def test_self_report_does_not_bypass_other_guards(setup, monkeypatch, change):
    db, players, ctx = setup
    cfg = Config(enabled=True, mode="active", allow_self_reports=True)
    if change == "dry_run":
        cfg.mode = "dry_run"
    service.configure(1, cfg)
    if change == "nonleader":
        players[0]["role"] = "Rifleman"
    i = report(setup, "!admin BattlefieldHero redet nicht", reporter_id="target")
    if change == "stale":
        ctx["captured_at"] -= 20
    if change == "session":
        with db() as sess:
            row = sess.scalar(
                select(PlayerSession)
                .join(PlayerID)
                .where(PlayerID.player_id == "target")
            )
            row.end = service.utc(db.clock.now).replace(tzinfo=None)
    if change == "disabled":
        service.configure(1, Config(enabled=True, mode="active"))
    if change == "no_delivery":
        monkeypatch.setattr(service, "delivered", lambda *_: False)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(db, i["id"])["report_admin"]["status"] == (
        "dry_run"
        if change == "dry_run"
        else "queued" if change == "no_delivery" else "manual"
    )


def test_self_report_never_bypasses_teamkill_intent_check(setup):
    service.configure(1, Config(enabled=True, mode="active", allow_self_reports=True))
    teamkills(setup, 4)
    i = report(setup, "!admin BattlefieldHero teamkills", reporter_id="target")
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(setup[0], i["id"])["report_admin"]["teamkill_count"] == 4


def test_single_hllv_squadleader_can_test_own_report(setup):
    db, players, ctx = setup
    players[:] = [players[0]]
    players[0].update(name="Biene", role="squadleader", unit_id=0, unit_name="able")
    service.configure(1, Config(enabled=True, mode="active", allow_self_reports=True))
    i = report(setup, reporter_id="target")
    assert i["leadership_vote"] is None
    api = transport()
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert current(db, i["id"])["report_admin"]["status"] == "kicked"


def test_enabling_self_reports_never_replays_old_report(setup):
    db, _, _ = setup
    i = report(setup, reporter_id="target")
    assert i["report_admin"]["status"] == "manual"
    service.configure(1, Config(enabled=True, mode="active", allow_self_reports=True))
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(db, i["id"])["report_admin"]["status"] == "manual"


def test_self_report_exception_is_server_local_and_not_a_vote_permission(setup):
    from rcon.leadership_vote.domain import identity, may_report

    db, players, _ = setup
    service.configure(2, Config(enabled=True, mode="active", allow_self_reports=True))
    i = report(setup, reporter_id="target")
    assert i["report_admin"]["status"] == "manual"
    service.configure(1, Config(enabled=True, mode="active", allow_self_reports=True))
    assert not may_report(
        players, "target", dict(identity(players[0]), player_id="target")
    )
    with db() as sess:
        assert service.config(sess, 3).allow_self_reports is False


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
    api.message_player.assert_called_once()
    receipt = api.message_player.call_args
    assert receipt.args[0] == "v0"
    assert "BattlefieldHero wurde vom Server gekickt" in receipt.args[1]
    assert "BattlefieldHero was kicked from the server" in receipt.args[1]
    assert receipt.kwargs["save_message"] is False
    final = current(db, i["id"])
    assert final["status"] == "resolved" and final["report_admin"]["status"] == "kicked"


@pytest.mark.parametrize("count", [0, 1, 4, 5, 6, 20])
def test_teamkill_count_alone_never_kicks(setup, count):
    db, _, _ = setup
    teamkills(setup, count)
    i = report(setup, "!admin BattlefieldHero teamkills")
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
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
    api.message_player.assert_not_called()


def notification(db, iid):
    with db() as sess:
        event = next(
            e
            for e in sess.get(AdminIncident, iid).events
            if e.event_type == "report_admin"
        )
        return event.id, event.payload.get("reporter_notification")


def test_report_receipt_defaults_preserve_existing_languages():
    assert Config.model_validate({}).receipt_language == "de+en"
    assert service.reporter_receipt("Player") == (
        "Deine Meldung wurde bearbeitet: Player wurde vom Server gekickt.\n"
        "Your report was handled: Player was kicked from the server."
    )
    assert "Deine Cheatmeldung" in service.reporter_receipt("Player", review=True)
    assert "Your cheat report" in service.reporter_receipt("Player", review=True)
    assert "Votre signalement" in service.reporter_receipt("Player", language="fr")
    assert "preuves sont examinées" in service.reporter_receipt("Player", review=True, language="fr")
    with pytest.raises(ValueError):
        Config.model_validate({"receipt_language": "invalid"})


def test_french_report_receipt_uses_config_without_changing_action(setup):
    db, _, _ = setup
    service.configure(1, Config(enabled=True, mode="active", receipt_language="fr"))
    incident = report(setup)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_called_once()
    api.message_player.assert_called_once()
    text = api.message_player.call_args.args[1]
    assert "Votre signalement a été traité" in text
    assert "Your report" not in text and "Deine Meldung" not in text
    assert notification(db, incident["id"])[1]["status"] == "sent"


@pytest.mark.parametrize("result", [True, False, None, "exception"])
def test_reporter_receipt_never_retries_or_changes_kick_result(setup, result):
    db, _, _ = setup
    i = report(setup)
    api = transport()

    def send(*args, **kwargs):
        # The confirmed kick is already durable before the notification.
        assert current(db, i["id"])["status"] == "resolved"
        assert notification(db, i["id"])[1]["status"] == "sending"
        if result == "exception":
            raise RuntimeError("message timeout")
        return result

    api.message_player.side_effect = send
    service.tick(api, 1)
    event_id, receipt = notification(db, i["id"])
    service.notify_reporter(api, 1, event_id)
    service.tick(api, 1)
    api.kick.assert_called_once()
    api.message_player.assert_called_once()
    assert receipt["status"] == ("sent" if result is True else "unknown")
    assert current(db, i["id"])["report_admin"]["status"] == "kicked"


@pytest.mark.parametrize(
    "change", ["offline", "team", "reconnect", "stale", "round", "read_error"]
)
def test_reporter_receipt_uses_current_recipient_and_preserves_kick(
    setup, monkeypatch, change
):
    db, players, ctx = setup
    i = report(setup)
    api = transport()
    calls = []

    def read(_):
        calls.append(1)
        fresh = deepcopy(ctx)
        if len(calls) == 3:  # Receipt check, after the two kick preflights.
            if change == "read_error":
                raise RuntimeError("roster unavailable")
            if change == "offline":
                fresh["players"] = [
                    p for p in fresh["players"] if p["player_id"] != "v0"
                ]
            if change == "team":
                next(p for p in fresh["players"] if p["player_id"] == "v0")[
                    "team"
                ] = "axis"
            if change == "stale":
                fresh["captured_at"] -= 20
            if change == "round":
                fresh["round_id"] = "new-round"
            if change == "reconnect":
                with db() as sess:
                    row = sess.scalar(
                        select(PlayerSession)
                        .join(PlayerID)
                        .where(PlayerID.player_id == "v0")
                    )
                    row.end = service.utc(db.clock.now).replace(tzinfo=None)
        return fresh

    monkeypatch.setattr(service, "read_context", read)
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    api.message_player.assert_not_called()
    assert current(db, i["id"])["status"] == "resolved"


def test_teamkill_kick_also_notifies_only_reporter(setup):
    admitted_teamkill(setup)
    report(setup, "!admin BattlefieldHero teamkills")
    api = transport()
    service.tick(api, 1)
    api.message_player.assert_called_once()
    assert api.message_player.call_args.args[0] == "v0"


def test_receipt_hll_and_hllv_delivery_does_not_record_a_warning(setup, controller):
    report(setup)
    api = transport()
    api.message_player = controller.api.message_player
    service.tick(api, 1)
    api.kick.assert_called_once()
    controller.sent.assert_called_once()
    assert controller.sent.call_args.args[0] == "v0"
    controller.audit.assert_not_called()


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
    admitted_teamkill(setup)
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
    admitted_teamkill(setup, 5)
    report(setup, "!admin BattlefieldHero teamkills")
    api = transport()
    service.tick(api, 1)
    assert api.kick.call_args.args[1] == "BattlefieldHero: 5 TK / 10.0 min"


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


@pytest.mark.parametrize("recovered", [True, False])
def test_initial_context_gap_preserves_runtime_owner(setup, monkeypatch, recovered):
    from unittest.mock import Mock

    db, _, ctx = setup
    i = report(setup)
    api = transport()
    runtime = service.Runtime()
    runtime.server = 1
    runtime.owner = owner = Mock()
    owner.dialect.name = "sqlite"
    monkeypatch.setattr(
        service,
        "read_context",
        Mock(side_effect=ValueError("No recorder-confirmed current round")),
    )
    runtime.step(api)
    assert runtime.owner is owner
    owner.close.assert_not_called()
    assert current(db, i["id"])["report_admin"]["status"] == "queued"
    api.kick.assert_not_called()
    db.clock.now += 5 if recovered else service.CONTEXT_RETRY_SECONDS
    ctx["captured_at"] = db.clock.now
    if recovered:
        monkeypatch.setattr(service, "read_context", lambda _: deepcopy(ctx))
    runtime.step(api)
    assert runtime.owner is owner
    if recovered:
        api.kick.assert_called_once()
    else:
        api.kick.assert_not_called()
        assert current(db, i["id"])["report_admin"]["status"] == "manual"


def test_context_recovery_rechecks_round(setup, monkeypatch):
    from unittest.mock import Mock

    db, _, ctx = setup
    i = report(setup)
    api = transport()
    monkeypatch.setattr(
        service, "read_context", Mock(side_effect=ValueError("round unavailable"))
    )
    service.tick(api, 1)
    db.clock.now += 5
    ctx.update(
        captured_at=db.clock.now, round_start=db.clock.now, round_id="next-round"
    )
    monkeypatch.setattr(service, "read_context", lambda _: deepcopy(ctx))
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(db, i["id"])["report_admin"]["status"] == "manual"


@pytest.mark.parametrize("initial_age,recovery_delay", [(58, 3), (0, 16)])
def test_context_retry_does_not_extend_deadlines(
    setup, monkeypatch, initial_age, recovery_delay
):
    from unittest.mock import Mock

    db, _, ctx = setup
    i = report(setup)
    api = transport()
    db.clock.now += initial_age
    monkeypatch.setattr(
        service, "read_context", Mock(side_effect=ValueError("round unavailable"))
    )
    service.tick(api, 1)
    db.clock.now += recovery_delay
    ctx["captured_at"] = db.clock.now
    monkeypatch.setattr(service, "read_context", lambda _: deepcopy(ctx))
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(db, i["id"])["report_admin"]["status"] == "manual"
