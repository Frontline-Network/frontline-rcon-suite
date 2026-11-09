"""Semantic routing with stubbed model output, never real AI or game actions."""

import pytest
from sqlalchemy import select

from tests.test_report_admin import setup, db, service, current, report, transport
from rcon import report_reason
from rcon.models import AdminIncidentEvent, PlayerSession, PlayerID
from rcon.user_config.report_admin import ReportAdminUserConfig as Config


@pytest.fixture
def semantic(setup):
    service.configure(1, Config(enabled=True, mode="active", reason_mode="ai"))
    return setup


def decision(
    target="BattlefieldHero", excerpt="never answers us in command chat", **changes
):
    return {
        "rule": "communication",
        "target_kind": "player",
        "target_text": target,
        "allegation_excerpt": excerpt,
        "unambiguous": True,
        "uncertainties": [],
        "rationale": "Current allegation of missing leadership communication.",
        **changes,
    }


def complete(setup, iid, result, status="done"):
    with setup[0]() as sess:
        event = sess.scalar(
            select(AdminIncidentEvent).where(
                AdminIncidentEvent.incident_id == iid,
                AdminIncidentEvent.event_type == "report_admin",
            )
        )
        event.payload = {
            **event.payload,
            "reason_request": {
                **event.payload["reason_request"],
                "status": status,
                "analysis": {
                    "decision": result,
                    "model": "configured-model",
                    "prompt_version": "report-reason-1",
                },
            },
        }


def test_whole_reason_not_keyword_gate_and_no_action_during_analysis(semantic):
    message = "!admin BattlefieldHero never answers us in command chat; he is back after reconnecting"
    i = report(semantic, message)
    assert i["report_admin"]["status"] == "classifying"
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    complete(semantic, i["id"], decision())
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(semantic[0], i["id"])["report_admin"]["status"] == "queued"
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "target"
    assert current(semantic[0], i["id"])["report_admin"]["reason_analysis"]["decision"][
        "rationale"
    ]


@pytest.mark.parametrize(
    "fragment", ["BattlefielxHero", "BattlexielxHero", "BattlexielxHera"]
)
def test_model_preserves_typo_local_roster_resolves_it(semantic, fragment):
    i = report(semantic, f"!admin {fragment} never answers us in command chat")
    complete(semantic, i["id"], decision(target=fragment))
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "target"


@pytest.mark.parametrize(
    "result,status",
    [
        (
            decision(rule="manual", unambiguous=False, uncertainties=["Retracted"]),
            "done",
        ),
        (decision(unambiguous=False), "done"),
        (decision(uncertainties=["Two possible targets"]), "done"),
        (decision(target="invented-player"), "done"),
        (decision(excerpt="invented evidence"), "done"),
        (decision(target="!admin BattlefieldHero"), "done"),
        (decision(excerpt="BattlefieldHero"), "done"),
        (decision(action="kick"), "done"),
        (decision(rule="ban"), "done"),
        (decision(), "failed"),
    ],
)
def test_unsafe_or_unavailable_interpretation_never_falls_back(
    semantic, result, status
):
    i = report(
        semantic, "!admin BattlefieldHero redet nicht; never answers us in command chat"
    )
    complete(semantic, i["id"], result, status)
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(semantic[0], i["id"])["report_admin"]["status"] == "manual"


@pytest.mark.parametrize(
    "change",
    [
        "offline",
        "opponent",
        "nonleader",
        "twin",
        "team_switch",
        "role_change",
        "reconnect",
        "map",
        "stale",
        "expired",
        "config",
        "takeover",
        "recovery",
        "player_action",
        "reporter_reconnect",
    ],
)
def test_model_never_overrides_live_guards(semantic, change):
    database, players, ctx = semantic
    if change == "offline":
        players[0]["online"] = False
    if change == "opponent":
        players[0]["team"] = "axis"
    if change == "nonleader":
        players[0]["role"] = "Rifleman"
    if change == "twin":
        players[1]["name"] = "BattlefieldHero"
    i = report(semantic, "!admin BattlefieldHero never answers us in command chat")
    complete(semantic, i["id"], decision())
    if change == "team_switch":
        players[0]["team"] = "axis"
    if change == "role_change":
        players[0]["role"] = "Rifleman"
    if change in {"reconnect", "reporter_reconnect"}:
        pid = "target" if change == "reconnect" else "v0"
        with database() as sess:
            row = sess.scalar(
                select(PlayerSession).join(PlayerID).where(PlayerID.player_id == pid)
            )
            row.start = service.utc(database.clock.now + 1).replace(tzinfo=None)
        database.clock.now += 2
    if change == "map":
        ctx["round_id"] = "new-map"
    if change == "stale":
        ctx["captured_at"] -= 20
    if change == "expired":
        database.clock.now += 61
        ctx["captured_at"] = database.clock.now
    if change == "config":
        service.configure(1, Config())
    if change == "takeover":
        with database() as sess:
            event = sess.scalar(
                select(AdminIncidentEvent).where(
                    AdminIncidentEvent.event_type == "report_admin"
                )
            )
            event.incident.assigned_to = "human-admin"
    if change == "recovery":
        service.recover(1)
    if change == "player_action":
        with database() as sess:
            service.cancel_player(sess, 1, "target")
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(database, i["id"])["report_admin"]["status"] == "manual"


def test_ai_mode_is_server_local_and_does_not_replay_reports(setup):
    i = report(setup, "!admin BattlefieldHero never answers us in command chat")
    assert i["report_admin"] is None
    service.configure(2, Config(enabled=True, reason_mode="ai"))
    with setup[0]() as sess:
        assert service.config(sess, 1).reason_mode == "rules"
    service.configure(1, Config(enabled=True, reason_mode="ai"))
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()


def test_dry_run_never_kicks(semantic):
    service.configure(1, Config(enabled=True, mode="dry_run", reason_mode="ai"))
    i = report(semantic, "!admin BattlefieldHero never answers us in command chat")
    complete(semantic, i["id"], decision())
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(semantic[0], i["id"])["report_admin"]["status"] == "dry_run"


def test_wire_contracts_match():
    from rcon.report_reason_contract import ReportReasonDecision, ReportReasonRequest
    from discord_service.app.report_reason_contract import (
        ReportReasonDecision as RemoteDecision,
        ReportReasonRequest as RemoteRequest,
    )

    assert (
        ReportReasonDecision.model_json_schema() == RemoteDecision.model_json_schema()
    )
    assert ReportReasonRequest.model_json_schema() == RemoteRequest.model_json_schema()


@pytest.mark.parametrize(
    "reference,kind,pid",
    [("able", "squad", "target"), ("commander", "commander", "v5")],
)
def test_semantic_squad_and_commander_references_remain_supported(
    semantic, reference, kind, pid
):
    i = report(semantic, f"!admin {reference} never answers us in command chat")
    complete(semantic, i["id"], decision(target=reference, target_kind=kind))
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == pid


def test_model_cannot_replace_missing_named_player_with_squadleader(semantic):
    i = report(semantic, "!admin able never answers us in command chat")
    complete(semantic, i["id"], decision(target="able", target_kind="player"))
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_not_called()


@pytest.mark.parametrize("rule", ["teamkills", "cheating"])
def test_semantic_accusation_is_not_evidence_for_sanctions(semantic, rule):
    service.configure(
        1, Config(enabled=True, mode="active", reason_mode="ai", cheating=True)
    )
    excerpt = (
        "is shooting his own team" if rule == "teamkills" else "is using wallhacks"
    )
    i = report(semantic, f"!admin BattlefieldHero {excerpt}")
    complete(semantic, i["id"], decision(rule=rule, excerpt=excerpt))
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(semantic[0], i["id"])["report_admin"]["status"] == "manual"


def test_similar_live_names_stay_manual_even_when_model_is_certain(semantic):
    semantic[1][1]["name"] = "BattlefieldHera"
    i = report(semantic, "!admin BattlefieldHere never answers us in command chat")
    complete(semantic, i["id"], decision(target="BattlefieldHere"))
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_not_called()


@pytest.mark.parametrize("pid", ["v0", "v1", "not-in-roster"])
@pytest.mark.parametrize("stage", ["pending", "done", "queued"])
def test_unrelated_player_action_never_cancels_report(semantic, pid, stage):
    i = report(semantic, "!admin BattlefieldHero never answers us in command chat")
    api = transport()
    if stage != "pending":
        complete(semantic, i["id"], decision())
    if stage == "queued":
        service.tick(api, 1)
    with semantic[0]() as sess:
        service.cancel_player(sess, 1, pid, actor="unrelated-action")
    if stage == "pending":
        complete(semantic, i["id"], decision())
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()


def test_intervention_before_unknown_typo_target_is_bound_still_wins(semantic):
    fragment = "BattlexielxHera"
    i = report(semantic, f"!admin {fragment} never answers us in command chat")
    assert not i["target_id"]
    with semantic[0]() as sess:
        service.cancel_player(sess, 1, "target", actor="moderator")
    complete(semantic, i["id"], decision(target=fragment))
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert (
        "Target intervention" in current(semantic[0], i["id"])["report_admin"]["result"]
    )


@pytest.mark.parametrize(
    "server,pid,kicked", [(2, "target", True), (1, None, False), (1, "target", False)]
)
def test_intervention_scope_and_server_wide_changes(semantic, server, pid, kicked):
    i = report(semantic, "!admin BattlefieldHero never answers us in command chat")
    with semantic[0]() as sess:
        service.cancel_player(sess, server, pid)
    complete(semantic, i["id"], decision())
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    assert api.kick.called is kicked


def test_final_role_change_keeps_bounded_diagnostics(semantic):
    i = report(semantic, "!admin BattlefieldHero never answers us in command chat")
    complete(semantic, i["id"], decision())
    api = transport()
    service.tick(api, 1)
    semantic[1][0]["role"] = "Rifleman"
    service.tick(api, 1)
    api.kick.assert_not_called()
    with semantic[0]() as sess:
        event = sess.scalar(
            select(AdminIncidentEvent).where(
                AdminIncidentEvent.event_type == "report_admin"
            )
        )
        evidence = event.payload["guard_diagnostics"]
        assert evidence["expected_seat"]["kind"] == "squadleader"
        assert evidence["observed_seat"] is None


def test_reviewed_commander_typo_is_resolved_without_correcting_model_excerpt(semantic):
    i = report(semantic, "!admin kommder never answers us in command chat")
    complete(semantic, i["id"], decision(target="kommder", target_kind="commander"))
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "v5"


@pytest.mark.parametrize("squad", ["jig", "how", "baker", "juliett", "Eagles"])
def test_bare_squad_communication_means_own_team_leader(semantic, squad):
    leader = semantic[1][0]
    leader.update(role="squadleader", unit_name=squad)
    semantic[1].append({**leader, "player_id": "opponent", "team": "axis"})
    i = report(semantic, f"!admin {squad} not talking")
    complete(
        semantic,
        i["id"],
        decision(target=squad, target_kind="squad", excerpt="not talking"),
    )
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "target"


@pytest.mark.parametrize("self_allowed", [True, False])
def test_bare_jig_report_by_own_leader_keeps_self_report_setting(
    semantic, self_allowed
):
    service.configure(
        1,
        Config(
            enabled=True,
            mode="active",
            reason_mode="ai",
            allow_self_reports=self_allowed,
        ),
    )
    semantic[1][0].update(role="squadleader", unit_name="jig")
    i = report(semantic, "!admin jig not talking", reporter_id="target")
    complete(
        semantic,
        i["id"],
        decision(target="jig", target_kind="squad", excerpt="not talking"),
    )
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    assert api.kick.called is self_allowed


@pytest.mark.parametrize(
    "squad,reference,similar",
    [
        ("charlie", "charlie", "Charli"),
        ("papa", "peter", "Petr"),
        ("JULIETTE", "jig", "Jigg"),
    ],
)
def test_current_squad_names_with_fuzzy_noise_complete_once(
    semantic, squad, reference, similar
):
    semantic[1][0].update(role="squadleader", unit_name=squad)
    semantic[1][2]["name"] = similar
    i = report(semantic, f"!admin {reference} not talking")
    complete(
        semantic,
        i["id"],
        decision(target=reference, target_kind="squad", excerpt="not talking"),
    )
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "target"
    assert current(semantic[0], i["id"])["report_admin"]["status"] == "kicked"


def test_explicit_named_player_is_not_replaced_by_matching_squad(semantic):
    semantic[1][0].update(role="squadleader", unit_name="charlie")
    semantic[1][2]["name"] = "Charli"
    i = report(semantic, "!admin charlie not talking")
    complete(
        semantic,
        i["id"],
        decision(target="charlie", target_kind="player", excerpt="not talking"),
    )
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    api.kick.assert_not_called()
    assert current(semantic[0], i["id"])["report_admin"]["status"] == "manual"


def test_realpb7_report_with_unchanged_roster_completes_once(semantic):
    """Replay the recorded wording/roles, not an invented historical live roster."""
    service.configure(
        1,
        Config(
            enabled=True,
            mode="active",
            reason_mode="ai",
            communication_squad_members=True,
            allow_self_reports=True,
        ),
    )
    semantic[1][0].update(
        name="realpb7", role="squadleader", unit_name="golf", unit_id=6
    )
    reporter = next(p for p in semantic[1] if p["player_id"] == "v0")
    reporter.update(name="Jolly Jumper", role="engineer", unit_name="golf", unit_id=6)
    i = report(semantic, "!admin REALPB7 not communicating")
    complete(
        semantic,
        i["id"],
        decision(target="REALPB7", excerpt="REALPB7 not communicating"),
    )
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "target"


@pytest.mark.parametrize(
    "change,code",
    [
        ("gone", "live_target_unresolved"),
        ("duplicate", "live_target_unresolved"),
        ("seat", "target_identity_changed"),
        ("invalid", "invalid_interpretation_or_roster"),
        ("invented", "ungrounded_interpretation"),
    ],
)
def test_classification_failure_retains_specific_bounded_evidence(
    semantic, change, code
):
    i = report(semantic, "!admin BattlefieldHero never answers us in command chat")
    complete(
        semantic,
        i["id"],
        decision(
            **(
                {"action": "kick"}
                if change == "invalid"
                else {"target": "invented"} if change == "invented" else {}
            )
        ),
    )
    if change == "gone":
        semantic[1][0]["online"] = False
    elif change == "duplicate":
        semantic[1].append(dict(semantic[1][0]))
    elif change == "seat":
        semantic[1][0].update(unit_name="new-squad", unit_id=99)
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    api.kick.assert_not_called()
    result = current(semantic[0], i["id"])["report_admin"]
    audit = result["reason_analysis"]["target_check"]
    assert result["status"] == "manual"
    assert audit["code"] == code
    assert "roster" not in audit
    assert "BattlefieldHero" not in str(audit)
    if change == "gone":
        assert audit["original"]["target"]["online"] is True
        assert audit["current"]["target"]["online"] is False
    elif change == "duplicate":
        assert audit["current"]["duplicate_ids"] == 1
        assert audit["current"]["target"]["matches"] == 2
    elif change == "seat":
        assert audit["changed_fields"] == ["seat"]


def test_reporter_temporarily_without_squad_stops_and_records_cause(semantic):
    i = report(semantic, "!admin BattlefieldHero never answers us in command chat")
    complete(semantic, i["id"], decision())
    reporter = next(p for p in semantic[1] if p["player_id"] == "v0")
    reporter.update(role="rifleman", unit_name="unassigned", unit_id=0)
    api = transport()
    service.tick(api, 1)
    result = current(semantic[0], i["id"])["report_admin"]
    audit = result["reason_analysis"]["target_check"]
    assert result["status"] == "manual"
    assert "Reporter" in result["result"]
    assert audit["code"] == "reporter_squad_unassigned"
    assert audit["original"]["target"] == audit["current"]["target"]
    assert audit["current"]["reporter"]["squad"] == "unassigned"
    reporter.update(unit_name="november", unit_id=13)
    service.tick(api, 1)
    api.kick.assert_not_called()  # Never replay an already handed-off report.
