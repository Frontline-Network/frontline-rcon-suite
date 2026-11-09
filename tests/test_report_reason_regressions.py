"""October 26 report audit: recorded wording, fake rosters and transports only."""

import pytest

from tests.test_report_reason import semantic, setup, db, complete, decision
from tests.test_report_admin import report, current, service, transport
from rcon.user_config.report_admin import ReportAdminUserConfig as Config


def finish_case(semantic, message, interpretation):
    incident = report(semantic, message)
    complete(semantic, incident["id"], interpretation)
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    return api, current(semantic[0], incident["id"])["report_admin"]


@pytest.mark.parametrize("reference,squad", [("ABLE", "alfa"), ("GOLF", "golf")])
def test_no_mic_can_complete_for_either_squad(semantic, reference, squad):
    original_squad = semantic[1][0]["unit_name"]
    for player in semantic[1]:
        if player.get("unit_name") == original_squad:
            player.update(unit_name=squad, unit_id=0)
    semantic[1][0].update(role="tankcommander", unit_name=squad, unit_id=0)
    text = f"{reference} SL NO MIC"
    api, result = finish_case(
        semantic,
        "!ADMIN " + text,
        decision(target=reference, target_kind="squad", excerpt=text),
    )
    api.kick.assert_called_once()
    assert api.kick.call_args.args[0] == "target"
    assert result["status"] == "kicked"


@pytest.mark.parametrize(
    "fragment,kind",
    [
        ("Grrey_Mentor", "player"),
        ("Grey_Mento", "commander"),
    ],
)
@pytest.mark.parametrize("collision", [False, True])
def test_commander_full_name_typos_still_require_unique_player(
    semantic,
    fragment,
    kind,
    collision,
):
    commander = next(p for p in semantic[1] if p["player_id"] == "v5")
    commander["name"] = "Grey_Mentor"
    if collision:
        semantic[1][0]["name"] = "Grey_Mentox"
    text = f"Kommandant {fragment} spricht nicht"
    api, result = finish_case(
        semantic,
        "!Admin " + text,
        decision(target=fragment, target_kind=kind, excerpt=text),
    )
    if collision:
        api.kick.assert_not_called()
        assert result["status"] == "manual"
    else:
        api.kick.assert_called_once()
        assert api.kick.call_args.args[0] == "v5"


@pytest.mark.parametrize(
    "complaint",
    [
        "NS Parolen HH im SL chat",
        "NS Äußerungen",
        "Nazi slogans in voice chat",
        "racist slurs over VOIP",
        "Beleidigungen im Squadchat",
        "droht anderen Spielern",
        "death threats in command chat",
        "no comms und NS Parolen im Chat",
    ],
)
def test_other_allegations_cannot_become_communication_kicks(semantic, complaint):
    # Replay even a confident, incorrect model classification like the live case.
    semantic[1][0]["name"] = "LARRY THE LOBSTER"
    text = f"LARRX the Lobster {complaint}"
    api, result = finish_case(
        semantic,
        "!admin " + text,
        decision(target="LARRX the Lobster", excerpt=text),
    )
    api.kick.assert_not_called()
    assert result["status"] == "manual"
    assert result["reason_analysis"]["target_check"]["code"] == (
        "communication_category_conflict"
    )
    assert "other than missing communication" in result["result"]


def test_guard_reads_whole_report_not_just_selected_excerpt(semantic):
    api, result = finish_case(
        semantic,
        "!admin BattlefieldHero no comms. Also racist slurs in voice chat.",
        decision(excerpt="no comms"),
    )
    api.kick.assert_not_called()
    assert "other than missing communication" in result["result"]


@pytest.mark.parametrize("name", ["NaziHunter", "HH", "ThreatHunter"])
def test_handle_alone_does_not_manufacture_an_unsupported_complaint(semantic, name):
    from rcon.report_reason_contract import ReportReasonDecision
    from rcon.report_reason_policy import interpretation_failure

    semantic[1][0]["name"] = name
    assert (
        interpretation_failure(
            {"raw_message": f"!admin {name} no comms"},
            ReportReasonDecision(**decision(target=name, excerpt="no comms")),
        )
        is None
    )
    api, result = finish_case(
        semantic,
        f"!admin {name} no comms",
        decision(target=name, excerpt="no comms"),
    )
    if name == "HH":
        api.kick.assert_not_called()  # The independent short-name guard still applies.
        assert result["status"] == "manual"
    else:
        api.kick.assert_called_once()
        assert result["status"] == "kicked"


def test_member_without_squad_explains_real_block_and_is_not_replayed(semantic):
    service.configure(
        1,
        Config(
            enabled=True,
            mode="active",
            reason_mode="ai",
            communication_squad_members=True,
        ),
    )
    member = next(p for p in semantic[1] if p["player_id"] == "member")
    member.update(
        name="piloto_terco693", role="sniper", unit_name="unassigned", unit_id=0
    )
    api, result = finish_case(
        semantic,
        "!admin kick player piloto_terco693 keine kommunikation",
        decision(target="piloto_terco693", excerpt="keine kommunikation"),
    )
    api.kick.assert_not_called()
    assert "no confirmed squad assignment" in result["result"]
    audit = result["reason_analysis"]["target_check"]
    assert audit["code"] == "target_squad_unassigned"
    assert audit["original"]["target"]["squad_id"] == "0"
    member.update(unit_name="echo", unit_id=4)
    service.tick(api, 1)
    api.kick.assert_not_called()


@pytest.mark.parametrize(
    "interpretation,code",
    [
        (decision(rule="manual", unambiguous=False), "manual_review_required"),
        (decision(uncertainties=["Two possible players"]), "interpretation_uncertain"),
        (decision(excerpt="invented allegation"), "ungrounded_interpretation"),
    ],
)
def test_semantic_refusals_are_not_mislabeled_as_player_lookup_errors(
    semantic,
    interpretation,
    code,
):
    api, result = finish_case(
        semantic,
        "!admin BattlefieldHero never answers us in command chat",
        interpretation,
    )
    api.kick.assert_not_called()
    assert result["reason_analysis"]["target_check"]["code"] == code
    assert "Target not safely identified" not in result["result"]
