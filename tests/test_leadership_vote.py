"""Deterministic synthetic game/DB tests. No production connection or real kick."""

import os
from contextlib import contextmanager, nullcontext
from copy import deepcopy
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import Mock
import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.compiler import compiles


@compiles(JSONB, "sqlite")
def sqlite_jsonb(type_, compiler, **kw):
    return "JSON"


os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")
os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("DEBUG", "1")
from rcon import admin_incidents as incidents
from rcon.leadership_vote import domain, service, storage
from rcon.models import (
    AdminIncident,
    AdminIncidentEvent,
    AdminIncidentSubject,
    LeadershipMessage,
    LeadershipPresence,
    LeadershipVote,
    UserConfig,
)
from rcon.user_config.leadership_vote import LeadershipVoteUserConfig as Config

REAL_DISCORD_READY = storage.discord_ready
REAL_REPORT_DELIVERED = storage.report_delivered

NOW = 2000000000.0
TABLES = (
    UserConfig,
    LeadershipPresence,
    LeadershipVote,
    LeadershipMessage,
    AdminIncident,
    AdminIncidentSubject,
    AdminIncidentEvent,
)


def player(pid, role="Officer", squad="Baker", team="allies"):
    return dict(
        player_id=pid,
        name="Person-" + pid,
        role=role,
        unit_name=squad,
        team=team,
        online=True,
    )


def roster(n=6, commander=False):
    leaders = [player(f"v{i}", squad=f"Squad-{i}") for i in range(n)]
    if commander:
        target = player("target", role="ArmyCommander", squad="")
    else:
        target = player("target", squad="Able")
        leaders[-1] = player(f"v{n-1}", role="ArmyCommander", squad="")
    return [target, player("member", "Rifleman", "Able")] + leaders


def squads(players):
    grouped = {}
    for p in players:
        if p["unit_name"]:
            grouped.setdefault((p["team"], p["unit_name"]), []).append(p)
    return [
        dict(
            name=squad,
            team=team,
            type="infantry",
            has_leader=True,
            leader=next((p for p in members if incidents._is_squad_leader(p)), None),
            players=members,
        )
        for (team, squad), members in grouped.items()
    ]


@pytest.fixture
def db(monkeypatch):
    engine = create_engine("sqlite://")
    for model in TABLES:
        model.__table__.create(engine)
    sessions = sessionmaker(engine, expire_on_commit=False)

    @contextmanager
    def session():
        with sessions.begin() as sess:
            yield sess

    session.clock = SimpleNamespace(now=NOW)
    for module in (incidents, storage, service):
        monkeypatch.setattr(module, "enter_session", session)
    monkeypatch.setattr(storage, "confirmed_audit", lambda sess, vote: False)
    monkeypatch.setattr(storage, "discord_ready", lambda sess: True)
    monkeypatch.setattr(storage, "report_delivered", lambda sess, vote: True)
    monkeypatch.setattr(
        incidents,
        "_utcnow",
        lambda: datetime.fromtimestamp(session.clock.now, timezone.utc),
    )
    monkeypatch.setattr(storage.time, "time", lambda: session.clock.now)
    monkeypatch.setattr(incidents, "_mobile_context_fuzzy_threshold", lambda: 0.9)

    def enabled(cls):
        with session() as sess:
            return storage.config(sess, 1)

    monkeypatch.setattr(Config, "load_from_db", classmethod(enabled))
    storage.configure(1, Config(enabled=True), "tester")
    yield session
    engine.dispose()


def context(players, round_id="round-1"):
    return dict(
        players=players,
        round_id=round_id,
        captured_at=storage.time.time(),
        event_time=storage.time.time(),
        private_chat=True,
    )


def observe_for(db, players, seconds=300, server=1):
    # Tenure is earned by actual successive observations, not assumed by fixtures.
    end = db.clock.now
    for t in range(0, seconds + 1, 5):
        db.clock.now = end - seconds + t
        storage.observe(server, context(players))
    db.clock.now = end


def elapse(db, players, seconds, server=1):
    for delta in [5] * int(seconds // 5) + ([seconds % 5] if seconds % 5 else []):
        db.clock.now += delta
        storage.observe(server, context(players))


def report(
    players=None,
    text="!admin able redet nicht",
    reporter="v0",
    server=1,
    private=True,
    stamp=None,
    round_id="round-1",
    dedupe_seconds=-1,
):
    players = players or roster()
    reporter_data = next(p for p in players if p["player_id"] == reporter)
    parsed = incidents.parse_chat_report(
        text,
        current_players=players,
        current_squads=squads(players),
        reporter_context=reporter_data,
        context_mode="enabled",
    )
    ctx = context(players, round_id)
    ctx.update(
        private_chat=private, event_time=storage.time.time() if stamp is None else stamp
    )
    return incidents.create_incident(
        server_number=server,
        source="chat",
        actor="system:chat",
        reason=parsed["reason"],
        raw_message=text,
        reporter_id=reporter,
        reporter_name=reporter,
        dedupe_seconds=dedupe_seconds,
        reporter_context=reporter_data,
        subjects=parsed["subjects"],
        leadership_context=ctx,
    )[0]


def vote(db, vote_id):
    with db() as sess:
        return storage.summary(sess.get(LeadershipVote, vote_id))


def transport():
    return SimpleNamespace(
        without_retries=nullcontext,
        message_player=Mock(return_value=True),
        kick=Mock(return_value=True),
    )


def deliver(db, players, api=None):
    api = api or transport()
    for _ in range(100):
        if not service.dispatch_one(api, 1, context(players)):
            break
    return api


def confirm(db, players, incident):
    vid = incident["leadership_vote"]["id"]
    deliver(db, players)
    db.clock.now += 1
    assert storage.ballot(1, "v0", True, db.clock.now, players, "round-1")
    assert vote(db, vid)["status"] == "warning"
    deliver(db, players)
    return vid


def activate(db, n=6, commander=False, mode="dry_run"):
    storage.configure(1, Config(enabled=True, mode=mode), "tester")
    players = roster(n, commander)
    observe_for(db, players)
    incident = report(
        players,
        text=(
            "!admin commander is not talking"
            if commander
            else "!admin able redet nicht"
        ),
    )
    vid = confirm(db, players, incident)
    elapse(db, players, 60)
    storage.advance(1, context(players))
    deliver(db, players)
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "active"
    return vid, players


def cast(db, players, pid="v0", yes=True):
    db.clock.now += 0.1
    return storage.ballot(1, pid, yes, db.clock.now, players, "round-1")


@pytest.mark.parametrize(
    "text",
    [
        "!admin able redet nicht",
        "!admin Able is not talking",
        "!admin able spricht nicht",
        "!admin able doesn't communicate",
    ],
)
def test_explicit_communication_reports(db, text):
    players = roster()
    observe_for(db, players)
    result = report(players, text)
    assert result["leadership_vote"]["target_id"] == "target"
    assert result["leadership_vote"]["phase"] == "confirming"
    assert result["status"] == "new"


@pytest.mark.parametrize("alias", ["commander", "kommandant", "kommandeur"])
def test_commander_target_and_only_squadleader_voters(db, alias):
    players = roster(commander=True)
    observe_for(db, players)
    incident = report(players, f"!admin {alias} is not talking")
    vid = confirm(db, players, incident)
    result = vote(db, vid)
    assert result["target_role"] == "commander"
    assert len(result["electorate"]) == 6
    assert all(
        p["identity"]["kind"] == "squadleader" for p in result["electorate"].values()
    )


@pytest.mark.parametrize(
    "text",
    [
        "!admin able",
        "!admin able sabotiert",
        "!admin able redet nicht?",
        "!admin able redet wieder",
        "!admin able is not talking anymore",
        "!admin able und Squad-1 redet nicht",
        "!admin Person-v1 redet nicht",
    ],
)
def test_ambiguous_or_other_reports_stay_ordinary(db, text):
    observe_for(db, roster())
    assert not report(text=text)["leadership_vote"]


@pytest.mark.parametrize("role", sorted(incidents.SQUAD_LEADER_ROLES))
def test_all_hll_and_vietnam_leadership_roles(role):
    p = player("p", role=role)
    assert domain.identity(p)["kind"] == (
        "commander" if role in incidents.COMMANDER_ROLES else "squadleader"
    )


@pytest.mark.parametrize("role", ["Commander", "ArmyCommander"])
def test_commander_roles(role):
    assert domain.identity(player("p", role=role))["kind"] == "commander"


@pytest.mark.parametrize(
    "raw,expected",
    [
        (" !YeS ", True),
        ("!NO", False),
        ("!yes please", None),
        ("!no x", None),
        ("yes", None),
        ("!yes\n!no", None),
    ],
)
def test_exact_answers(raw, expected):
    assert domain.answer(raw) is expected


@pytest.mark.parametrize(
    "channel,expected",
    [
        ("CHAT[Allies][Team]", True),
        ("CHAT[Allies][Unit]", True),
        ("CHAT[Axis][Team]", False),
        ("CHAT[Allies][Global]", False),
        ("CHAT", False),
        ("", False),
    ],
)
def test_private_channels_match_team(channel, expected):
    assert domain.private_chat({"action": channel}, "allies") is expected


def test_no_history_no_offer_and_gap_resets_tenure(db):
    players = roster()
    assert not report(players)["leadership_vote"]
    observe_for(db, players, 295)
    assert not report(players)["leadership_vote"]
    elapse(db, players, 5)
    assert report(players)["leadership_vote"]
    storage.recover(1)
    db.clock.now += 20
    storage.observe(1, context(players))
    assert not report(players)["leadership_vote"]


@pytest.mark.parametrize("reporter", ["target", "member"])
def test_target_and_target_squad_cannot_start(db, reporter):
    observe_for(db, roster())
    assert not report(reporter=reporter)["leadership_vote"]


def test_commander_may_start_against_squadleader_but_not_self(db):
    players = roster()
    observe_for(db, players)
    assert report(players, reporter="v5")["leadership_vote"]
    assert not report(players, "!admin commander redet nicht", reporter="v5")[
        "leadership_vote"
    ]


def test_unknown_and_global_reports_are_never_offered(db):
    observe_for(db, roster())
    assert not report(private=False)["leadership_vote"]
    assert not report(stamp=NOW - 31)["leadership_vote"]


def test_one_flow_per_team_server_scope_and_opposition_excluded(db):
    players = roster() + [player("enemy", squad="Able", team="axis")]
    observe_for(db, players)
    first = report(players)
    assert first["leadership_vote"]
    assert not report(players)["leadership_vote"]
    assert not report(players, server=2)["leadership_vote"]
    vid = confirm(db, players, first)
    assert "enemy" not in vote(db, vid)["electorate"]


def test_confirmation_not_ballot_warning_withdraw_and_cooldown(db):
    players = roster()
    observe_for(db, players)
    vid = confirm(db, players, report(players))
    assert vote(db, vid)["yes"] == 0
    assert not cast(db, players, "target")
    assert cast(db, players, yes=False)
    assert vote(db, vid)["status"] == "cancelled"
    assert not report(players)["leadership_vote"]


def test_confirmation_timeout_or_decline_does_not_trigger_cooldown(db):
    players = roster()
    observe_for(db, players)
    first = report(players)
    deliver(db, players)
    assert cast(db, players, yes=False)
    assert report(players)["leadership_vote"]
    elapse(db, players, 60)
    storage.advance(1, context(players))
    assert report(players)["leadership_vote"]
    assert vote(db, first["leadership_vote"]["id"])["status"] == "cancelled"


@pytest.mark.parametrize("n,required", [(3, 2), (4, 3), (6, 4), (8, 5)])
def test_majority_full_duration_and_dry_run_no_kick(db, n, required, monkeypatch):
    vid, players = activate(db, n)
    assert vote(db, vid)["required"] == required
    for i in range(required):
        assert cast(db, players, f"v{i}")
    assert storage.advance(1, context(players)) == []
    assert vote(db, vid)["status"] == "active"
    elapse(db, players, 120)
    assert storage.advance(1, context(players)) == []
    assert vote(db, vid)["status"] == "dry_run"
    with db() as sess:
        assert sess.scalar(select(AdminIncident)).status == "new"
    api = transport()
    monkeypatch.setattr(service, "read_context", lambda _: context(players))
    service.execute(api, 1, vote(db, vid))
    api.kick.assert_not_called()


def test_latest_ballot_duplicate_late_votes_and_abstentions(db):
    vid, players = activate(db, 6)
    assert cast(db, players)
    assert not storage.ballot(1, "v0", False, db.clock.now, players, "round-1")
    assert cast(db, players, yes=False)
    assert vote(db, vid)["yes"] == 0 and vote(db, vid)["no"] == 1
    assert not cast(db, players, "member")
    elapse(db, players, 120)
    assert not cast(db, players)
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "rejected"


def test_electorate_frozen_role_loss_removes_ballot_never_lowers_threshold(db):
    vid, players = activate(db, 6)
    assert cast(db, players)
    players = deepcopy(players)
    next(p for p in players if p["player_id"] == "v0")["role"] = "Rifleman"
    players.append(player("new", squad="New"))
    storage.observe(1, context(players))
    storage.advance(1, context(players))
    result = vote(db, vid)
    assert result["required"] == 4 and result["yes"] == 0
    assert not result["electorate"]["v0"]["valid"] and "new" not in result["electorate"]
    next(p for p in players if p["player_id"] == "v0")["role"] = "Officer"
    storage.observe(1, context(players))
    assert not cast(db, players)
    assert not cast(db, players, "new")


@pytest.mark.parametrize("commander", [False, True])
@pytest.mark.parametrize(
    "change", ["role", "team", "disconnect", "successor", "reconnect", "squad"]
)
def test_target_identity_and_session_cannot_transfer(db, commander, change):
    vid, players = activate(db, commander=commander)
    players = deepcopy(players)
    target = players[0]
    if change == "role":
        target["role"] = "Rifleman"
    if change == "team":
        target["team"] = "axis"
    if change == "squad":
        if commander:
            target["role"] = "Officer"
        target["unit_name"] = "New"
    if change == "disconnect":
        players.pop(0)
    if change == "successor":
        target["player_id"] = "successor"
    if change == "reconnect":
        storage.end_for_event(1, db.clock.now, "target")
    storage.observe(1, context(players))
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "cancelled"


def test_less_than_three_valid_cancels(db):
    vid, players = activate(db, 3)
    storage.end_for_event(1, db.clock.now, "v0")
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "cancelled"


@pytest.mark.parametrize("kind", ["stale", "round", "restart", "disable"])
def test_faults_cancel_without_retry(db, kind):
    vid, players = activate(db)
    if kind == "restart":
        storage.recover(1)
    elif kind == "disable":
        storage.configure(1, Config(), "admin")
    elif kind == "round":
        storage.advance(1, context(players, "next-round"))
    else:
        ctx = context(players)
        ctx["captured_at"] -= 11
        storage.advance(1, ctx)
    assert vote(db, vid)["status"] == "cancelled"


@pytest.mark.parametrize(
    "operation", ["claim", "link_target", "cancel_leadership_vote"]
)
def test_admin_takes_over(db, operation):
    vid, _ = activate(db)
    with db() as sess:
        incident = sess.scalar(select(AdminIncident)).to_dict()
    incidents.mutate_incident(
        incident["id"],
        actor="admin",
        expected_revision=incident["revision"],
        operation=operation,
        payload={"target_id": "someone", "target_name": "Other"},
    )
    assert vote(db, vid)["status"] == "cancelled"


def test_admin_subject_edit_cancels(db):
    vid, _ = activate(db)
    with db() as sess:
        incident = sess.scalar(select(AdminIncident)).to_dict()
    incidents.mutate_incident_subject(
        incident["id"],
        actor="admin",
        expected_revision=incident["revision"],
        operation="reject",
        payload={},
        subject_id=incident["subjects"][0]["id"],
        idempotency_key="reject-1",
    )
    assert vote(db, vid)["status"] == "cancelled"


def ready_to_kick(db):
    vid, players = activate(db, 3, mode="active")
    cast(db, players, "v0")
    cast(db, players, "v1")
    elapse(db, players, 120)
    job = storage.advance(1, context(players))[0]
    return vid, players, job


@pytest.mark.parametrize(
    "response", [True, False, None, "SUCCESS", TimeoutError("uncertain")]
)
def test_at_most_one_kick_and_only_confirmed_success_resolves(
    db, monkeypatch, response
):
    vid, players, job = ready_to_kick(db)
    api = transport()
    if isinstance(response, Exception):
        api.kick.side_effect = response
    else:
        api.kick.return_value = response
    monkeypatch.setattr(service, "read_context", lambda _: context(players))
    service.execute(api, 1, job)
    service.execute(api, 1, job)
    assert api.kick.call_count == 1
    result = vote(db, vid)
    assert result["status"] == ("kicked" if response is True else "unknown")
    with db() as sess:
        assert sess.scalar(select(AdminIncident)).status == (
            "resolved" if response is True else "new"
        )


def test_final_validation_role_change_or_admin_takeover_prevents_send(db, monkeypatch):
    vid, players, job = ready_to_kick(db)
    storage.cancel(1, vid, "admin")
    api = transport()
    monkeypatch.setattr(service, "read_context", lambda _: context(players))
    service.execute(api, 1, job)
    api.kick.assert_not_called()


def test_started_send_blocks_manual_action_and_restart_marks_unknown(db):
    vid, players, job = ready_to_kick(db)
    assert storage.begin_send(1, vid, context(players))
    with pytest.raises(incidents.IncidentConflict):
        storage.cancel(1, vid, "admin")
    assert not storage.begin_send(1, vid, context(players))
    storage.recover(1)
    assert vote(db, vid)["status"] == "unknown"


def test_delivery_failure_never_retries_or_discloses_to_enemy(db):
    players = roster()
    observe_for(db, players)
    incident = report(players)
    api = transport()
    api.message_player.return_value = None
    deliver(db, players, api)
    deliver(db, players, api)
    assert api.message_player.call_count == 1
    assert not cast(db, players)
    elapse(db, players, 60)
    storage.advance(1, context(players))
    next(p for p in players if p["player_id"] == "v0")["team"] = "axis"
    deliver(db, players, api)
    assert api.message_player.call_count == 1


def test_command_conflicts_reject_activation(db):
    storage.configure(1, Config(), "admin")
    with db() as sess:
        sess.add(
            UserConfig(
                key="1_ChatCommandsUserConfig",
                value={"enabled": True, "command_words": [{"words": ["!YES"]}]},
            )
        )
    with pytest.raises(ValueError, match="Konflikt"):
        storage.configure(1, Config(enabled=True), "admin")


def test_db_enqueue_fault_preserves_ordinary_report(db, monkeypatch):
    monkeypatch.setattr(
        storage, "enqueue", Mock(side_effect=RuntimeError("DB failure"))
    )
    incident = report()
    assert incident["status"] == "new" and not incident["leadership_vote"]


def test_messages_are_bilingual_named_and_explicitly_dry(db):
    vid, players = activate(db)
    with db() as sess:
        items = list(sess.scalars(select(LeadershipMessage)))
    assert items
    assert all(
        "Person-target" in m.body
        and "DRY RUN" in m.body
        and "kein automatischer Kick" in m.body
        for m in items
    )
    invites = [m for m in items if m.purpose == "invite"]
    assert {m.player_id for m in invites} == {f"v{i}" for i in range(6)}
    assert all(
        "!yes" in m.body and "!no" in m.body and "120" in m.body for m in invites
    )


def test_no_warning_before_initial_discord_delivery(db, monkeypatch):
    players = roster()
    observe_for(db, players)
    incident = report(players)
    vid = incident["leadership_vote"]["id"]
    deliver(db, players)
    monkeypatch.setattr(storage, "report_delivered", lambda sess, v: False)
    assert cast(db, players)
    assert vote(db, vid)["status"] == "cancelled"
    with db() as sess:
        assert not sess.scalar(
            select(LeadershipMessage.id).where(LeadershipMessage.purpose == "target")
        )


def test_discord_disabled_cancels_and_cannot_be_enabled(db, monkeypatch):
    vid, players = activate(db)
    monkeypatch.setattr(storage, "discord_ready", lambda sess: False)
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "cancelled"
    with pytest.raises(ValueError, match="Discord"):
        storage.configure(1, Config(enabled=True), "admin")


def test_discord_readiness_requires_real_connection_metadata(db, monkeypatch):
    from sqlalchemy import text

    monkeypatch.setenv("DISCORD_REPORTS_ENABLED", "1")
    with db() as sess:
        sess.execute(
            text(
                "CREATE TABLE api_discordreportintegration (id INT, enabled BOOL, "
                "service_url TEXT, channel_id TEXT, moderator_role_ids TEXT, outbound_capability_ciphertext BLOB)"
            )
        )
        sess.execute(
            text(
                "INSERT INTO api_discordreportintegration VALUES (1, 1, "
                "'https://example.invalid', '123', '[\"456\"]', :cipher)"
            ),
            {"cipher": b""},
        )
        assert not REAL_DISCORD_READY(sess)
        sess.execute(
            text(
                "UPDATE api_discordreportintegration SET outbound_capability_ciphertext=:cipher"
            ),
            {"cipher": b"synthetic-encrypted-test-value"},
        )
        assert REAL_DISCORD_READY(sess)
        monkeypatch.setenv("DISCORD_REPORTS_ENABLED", "0")
        assert not REAL_DISCORD_READY(sess)


def test_initial_report_delivery_confirmation_uses_durable_outbox(db):
    from rcon.models import AdminIncidentDiscordDelivery

    observe_for(db, roster())
    incident = report()
    with db() as sess:
        AdminIncidentDiscordDelivery.__table__.create(sess.bind)
        v = sess.get(LeadershipVote, incident["leadership_vote"]["id"])
        assert not REAL_REPORT_DELIVERED(sess, v)
        event = sess.scalar(
            select(AdminIncidentEvent).where(
                AdminIncidentEvent.incident_id == incident["id"],
                AdminIncidentEvent.event_type == "created",
            )
        )
        sess.add(
            AdminIncidentDiscordDelivery(
                event_id=event.id,
                delivered_at=datetime.fromtimestamp(NOW, timezone.utc),
            )
        )
        sess.flush()
        assert REAL_REPORT_DELIVERED(sess, v)


def test_reserved_commands_cannot_be_added_while_enabled(db):
    with db() as sess:
        with pytest.raises(ValueError, match="reserviert"):
            storage.guard_command_config(
                sess,
                "1_ChatCommandsUserConfig",
                {"enabled": True, "command_words": [{"words": ["!no"]}]},
            )
        storage.guard_command_config(
            sess,
            "2_ChatCommandsUserConfig",
            {"enabled": True, "command_words": [{"words": ["!no"]}]},
        )


def test_ambiguous_commander_or_duplicate_leadership_seat(db):
    players = roster(commander=True) + [player("other", role="Commander", squad="")]
    observe_for(db, players)
    assert not report(players, "!admin commander redet nicht")["leadership_vote"]


def test_ineligible_reporter_role_changed_during_confirmation(db):
    players = roster()
    observe_for(db, players)
    incident = report(players)
    deliver(db, players)
    next(p for p in players if p["player_id"] == "v0")["unit_name"] = "New"
    storage.observe(1, context(players))
    assert cast(db, players)
    assert vote(db, incident["leadership_vote"]["id"])["status"] == "cancelled"


def test_ambiguous_target_after_confirmation_cancels(db):
    vid, players = activate(db, commander=True)
    players.append(player("duplicate-commander", role="Commander", squad=""))
    storage.observe(1, context(players))
    storage.advance(1, context(players))
    assert vote(db, vid)["status"] == "cancelled"


def test_forged_actor_cannot_bypass_manual_action_guard(db):
    vid, players, _ = ready_to_kick(db)
    assert storage.begin_send(1, vid, context(players))
    with pytest.raises(incidents.IncidentConflict):
        storage.before_manual_action("target", "system:leadership-vote")
    with storage.automatic_action():
        storage.before_manual_action("target", "system:leadership-vote")
    with pytest.raises(incidents.IncidentConflict):
        storage.before_manual_action("target", "admin")
