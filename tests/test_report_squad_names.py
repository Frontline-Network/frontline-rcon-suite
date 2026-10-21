"""Squad references must beat same-word fuzzy noise, never genuine conflicts."""

from copy import deepcopy

import pytest

from rcon.admin_incidents import parse_chat_report
from rcon.report_admin_rules import target_for
from rcon.report_admin_rules import conservative_name_match
from rcon.report_reason import target as reason_target


def roster(squad="charlie", similar="Charli"):
    return [
        dict(
            player_id="reporter",
            name="Reporter",
            team="allies",
            role="Rifleman",
            unit_name="bravo",
            unit_id=1,
        ),
        dict(
            player_id="leader",
            name="Leader",
            team="allies",
            role="SquadLeader",
            unit_name=squad,
            unit_id=2,
        ),
        dict(
            player_id="similar",
            name=similar,
            team="allies",
            role="Rifleman",
            unit_name="delta",
            unit_id=3,
        ),
    ]


def incident(players, reference):
    message = f"!admin {reference} not talking"
    parsed = parse_chat_report(
        message,
        current_players=players,
        reporter_context=players[0],
        fuzzy_threshold=0.70,
    )
    return {**parsed, "reporter_id": "reporter"}


@pytest.mark.parametrize(
    "squad,reference,similar",
    [
        ("charlie", "charlie", "Charli"),
        ("papa", "peter", "Petr"),
        ("JULIETTE", "jig", "Jigg"),
    ],
)
@pytest.mark.parametrize("team", ["allies", "axis"])
def test_known_squad_beats_only_same_word_fuzzy_player_noise(
    squad, reference, similar, team
):
    players = roster(squad, similar)
    players[2]["team"] = team
    report = incident(players, reference)
    assert any(
        s["match_method"] == "fuzzy" and s["player_id"] == "similar"
        for s in report["subjects"]
    )
    before = deepcopy(report)
    assert target_for(report, players, "communication")["player_id"] == "leader"
    assert (
        reason_target(
            report,
            players,
            dict(
                rule="communication",
                target_kind="squad",
                target_text=reference,
                allegation_excerpt="not talking",
                unambiguous=True,
                uncertainties=[],
                rationale="Test only",
            ),
            False,
        )["player_id"]
        == "leader"
    )
    assert report == before


@pytest.mark.parametrize(
    "state,method,matched",
    [
        ("confirmed", "fuzzy", "charlie"),
        ("rejected", "fuzzy", "charlie"),
        ("suggested", "recent_name", "charlie"),
        ("suggested", "fuzzy", "someone else"),
        ("suggested", "fuzzy", None),
        ("suggested", "name_contained", "charlie"),
    ],
)
def test_other_subject_conflicts_are_not_discarded(state, method, matched):
    players = roster()
    report = incident(players, "charlie")
    report["subjects"] = [
        dict(
            kind="player",
            state=state,
            match_method=method,
            player_id="similar",
            matched_text=matched,
        )
    ]
    assert target_for(report, players, "communication") is None


@pytest.mark.parametrize(
    "change",
    [
        "exact_name",
        "missing_leader",
        "two_leaders",
        "other_team",
        "absent_squad",
        "two_squads",
    ],
)
def test_ambiguous_or_unavailable_squad_remains_manual(change):
    players = roster()
    if change == "exact_name":
        players[2]["name"] = "Charlie"
    elif change == "missing_leader":
        players[1]["role"] = "Rifleman"
    elif change == "two_leaders":
        players.append({**players[1], "player_id": "second", "name": "Another leader"})
    elif change == "other_team":
        players[1]["team"] = "axis"
    elif change == "absent_squad":
        players[1]["unit_name"] = "echo"
    elif change == "two_squads":
        players[2].update(role="SquadLeader", unit_name="charlie")
    report = incident(players, "charlie")
    assert target_for(report, players, "communication") is None
    assert (
        reason_target(
            report,
            players,
            dict(
                rule="communication",
                target_kind="squad",
                target_text="charlie",
                allegation_excerpt="not talking",
                unambiguous=True,
                uncertainties=[],
                rationale="Test only",
            ),
            False,
        )
        is None
    )


@pytest.mark.parametrize("role", ["Rifleman", "SquadLeader"])
def test_explicit_player_typo_is_never_redirected_to_another_squadleader(role):
    players = roster()
    players[2]["role"] = role
    report = incident(players, "charlie")
    assert (
        conservative_name_match(report["subjects"], players)["player_id"] == "similar"
    )
    assert (
        reason_target(
            report,
            players,
            dict(
                rule="communication",
                target_kind="player",
                target_text="charlie",
                allegation_excerpt="not talking",
                unambiguous=True,
                uncertainties=[],
                rationale="Named player, not the squad",
            ),
            False,
        )
        is None
    )
