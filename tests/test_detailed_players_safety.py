from types import SimpleNamespace
from unittest.mock import Mock

import pytest
from rcon.rcon import Rcon
from rcon.commands import ServerCtl
from rcon.game import get_game_profile
from rcon.types import GameEnum


def test_missing_player_details_are_reported_as_incomplete(monkeypatch):
    monkeypatch.setattr("rcon.rcon.MapsHistory", lambda: [{"start": 1}])
    fake = SimpleNamespace(
        get_players=Mock(return_value=[{"player_id": "missing"}]),
        get_all_player_info=Mock(return_value=[]),
    )
    result = Rcon.get_detailed_players.__wrapped__(fake)
    assert result["players"] == {}
    assert result["fail_count"] == 1


def test_player_id_list_preserves_equal_names(monkeypatch):
    response = SimpleNamespace(content_dict={"players": [
        {"name": "Same", "iD": "id-1"}, {"name": "Same", "iD": "id-2"},
    ]})
    monkeypatch.setattr(ServerCtl, "exchange", lambda *_args, **_kwargs: response)
    rcon = object.__new__(Rcon)
    rcon.game_profile = get_game_profile(GameEnum.HLL_WW2)
    assert rcon.get_player_ids() == [("Same", "id-1"), ("Same", "id-2")]
    assert rcon.get_player_ids(as_dict=True) == {"Same": "id-2"}


def test_vietnam_player_list_accepts_v2_field_names(monkeypatch):
    response = SimpleNamespace(content_dict={"players": [{"Name": "Player", "Id": "vietnam-id"}]})
    monkeypatch.setattr(ServerCtl, "exchange", lambda *_args, **_kwargs: response)
    rcon = object.__new__(Rcon)
    rcon.game_profile = get_game_profile(GameEnum.HLL_VIETNAM)
    assert rcon.get_player_ids() == [("Player", "vietnam-id")]


@pytest.mark.parametrize("game", [GameEnum.HLL_WW2, GameEnum.HLL_VIETNAM])
def test_team_view_keeps_squadless_player_alongside_commander(game):
    rcon = object.__new__(Rcon)
    rcon.config = SimpleNamespace(game=game)
    stats = {"team": "allies", "unit_name": None, "combat": 0, "offense": 0,
             "defense": 0, "support": 0, "kills": 0, "deaths": 0}
    commander = {**stats, "player_id": "commander", "role": "armycommander"}
    soldier = {**stats, "player_id": "soldier", "role": "rifleman"}
    rcon.get_detailed_players = Mock(return_value={"players": {"commander": commander, "soldier": soldier}, "fail_count": 0})
    team = Rcon.get_team_view.__wrapped__(rcon)["allies"]
    assert team["commander"]["player_id"] == "commander"
    assert [p["player_id"] for squad in team["squads"].values() for p in squad["players"]] == ["soldier"]
    assert team["count"] == 2
