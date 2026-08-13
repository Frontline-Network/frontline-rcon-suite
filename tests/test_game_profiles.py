from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from rcon.commands import HLLServerCtl, HLLVServerCtl
from rcon.api_commands import (
    HLLRconAPI,
    HLLVRconAPI,
    RconAPI,
    create_rcon_api,
)
from rcon.game import get_game_profile
from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv.profile import HLLV_PROFILE
from rcon.maps import GameMode, Team, UNKNOWN_MAP_NAME
from rcon.rcon import HLLRcon, HLLVRcon, Rcon, create_rcon
from rcon.types import GameEnum, ServerInfo


def _response(content_dict):
    return SimpleNamespace(content_dict=content_dict)


def _session(map_id: str, game_mode: str = "Warfare") -> dict:
    return {
        "remainingMatchTime": 3600,
        "gameMode": game_mode,
        "mapId": map_id,
        "axisScore": 1,
        "axisFaction": 2,
        "axisPlayerCount": 40,
        "alliedScore": 3,
        "alliedFaction": 4,
        "alliedPlayerCount": 42,
        "alliedMorale": 5,
        "axisMorale": 6,
        "initialMorale": 7,
        "matchTime": 5400,
        "queueCount": 2,
        "maxQueueCount": 6,
        "vipQueueCount": 1,
        "maxVipQueueCount": 2,
        "serverName": "Test server",
    }


def test_server_info_defaults_game_even_without_port():
    assert ServerInfo().game is GameEnum.HLL_WW2


@pytest.mark.parametrize(
    ("game", "expected"),
    [
        (GameEnum.HLL_WW2, HLL_PROFILE),
        (GameEnum.HLL_VIETNAM, HLLV_PROFILE),
        ("hll", HLL_PROFILE),
        ("hllv", HLLV_PROFILE),
    ],
)
def test_get_game_profile(game, expected):
    assert get_game_profile(game) is expected


def test_hllv_profile_does_not_read_hll_map_catalog():
    hll_layer = HLL_PROFILE.parse_layer("carentan_warfare")
    hllv_layer = HLLV_PROFILE.parse_layer("carentan_warfare")

    assert hll_layer.map.id == "carentan"
    assert hllv_layer.id == "carentan_warfare"
    assert hllv_layer.map.id == UNKNOWN_MAP_NAME
    assert hllv_layer.game_mode is GameMode.DOMINATION


def test_hllv_profile_loads_hllv_catalog_with_logical_sides():
    layer = HLLV_PROFILE.parse_layer("wdeve_offensivenva_day")

    assert layer.map.id == "WDEV_E"
    assert layer.map.allies.team is Team.ALLIES
    assert layer.map.axis.team is Team.AXIS
    assert layer.attackers is Team.AXIS


def test_profiles_only_accept_their_supported_game_modes():
    assert HLL_PROFILE.parse_game_mode("Skirmish") is GameMode.SKIRMISH
    assert HLLV_PROFILE.parse_game_mode("Domination") is GameMode.DOMINATION

    with pytest.raises(ValueError, match="not supported by the 'hll' game profile"):
        HLL_PROFILE.parse_game_mode("Domination")

    with pytest.raises(ValueError, match="not supported by the 'hllv' game profile"):
        HLLV_PROFILE.parse_game_mode("Skirmish")


@pytest.mark.parametrize("raw_mode", ["NVA Offensive", "US Offensive"])
def test_hllv_profile_accepts_faction_specific_offensive_modes(raw_mode):
    assert HLLV_PROFILE.parse_game_mode(raw_mode) is GameMode.OFFENSIVE


@pytest.mark.parametrize(
    ("game", "game_mode", "expected_map_id"),
    [
        (GameEnum.HLL_WW2, "Warfare", "carentan"),
        (GameEnum.HLL_VIETNAM, "Domination", UNKNOWN_MAP_NAME),
    ],
)
def test_server_ctl_parses_game_state_with_selected_profile(
    game, game_mode, expected_map_id
):
    ctl_type = HLLServerCtl if game is GameEnum.HLL_WW2 else HLLVServerCtl
    ctl = ctl_type(ServerInfo(game=game), Mock())
    ctl.exchange = Mock(
        side_effect=[
            _response(_session("carentan_warfare", game_mode)),
            _response(
                {
                    "mAPS": [{"iD": "carentan_warfare"}],
                    "currentIndex": 0,
                }
            ),
        ]
    )

    game_state = ctl.get_gamestate()

    assert game_state["current_map"]["map"]["id"] == expected_map_id
    assert game_state["next_map"]["map"]["id"] == expected_map_id
    assert game_state["next_map"]["id"] == "carentan_warfare"
    assert game_state["game_mode"] is GameMode(game_mode.lower())


def test_hllv_gamestate_uses_layer_mode_during_map_transition():
    ctl = HLLVServerCtl(ServerInfo(game=GameEnum.HLL_VIETNAM), Mock())
    ctl.exchange = Mock(
        side_effect=[
            _response(_session("wdeve_offensivenva_day", "")),
            _response(
                {
                    "mAPS": [{"iD": "wdeve_offensivenva_day"}],
                    "currentIndex": 0,
                }
            ),
        ]
    )

    game_state = ctl.get_gamestate()

    assert game_state["current_map"]["id"] == "wdeve_offensivenva_day"
    assert game_state["game_mode"] is GameMode.OFFENSIVE


def test_game_specific_controller_surface():
    hll = HLLServerCtl(ServerInfo(game=GameEnum.HLL_WW2), Mock())
    hllv = HLLVServerCtl(ServerInfo(game=GameEnum.HLL_VIETNAM), Mock())

    for method_name in (
        "get_map_sequence",
        "set_game_layout",
        "set_dynamic_weather_enabled",
    ):
        assert callable(getattr(hll, method_name))
        assert callable(getattr(hllv, method_name))


@pytest.mark.parametrize(
    ("game", "expected_type"),
    [
        (GameEnum.HLL_WW2, HLLRcon),
        (GameEnum.HLL_VIETNAM, HLLVRcon),
    ],
)
def test_rcon_factory_selects_concrete_game_controller(
    monkeypatch, game, expected_type
):
    monkeypatch.setattr(Rcon, "__init__", lambda self, *args, **kwargs: None)

    ctl = create_rcon(ServerInfo(game=game))

    assert type(ctl) is expected_type
    assert ctl.game_test_command() is game


def test_concrete_rcon_classes_share_commands_but_identify_their_game():
    for method_name in (
        "get_map_sequence",
        "get_objective_rows",
        "set_game_layout",
        "set_dynamic_weather_enabled",
    ):
        assert hasattr(HLLRcon, method_name)
        assert hasattr(HLLVRcon, method_name)

    assert HLLRcon.game_test_command(None) is GameEnum.HLL_WW2
    assert HLLVRcon.game_test_command(None) is GameEnum.HLL_VIETNAM


def test_detailed_player_parser_receives_controller_game(monkeypatch):
    parser = Mock(return_value={"player_id": "player-1"})
    monkeypatch.setattr("rcon.rcon.parse_raw_player_info", parser)
    ctl = HLLVRcon(ServerInfo(game=GameEnum.HLL_VIETNAM))
    player_info = {"iD": "player-1"}

    result = ctl._get_detailed_player_info(
        player_info,
        {"is_vip": True, "profile": None},
    )

    parser.assert_called_once_with(player_info, GameEnum.HLL_VIETNAM)
    assert result["is_vip"] is True
    assert result["profile"] is None


@pytest.mark.parametrize(
    ("game", "expected_type"),
    [
        (GameEnum.HLL_WW2, HLLRconAPI),
        (GameEnum.HLL_VIETNAM, HLLVRconAPI),
    ],
)
def test_rcon_api_factory_selects_concrete_game_controller(
    monkeypatch, game, expected_type
):
    monkeypatch.setattr(RconAPI, "__init__", lambda self, *args, **kwargs: None)

    ctl = create_rcon_api(ServerInfo(game=game))

    assert type(ctl) is expected_type
    assert ctl.game_test_command() is game


def test_api_classes_share_commands_and_keep_concrete_game_identity():
    assert hasattr(HLLRconAPI, "get_map_sequence")
    assert hasattr(HLLRconAPI, "set_dynamic_weather_enabled")
    assert hasattr(HLLVRconAPI, "get_map_sequence")
    assert hasattr(HLLVRconAPI, "set_dynamic_weather_enabled")
    assert HLLRconAPI.game_test_command(None) is GameEnum.HLL_WW2
    assert HLLVRconAPI.game_test_command(None) is GameEnum.HLL_VIETNAM


def test_timer_commands_validate_mode_against_profile():
    ctl = HLLVServerCtl(ServerInfo(game=GameEnum.HLL_VIETNAM), Mock())
    ctl.exchange = Mock()

    ctl.set_match_timer("Domination", 30)
    ctl.exchange.assert_called_once_with(
        "SetMatchTimer", 2, {"GameMode": "domination", "MatchLength": 30}
    )

    with pytest.raises(ValueError, match="not supported by the 'hllv' game profile"):
        ctl.set_match_timer(GameMode.SKIRMISH, 30)


@pytest.mark.parametrize(
    ("ctl_type", "game", "command"),
    [
        (HLLServerCtl, GameEnum.HLL_WW2, "SetWelcomeMessage"),
        (HLLVServerCtl, GameEnum.HLL_VIETNAM, "SetNoticeMessage"),
    ],
)
def test_welcome_message_uses_game_specific_command(ctl_type, game, command):
    ctl = ctl_type(ServerInfo(game=game), Mock())
    ctl.exchange = Mock()

    ctl.set_welcome_message("Welcome")

    ctl.exchange.assert_called_once_with(command, 2, {"Message": "Welcome"})


def test_hllv_votemap_whitelist_uses_selected_game_profile(monkeypatch):
    votemap = Mock()
    monkeypatch.setattr("rcon.api_commands.VoteMap", Mock(return_value=votemap))
    ctl = HLLVRconAPI(ServerInfo(game=GameEnum.HLL_VIETNAM))

    ctl.set_votemap_whitelist(["wdeva_warfare_day"])

    votemap.set_map_whitelist.assert_called_once_with(
        [HLLV_PROFILE.parse_layer("wdeva_warfare_day")]
    )
