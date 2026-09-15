"""Real wording, synthetic identities: no live game, DB, message or kick."""

from copy import deepcopy

import pytest

from rcon.admin_incidents import parse_chat_report
from rcon.leadership_vote import targets


def players(role="Officer"):
    result = [
        dict(
            player_id=f"p{i}",
            name=f"Demo Person {i:02d}",
            role=role,
            team="allies",
            unit_name=words[0],
            unit_id=i + 1,
        )
        for i, words in enumerate(targets.ALPHABET)
    ]
    result.append(
        dict(
            player_id="commander",
            name="Demo Commander Name",
            role="ArmyCommander",
            team="allies",
            unit_name="command",
        )
    )
    return result


def resolve(text, roster=None, subjects=()):
    roster = players() if roster is None else roster
    return targets.resolve(text, subjects, {"team": "allies"}, roster)


@pytest.mark.parametrize("role", ["Officer", "SquadLeader"])
@pytest.mark.parametrize("index,words", list(enumerate(targets.ALPHABET)))
def test_full_alphabet_and_current_names_in_both_games(role, index, words):
    for word in words:
        result = resolve(f"!admin bitte mal {word.upper()} prüfen", players(role))
        assert result["player"]["player_id"] == f"p{index}"
        assert result["resolution"]["version"] == targets.VERSION


@pytest.mark.parametrize(
    "cue", ["SL {letter}", "{letter} SL", "Squad {letter}", "{letter} squad"]
)
@pytest.mark.parametrize("index", range(26))
def test_single_letters_need_explicit_context(cue, index):
    text = cue.format(letter=chr(ord("A") + index))
    assert resolve(f"!admin {text} redet nicht")["player"]["player_id"] == f"p{index}"


@pytest.mark.parametrize("word,index", [("Eays", 4), ("Gorge", 6), ("Geoge", 6)])
def test_reviewed_typos(word, index):
    assert (
        resolve(f"!admin {word} SL redet nicht")["player"]["player_id"] == f"p{index}"
    )


@pytest.mark.parametrize("alias", sorted(targets.COMMANDERS))
def test_commander_aliases(alias):
    result = resolve(f" !ADMIN bitte der {alias} redet nicht ")
    assert result["player"]["player_id"] == "commander"


@pytest.mark.parametrize(
    "word,index",
    [("echosquad", 4), ("SquadBravo", 1), ("foxsl", 5), ("squadleaderkilo", 10)],
)
def test_attached_role_words(word, index):
    assert (
        resolve(f"!admin {word} not communicating")["player"]["player_id"]
        == f"p{index}"
    )


@pytest.mark.parametrize(
    "text,index",
    [
        ("!admin bitte mal prüfen able redet nicht", 0),
        ("!admin king sl keine com", 10),
        ("!admin fox squadlead spricht nciht", 5),
        ("!admin ITEM not talkin not respownding??", 8),
        ("!admin item", 8),
        (
            "!admin einmal bitte love tank squad kicken keine kommunikation und behindert das team",
            11,
        ),
        ("!Admin: SL EASY KEINE KOMMUNIKATION; kommt seiner aufgabe nicht nach", 4),
        ("!admin - charlie keine kommunikation", 2),
        ("!admin GEORGE REPORT", 6),
        ("!admin Baker Teamleader nutzt kein MIc/Antwortet mir nicht", 1),
        ("!admin sl B hat kein mic", 1),
        ("!admin Bitte KILO SL kicken, redet nicht", 10),
        ("!admin <HOW>", 7),
    ],
)
def test_reviewed_real_wording(text, index):
    assert resolve(text)["player"]["player_id"] == f"p{index}"


def test_same_squad_and_leader_name_merge_by_player_id():
    roster = players()
    text = "!admin Squad Easy SL redet nicht (Demo Person 04)"
    parsed = parse_chat_report(
        text, current_players=roster, reporter_context={"team": "allies"}
    )
    result = resolve(text, roster, parsed["subjects"])
    assert result["player"]["player_id"] == "p4"
    assert any(
        m["method"] == "exact_player_name" for m in result["resolution"]["matches"]
    )


def test_same_commander_alias_and_name_merge():
    assert (
        resolve("!admin Kommi Demo Commander Name redet nicht")["player"]["player_id"]
        == "commander"
    )


def test_explicit_leader_role_with_exact_name():
    assert (
        resolve("!admin SL Demo Person 01 redet nicht")["player"]["player_id"] == "p1"
    )
    assert resolve("!admin Demo Person 01 redet nicht") is None


def test_squad_reference_inside_full_player_name_is_not_another_target():
    roster = players()
    roster[1]["name"] = "Easy Company Bob"
    assert (
        resolve("!admin baker SL Easy Company Bob redet nicht", roster)["player"][
            "player_id"
        ]
        == "p1"
    )


def test_noise_from_fuzzy_players_does_not_block_exact_squad():
    noise = [
        {
            "kind": "player",
            "state": "suggested",
            "match_method": "fuzzy",
            "player_id": "p9",
        }
    ]
    assert (
        resolve("!admin item redet nich", subjects=noise)["player"]["player_id"] == "p8"
    )


@pytest.mark.parametrize(
    "text",
    [
        "!admin how fox redet nicht",
        "!admin squad able negat kommunizieren nicht",
        "!admin able baker redet nicht",
        "!admin 3 squad leader sprechen (jig, george & easy) rest ist totenstill",
        "!admin SL B hat doch ein mic, weigert sich aber der commander zu folgen",
        "!admin SL Unbekannt folgt dem commander nicht",
        "!admin easy Demo Person 01 redet nicht",
        "!admin Demo Person 01 und Demo Person 02 als SL redet nicht",
        "!admin sl redet nicht",
        "!admin unser squadlead redet nicht",
        "!admin beide aufklärer sprechen nicht",
        "!admin keine com",
        "!admin I have a problem",
        "!admin b",
        "bitte !admin easy redet nicht",
        "!administrator easy redet nicht",
        "!admin esay redet nicht",  # not a reviewed typo; no nearest-string guess
        "!admin notgeorge redet nicht",
    ],
)
def test_ambiguous_incomplete_and_non_commands_never_choose(text):
    assert resolve(text) is None


def test_multiple_spellings_for_same_target_are_not_multiple_votes():
    assert resolve("!admin Baker Bravo SL B redet nicht")["player"]["player_id"] == "p1"


def test_aliases_work_with_nato_named_live_squads_too():
    roster = players()
    roster[1]["unit_name"] = "Bravo"
    assert resolve("!admin baker redet nicht", roster)["player"]["player_id"] == "p1"


def test_colliding_current_squad_names_never_pick_one():
    roster = players()
    roster[2]["unit_name"] = "Bravo"
    assert resolve("!admin bravo redet nicht", roster) is None
    assert resolve("!admin baker redet nicht", roster) is None


def test_alias_does_not_fall_back_to_other_team_or_another_target():
    roster = players()
    roster[1]["team"] = "axis"
    assert resolve("!admin bravo redet nicht", roster) is None
    assert resolve("!admin bravo und commander redet nicht", roster) is None


def test_missing_or_duplicate_leader_and_disconnected_target():
    roster = players()
    roster[1]["role"] = "Rifleman"
    assert resolve("!admin bravo", roster) is None
    roster = players()
    roster[1]["online"] = False
    assert resolve("!admin bravo", roster) is None
    roster = players()
    duplicate = dict(roster[1], player_id="duplicate", name="Duplicate")
    assert resolve("!admin bravo", roster + [duplicate]) is None
    assert resolve("!admin bravo", roster + [deepcopy(roster[1])]) is None


def test_player_name_and_squad_collision_is_ambiguous():
    roster = players()
    roster[2]["name"] = "Bravo"
    assert resolve("!admin bravo", roster) is None


def test_duplicate_exact_player_names_are_not_collapsed():
    roster = players()
    roster[2]["name"] = roster[1]["name"]
    assert resolve("!admin bravo Demo Person 01", roster) is None


def test_departed_player_reference_does_not_transfer_to_replacement():
    recent = [
        {
            "kind": "player",
            "state": "confirmed",
            "match_method": "recent_name",
            "player_id": "departed",
        }
    ]
    assert resolve("!admin bravo", subjects=recent) is None


def test_custom_squad_name_supported_without_initial_letter_guess():
    roster = players()
    roster[1]["unit_name"] = "Custom Squad"
    assert (
        resolve("!admin Custom Squad redet nicht", roster)["player"]["player_id"]
        == "p1"
    )
    assert resolve("!admin Squad C redet nicht", roster)["player"]["player_id"] == "p2"


def test_pure_resolution_does_not_modify_inputs():
    roster = players()
    original = deepcopy(roster)
    resolve("!admin bravo", roster)
    assert roster == original


@pytest.mark.parametrize("text", ["!admin bravo", "!admin SL Demo Person 01"])
@pytest.mark.parametrize("squad", ["baker", "inconsistent-name"])
def test_same_seat_with_two_leaders_rejects_even_exact_player_name(text, squad):
    roster = players()
    roster.append(
        dict(roster[1], player_id="second-leader", name="Someone else", unit_name=squad)
    )
    assert resolve(text, roster) is None


@pytest.mark.parametrize("unit_id", [None, 2])
def test_missing_squad_cannot_be_recovered_from_name_alone(unit_id):
    roster = players()
    roster[1].update(unit_name="", unit_id=unit_id)
    assert resolve("!admin SL Demo Person 01", roster) is None


def test_multiple_commanders_reject_even_with_exact_name():
    roster = players()
    roster.append(dict(roster[-1], player_id="second-commander", name="Someone else"))
    assert resolve("!admin Kommi Demo Commander Name", roster) is None


@pytest.mark.parametrize("commander", [False, True])
def test_incumbent_change_between_report_parsing_and_live_snapshot_rejects(commander):
    roster = players()
    text = "!admin commander" if commander else "!admin baker"
    if commander:
        subject = dict(
            kind="player",
            state="confirmed",
            match_method="team_commander",
            player_id="previous-incumbent",
        )
    else:
        subject = dict(
            kind="squad",
            state="confirmed",
            match_method="squad_exact",
            squad_name="Baker",
            leader_player_id="previous-incumbent",
        )
    assert resolve(text, roster, [subject]) is None
