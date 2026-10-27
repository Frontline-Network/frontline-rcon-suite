"""Abbreviated report names: synthetic rosters and mocked game actions only."""

import pytest

from tests.test_report_reason import semantic, setup, db, complete, decision
from tests.test_report_admin import report, current, service, transport
from rcon import report_admin_rules as rules


def suggested(fragment, pid="target"):
    return [
        {
            "kind": "player",
            "state": "suggested",
            "match_method": "fuzzy",
            "matched_text": fragment,
            "player_id": pid,
        }
    ]


@pytest.mark.parametrize(
    "fragment,name",
    [
        ("BLITZ_33", "Blitz_33_1981"),
        ("BLITX_33", "Blitz_33_81"),
        ("Blitz_33", "Blitz_33-1981"),
        ("battlefield", "Battlefield Hero"),
    ],
)
def test_distinctive_prefix_resolves(fragment, name):
    target = {"player_id": "target", "name": name}
    assert rules.conservative_name_match(suggested(fragment), [target]) == target


@pytest.mark.parametrize(
    "fragment,name",
    [
        ("Blitz", "Blitz_33_1981"),  # Too short.
        ("Blitz_33", "Blitz_331981"),  # Truncated inside a token.
        ("1981", "Blitz_33_1981"),  # Suffix alone.
        ("Blitz_33", "Other_Blitz_33"),  # Arbitrary substring.
        ("Blizx_34", "Blitz_33_1981"),  # Too many errors plus abbreviation.
        ("a_____", "a______1981"),  # Separators are not distinctive characters.
    ],
)
def test_inadequate_reference_stays_manual(fragment, name):
    assert (
        rules.conservative_name_match(
            suggested(fragment), [{"player_id": "target", "name": name}]
        )
        is None
    )


@pytest.mark.parametrize(
    "other_name", ["Blitz_33_1982", "Blitz_34_1982", "Blitz_33", "Blitz_34"]
)
@pytest.mark.parametrize("team", ["allies", "axis"])
def test_competing_prefix_or_full_name_blocks_both_teams(other_name, team):
    players = [
        {"player_id": "target", "name": "Blitz_33_1981", "team": "allies"},
        {"player_id": "other", "name": other_name, "team": team},
    ]
    assert rules.conservative_name_match(suggested("BLITZ_33"), players) is None


def test_nearby_abbreviation_also_blocks_full_name_typo():
    players = [
        {"player_id": "target", "name": "Blitz_33"},
        {"player_id": "other", "name": "Blitz_34_1981"},
    ]
    assert rules.conservative_name_match(suggested("BLITX_33"), players) is None


def test_suggested_id_cannot_be_redirected_to_another_player():
    players = [{"player_id": "other", "name": "Blitz_33_1981"}]
    assert rules.conservative_name_match(suggested("BLITZ_33"), players) is None


@pytest.mark.parametrize("change", [None, "collision", "offline", "replacement"])
@pytest.mark.parametrize(
    "fragment,name", [("BLITZ_33", "Blitz_33_1981"), ("BLITX_33", "Blitz_33_81")]
)
def test_abbreviated_live_report_rechecks_identity_before_action(
    semantic, change, fragment, name
):
    players = semantic[1]
    players[0].update(name=name, role="helicopterlogisticsofficer")
    incident = report(semantic, f"!admin {fragment} Sl no Voip")
    complete(semantic, incident["id"], decision(target=fragment, excerpt="Sl no Voip"))
    if change == "collision":
        players[1]["name"] = "Blitz_33_1982"
    elif change == "offline":
        players[0]["online"] = False
    elif change == "replacement":
        players[0]["player_id"] = "replacement"
    api = transport()
    for _ in range(3):
        service.tick(api, 1)
    state = current(semantic[0], incident["id"])["report_admin"]
    if change is None:
        api.kick.assert_called_once()
        assert api.kick.call_args.args[0] == "target"
        assert state["status"] == "kicked"
    else:
        api.kick.assert_not_called()
        assert state["status"] == "manual"
