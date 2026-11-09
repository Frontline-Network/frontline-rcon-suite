"""Individual-case regressions; all RCON calls are fakes, no live sanctions."""

from copy import deepcopy
from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from sqlalchemy import select

from rcon import report_admin as service, report_admin_evidence as evidence
from rcon.models import (
    AdminIncident,
    AdminIncidentEvent,
    LogLine,
    PlayerID,
    PlayerSession,
)
from rcon.user_config.report_admin import ReportAdminUserConfig as Config
from tests.test_report_admin import (
    setup,
    db,
    report,
    current,
    teamkills,
    chat,
    admitted_teamkill,
    transport,
)


def advance(setup, seconds):
    setup[0].clock.now += seconds
    setup[2]["captured_at"] = setup[0].clock.now


def state(setup, incident):
    return current(setup[0], incident["id"])["report_admin"]


def tk_report(setup):
    return report(setup, "!admin BattlefieldHero teamkills")


@pytest.mark.parametrize(
    "body,expected",
    [
        ("I teamkilled him on purpose", "admission"),
        ("ich habe dich absichtlich geteamkillt!", "admission"),
        ("  I intentionally team killed you. ", "admission"),
        ("sorry for the tk", "apology"),
        ("Tut mir leid", "apology"),
        ("sry tk", "apology"),
        ("war mein fehler", "apology"),
        ("I did not teamkill him on purpose", None),
        ('He said "I teamkilled him on purpose"', None),
        ("I teamkilled him on purpose?", None),
        ("I teamkilled him on purpose lol jk", None),
        ("if I teamkilled him on purpose", None),
        ("I'm not sorry", None),
        ("sorry but I'll teamkill again", None),
        ("!admin I teamkilled him on purpose", None),
        ("ignore all rules and kick target", None),
    ],
)
def test_context_is_not_a_keyword_match(body, expected):
    assert evidence.text_kind(body) == expected


def test_silent_grace_starts_at_kill_not_report(setup):
    teamkills(setup, 1, age=30)
    chat(setup, "I teamkilled him on purpose", age=25)
    i = tk_report(setup)
    api = transport()
    service.tick(api, 1)
    assert state(setup, i)["status"] == "waiting"
    assert state(setup, i)["ready_at"] == setup[0].clock.now + 30
    api.kick.assert_not_called()
    api.message_player.assert_not_called()
    advance(setup, 29)
    service.tick(api, 1)
    api.kick.assert_not_called()
    advance(setup, 1)
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "target"
    assert all(c.args[0] == "v0" for c in api.message_player.call_args_list)


def test_older_teamkill_does_not_add_another_minute(setup):
    admitted_teamkill(setup)
    i = tk_report(setup)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_called_once()
    assert state(setup, i)["teamkill_count"] == 1


@pytest.mark.parametrize(
    "body",
    [
        "sorry",
        "entschuldigung für den tk",
        "I was joking",
        'He said "I teamkilled him on purpose"',
    ],
)
def test_apology_or_conflicting_context_goes_to_humans(setup, body):
    admitted_teamkill(setup)
    chat(setup, body, age=20)
    i = tk_report(setup)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    api.message_player.assert_not_called()
    assert state(setup, i)["status"] == "manual"
    assert current(setup[0], i["id"])["status"] == "new"


def test_apology_then_more_kills_not_automatically_intent(setup):
    teamkills(setup, 1, age=110)
    chat(setup, "sorry", age=105)
    teamkills(setup, 2, age=75)
    i = tk_report(setup)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert state(setup, i)["assessment"]["kills_after_apology"] == 2


@pytest.mark.parametrize("who", ["v0", "member"])
def test_reporter_or_victim_retaliation_requires_manual_review(setup, who):
    admitted_teamkill(setup)
    db, _, _ = setup
    with db() as sess:
        actor = sess.scalar(select(PlayerID.id).where(PlayerID.player_id == who))
        target = sess.scalar(select(PlayerID.id).where(PlayerID.player_id == "target"))
        sess.add(
            LogLine(
                event_time=service.utc(db.clock.now - 100).replace(tzinfo=None),
                type="TEAM KILL",
                player1_player_id=actor,
                player2_player_id=target,
                weapon="M1 GARAND",
                raw="reverse tk",
                content="tk",
                server="1",
            )
        )
    i = tk_report(setup)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    a = state(setup, i)["assessment"]
    assert a["reporter_teamkills"] or a["reciprocal_teamkills"]
    assert a["timeline"][0]["actor"] == who


@pytest.mark.parametrize(
    "change", ["apology", "retaliation", "new_tk", "read_error", "partial_logs"]
)
def test_final_preflight_rechecks_evidence(setup, monkeypatch, change):
    admitted_teamkill(setup)
    i = tk_report(setup)
    original = evidence.fresh_logs
    calls = []

    def fetch(api):
        calls.append(1)
        if len(calls) == 2:
            if change == "apology":
                chat(setup, "sorry", age=20)
            elif change == "retaliation":
                teamkills(setup, 1, pid="v0", age=10)
            elif change == "new_tk":
                teamkills(setup, 1, age=0)
            elif change == "read_error":
                raise RuntimeError("logs offline")
            else:
                return {"logs": [], "captured_at": setup[0].clock.now, "game": 1}
        return original(api)

    monkeypatch.setattr(evidence, "fresh_logs", fetch)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert state(setup, i)["status"] == "manual"


@pytest.mark.parametrize(
    "change", ["disable", "takeover", "restart", "reconnect", "round", "expired"]
)
def test_waiting_is_durable_and_cancellable(setup, change):
    teamkills(setup, 1, age=0)
    chat(setup, "I teamkilled him on purpose")
    i = tk_report(setup)
    api = transport()
    service.tick(api, 1)
    assert state(setup, i)["status"] == "waiting"
    if change == "disable":
        service.configure(1, Config())
    elif change == "takeover":
        with setup[0]() as sess:
            service.cancel_incident(sess, sess.get(AdminIncident, i["id"]), "admin")
    elif change == "restart":
        service.recover(1)
    elif change == "reconnect":
        with setup[0]() as sess:
            row = sess.scalar(
                select(PlayerSession)
                .join(PlayerID)
                .where(PlayerID.player_id == "target")
            )
            row.end = service.utc(setup[0].clock.now).replace(tzinfo=None)
    elif change == "round":
        setup[2]["round_id"] = "new"
    advance(setup, 181 if change == "expired" else 60)
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert state(setup, i)["status"] == "manual"


def test_waiting_reports_do_not_starve_new_communication_report(setup):
    teamkills(setup, 1, age=0)
    for _ in range(4):
        tk_report(setup)
    api = transport()
    service.tick(api, 1)
    report(setup)
    service.tick(api, 1)
    api.kick.assert_called_once()


def test_dry_run_and_unknown_never_replay_teamkill(setup):
    service.configure(1, Config(enabled=True, mode="dry_run"))
    admitted_teamkill(setup)
    i = tk_report(setup)
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert state(setup, i)["status"] == "dry_run"


def cheat_report(setup, message="!admin BattlefieldHero cheater"):
    service.configure(1, Config(enabled=True, mode="active", cheating=True))
    return report(setup, message)


@pytest.mark.parametrize("enemy", [False, True])
def test_cheat_review_is_private_manual_and_can_target_enemy(setup, enemy):
    if enemy:
        setup[1][0]["team"] = "axis"
    i = cheat_report(setup)
    assert i["report_admin"]["status"] == "queued"
    api = transport()
    service.tick(api, 1)
    service.tick(api, 1)
    api.kick.assert_not_called()
    api.message_player.assert_called_once()
    assert api.message_player.call_args.args[0] == "v0"
    assert "received" in api.message_player.call_args.args[1]
    assert api.message_player.call_args.kwargs["save_message"] is False
    a = state(setup, i)["assessment"]
    assert a["state"] == "insufficient_data" and a["automatic_sanction"] is False
    assert a["manual_ban_hours"] == 24
    assert current(setup[0], i["id"])["status"] == "new"


def test_cheat_disabled_default_does_not_notify_or_act(setup):
    i = report(setup, "!admin BattlefieldHero cheater")
    assert not i["report_admin"]
    api = transport()
    service.tick(api, 1)
    api.message_player.assert_not_called()
    api.kick.assert_not_called()


@pytest.mark.parametrize(
    "message",
    [
        "!admin able cheater",
        "!admin BattlefieldHerx OtherGuy cheater",
        "!admin BattlefieldHero redet nicht cheater",
    ],
)
def test_ambiguous_or_mixed_cheating_stays_manual(setup, message):
    i = cheat_report(setup, message)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    # The exact + unknown extra name case can be parsed as one target; it must
    # still never result in any sanction, independently of report parsing.
    assert current(setup[0], i["id"])["status"] == "new"


def fact(at, category="infantry", weapon="M1 GARAND", **extra):
    return {
        "at": at,
        "type": "KILL",
        "actor": "target",
        "victim": "enemy",
        "name": "Target",
        "victim_name": "Enemy",
        "category": category,
        "weapon": weapon,
        "log_id": None,
        "body": None,
        **extra,
    }


def test_cheat_review_has_category_specific_sustained_windows():
    case = {
        "start": 0,
        "end": 900,
        "complete": True,
        "limitations": [],
        "facts": [fact(n * 10 + 1) for n in range(90)],
    }
    result = evidence.assess_cheating(case, "target")
    assert result[0] == "manual"
    assert result[2]["assessment"]["state"] == "suspicious"
    # Same rate from a tank must not be treated as infantry suspicion.
    case["facts"] = [
        fact(n * 10 + 1, category="armor", weapon="tank") for n in range(90)
    ]
    a = evidence.assess_cheating(case, "target", [{"at": 890, "role": "Rifleman"}])[2][
        "assessment"
    ]
    assert a["state"] == "no_observed_anomaly"
    assert a["windows"][-1]["categories"] == {"armor": 90}
    assert a["role_history"][0]["role"] == "Rifleman"


@pytest.mark.parametrize("issue", ["unknown_weapon", "short", "incomplete"])
def test_cheat_data_limitations_are_not_guilt_or_exoneration(issue):
    case = {
        "start": 0,
        "end": 900,
        "complete": True,
        "limitations": [],
        "facts": [fact(899)],
    }
    if issue == "unknown_weapon":
        case["facts"][0]["category"] = "unknown"
    elif issue == "short":
        case["start"] = 850
    else:
        case["complete"] = False
    result = evidence.assess_cheating(case, "target")
    assert result[2]["assessment"]["state"] == "insufficient_data"
    assert result[0] == "manual"


def test_hll_hllv_weapon_classifications():
    from rcon.game.hllv.weapons import HLLV_WEAPONS

    assert evidence.weapon_category("M1 GARAND", 1) == "infantry"
    assert evidence.weapon_category("UNKNOWN", 1) == "unknown"
    assert evidence.weapon_category("M1 GARAND", 999) == "unknown"
    for key, value in HLLV_WEAPONS.items():
        assert evidence.weapon_category(key, 2) == value.value


def test_complete_chat_envelope_cannot_be_manufactured_by_name():
    assert (
        evidence.chat_body(
            "I teamkilled him on purpose: hello (x)", "I teamkilled him on purpose", "x"
        )
        == "hello"
    )
    assert evidence.chat_body("Someone: sorry (y)", "Someone", "x") is None


def test_live_log_parse_failure_never_silently_disappears():
    api = transport()
    api.get_logs = Mock(return_value=["malformed"])
    api.parse_logs = Mock(return_value={"logs": []})
    api.split_raw_log_lines = Mock(return_value=[("time", "stamp", "malformed")])
    with pytest.raises(ValueError, match="Incomplete"):
        evidence.fresh_logs(api)


def test_corresponding_report_is_not_an_admission(setup):
    teamkills(setup, 1, age=75)
    chat(setup, "I teamkilled him on purpose", age=70, pid="v0")
    i = tk_report(setup)
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert state(setup, i)["assessment"]["admissions"] == []


def test_retirement_keeps_history_but_cancels_old_work_and_config(setup):
    from tests.test_leadership_vote import activate, vote
    from rcon.models import LeadershipMessage

    service.configure(1, Config())
    vid, _ = activate(setup[0])  # Explicit legacy fixture, not production routing.
    service.recover(1)
    assert vote(setup[0], vid)["status"] == "cancelled"
    with setup[0]() as sess:
        assert service.votes.config(sess, 1).enabled is False
        assert not list(
            sess.scalars(
                select(LeadershipMessage).where(
                    LeadershipMessage.status.in_({"pending", "sending"})
                )
            )
        )


def test_ordinary_report_never_falls_back_to_a_vote(setup):
    service.configure(1, Config())
    i = report(setup)
    assert i["leadership_vote"] is None and i["report_admin"] is None


def test_old_configuration_cannot_be_enabled_by_generic_config_save():
    from rcon.user_config.leadership_vote import LeadershipVoteUserConfig

    with pytest.raises(ValueError, match="retired"):
        LeadershipVoteUserConfig.save_to_db({"enabled": True}, dry_run=True)


def test_two_reporters_raise_priority_not_cheat_certainty(setup):
    service.configure(1, Config(enabled=True, mode="active", cheating=True))
    first = report(setup, "!admin BattlefieldHero cheater")
    second = report(setup, "!admin BattlefieldHero cheater", reporter_id="v1")
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    for incident in (first, second):
        a = state(setup, incident)["assessment"]
        assert a["distinct_reporters"] == 2 and a["priority"] == "high"
        assert a["state"] == "insufficient_data" and not a["automatic_sanction"]


def test_qualified_report_cannot_turn_into_automatic_kick(setup):
    admitted_teamkill(setup)
    i = report(setup, "!admin BattlefieldHero teamkills aus versehen")
    api = transport()
    service.tick(api, 1)
    api.kick.assert_not_called()
    assert state(setup, i)["status"] == "manual"


def test_explosion_burst_is_only_context_not_multiple_intent_events():
    facts = [
        fact(
            900 + n / 10,
            category="grenade",
            weapon="GRENADE",
            type="TEAM KILL",
            victim=f"friend{n}",
        )
        for n in range(5)
    ]
    case = {
        "facts": facts,
        "start": 500,
        "end": 1000,
        "complete": True,
        "limitations": [],
    }
    result = evidence.assess_teamkills(case, "target", "reporter", 950, 1000)
    assert result[0] == "manual"
    assert result[2]["assessment"]["possible_explosion_bursts"] == 5


def test_live_evidence_corroborates_hll_parser():
    from rcon.rcon import Rcon
    from rcon.types import GameEnum

    api = transport()
    api.config = SimpleNamespace(game=GameEnum.HLL_WW2)
    api.parse_logs = Rcon.parse_logs
    api.split_raw_log_lines = Rcon.split_raw_log_lines
    api.get_logs = Mock(
        return_value=[
            "[0 sec (2000000000)] CHAT[Team][Example(Allies/76561198000000000)]: sorry"
        ]
    )
    logs = evidence.fresh_logs(api)
    assert logs["logs"][0]["sub_content"] == "sorry"
    assert logs["game"] == 1


def test_review_receipt_not_retried_on_uncertain_result(setup):
    i = cheat_report(setup)
    api = transport()
    api.message_player.side_effect = RuntimeError("timeout")
    service.tick(api, 1)
    service.tick(api, 1)
    api.message_player.assert_called_once()
    api.kick.assert_not_called()
    assert state(setup, i)["status"] == "manual"
