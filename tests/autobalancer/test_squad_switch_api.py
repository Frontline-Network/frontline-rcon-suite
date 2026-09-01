import os
import pytest

os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon.autobalancer.squad_switch import validate_squad_switch_moves


def team_view(*, allies_count=6, axis_count=2, squad_type="infantry"):
    return {
        "fail_count": 0,
        "allies": {
            "count": allies_count,
            "squads": {
                "Able": {
                    "type": squad_type,
                    "players": [
                        {"player_id": "a1", "name": "Alpha"},
                        {"player_id": "a2", "name": "Bravo"},
                    ],
                }
            },
        },
        "axis": {"count": axis_count, "squads": {}},
    }


def move(player_ids=None):
    return {
        "source_team": "allies",
        "target_team": "axis",
        "target_label": "Achsenmächte",
        "squad_name": "Able",
        "player_ids": player_ids or ["a1", "a2"],
    }


def test_squad_move_requires_and_returns_the_complete_live_squad():
    validated = validate_squad_switch_moves(team_view(), [move()])
    assert validated[0]["squad_name"] == "Able"
    assert validated[0]["target_label"] == "Achsenmächte"
    assert {player["player_id"] for player in validated[0]["players"]} == {
        "a1",
        "a2",
    }


def test_squad_move_is_rejected_when_membership_changed():
    with pytest.raises(ValueError, match="verändert"):
        validate_squad_switch_moves(team_view(), [move(["a1"])])


def test_special_squads_cannot_be_moved_as_a_group():
    with pytest.raises(ValueError, match="Spezial"):
        validate_squad_switch_moves(team_view(squad_type="armor"), [move()])


def test_incomplete_live_data_blocks_the_action():
    view = team_view()
    view["fail_count"] = 1
    with pytest.raises(ValueError, match="unvollständig"):
        validate_squad_switch_moves(view, [move()])


def test_client_cannot_override_the_target_team_label():
    payload = move()
    payload["target_label"] = "Manipulierter Zielname"
    validated = validate_squad_switch_moves(team_view(), [payload])
    assert validated[0]["target_label"] == "Achsenmächte"


def test_malformed_move_is_rejected_cleanly():
    with pytest.raises(ValueError, match="ungültiges Format"):
        validate_squad_switch_moves(team_view(), [None])
