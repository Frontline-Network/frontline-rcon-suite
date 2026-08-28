from contextlib import nullcontext
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from rcon.api_commands import (
    HLLRconAPI,
    HLLVRconAPI,
    RconAPI,
    create_rcon_api,
)
from rcon.commands import HLLCommandFailedError, HLLServerCtl, HLLVServerCtl
from rcon.connection import HLLBrokenConnectionError, HLLCommandError
from rcon.game import get_game_profile
from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv import legacy_layers
from rcon.game.hllv.legacy_layers import (
    HLLV_LEGACY_CATALOG_VERSION,
    report_unknown_hllv_layer,
)
from rcon.game.hllv.profile import HLLV_PROFILE
from rcon.maps import UNKNOWN_MAP_NAME, GameMode, Team
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
    ("controller_type", "leader_role"),
    [
        (HLLRcon, "officer"),
        (HLLRcon, "artilleryobserver"),
        (HLLVRcon, "squadleader"),
        (HLLVRcon, "mortarobserver"),
        (HLLVRcon, "helicopterlogisticsofficer"),
    ],
)
def test_no_leader_automod_detects_game_specific_squad_leaders(
    controller_type, leader_role
):
    controller = controller_type.__new__(controller_type)
    controller.config = SimpleNamespace(game=controller_type.game_test_command(None))

    assert controller._has_leader({"players": [{"role": leader_role}]}) is True
    assert controller._has_leader({"players": [{"role": "rifleman"}]}) is False


@pytest.mark.parametrize(
    ("controller_type", "game"),
    [
        (HLLServerCtl, GameEnum.HLL_WW2),
        (HLLVServerCtl, GameEnum.HLL_VIETNAM),
    ],
)
def test_get_slots_keeps_plausible_counts_without_player_list_lookup(
    controller_type, game
):
    controller = controller_type(ServerInfo(game=game), Mock())
    controller.exchange = Mock(
        return_value=_response({"playerCount": 42, "maxPlayerCount": 100})
    )

    assert controller.get_slots() == {
        "current_players": 42,
        "max_players": 100,
    }
    controller.exchange.assert_called_once_with(
        "GetServerInformation", 2, {"Name": "session", "Value": ""}
    )


def test_get_slots_replaces_implausible_hll_count_with_connected_player_count(
    caplog,
):
    controller = HLLServerCtl(ServerInfo(game=GameEnum.HLL_WW2), Mock())
    controller.exchange = Mock(
        side_effect=[
            _response({"playerCount": 10031, "maxPlayerCount": 100}),
            _response(
                {
                    "players": [
                        {"name": "Player 1", "iD": "1"},
                        {"name": "Player 2", "iD": "2"},
                        {"name": "Player 3", "iD": "3"},
                        {"name": "Player 4", "iD": "4"},
                        {"name": "Player 5", "iD": "5"},
                        {"name": "Player 6", "iD": "6"},
                    ]
                }
            ),
        ]
    )

    assert controller.get_slots() == {
        "current_players": 6,
        "max_players": 100,
    }
    assert controller.exchange.call_args_list == [
        call("GetServerInformation", 2, {"Name": "session", "Value": ""}),
        call("GetServerInformation", 2, {"Name": "players", "Value": ""}),
    ]
    assert "current=10031, max=100" in caplog.text


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


@pytest.mark.parametrize(
    ("controller_type", "game", "known_weapon"),
    [
        (HLLRconAPI, GameEnum.HLL_WW2, "155MM HOWITZER [M114]"),
        (HLLVRconAPI, GameEnum.HLL_VIETNAM, None),
    ],
)
def test_available_weapon_catalog_uses_active_game_profile(
    controller_type, game, known_weapon
):
    controller = controller_type.__new__(controller_type)
    controller.config = SimpleNamespace(game=game)
    controller.game_profile = get_game_profile(game)

    result = controller.get_available_weapons()

    assert result["game"] == game.value
    names = [weapon["name"] for weapon in result["weapons"]]
    assert names == sorted(names, key=str.casefold)
    if known_weapon:
        assert known_weapon in names
    else:
        assert names == []


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


def test_hllv_legacy_catalog_preserves_historical_layer_metadata():
    layer = HLLV_PROFILE.parse_layer("wdevc_warfare_day")

    assert layer.map.pretty_name == "Huế Outskirts"
    assert layer.map.allies.name == "us"
    assert layer.map.axis.name == "nva"
    assert layer.game_mode is GameMode.WARFARE


def test_hllv_legacy_alias_migrates_to_canonical_executable_layer():
    layer = HLLV_PROFILE.parse_layer("hue_outskirts_offensive_nva")

    assert layer.id == "wdevc_offensivenva_day"
    assert layer.map.pretty_name == "Huế Outskirts"
    assert layer.game_mode is GameMode.OFFENSIVE
    assert layer.attackers is Team.AXIS


def test_hllv_unknown_layers_emit_bounded_catalog_telemetry(monkeypatch):
    report_unknown_hllv_layer.cache_clear()
    calls = []
    monkeypatch.setattr(
        legacy_layers.logger,
        "warning",
        lambda message, *args: calls.append(message % args),
    )

    first = HLLV_PROFILE.parse_layer("future_hllv_layer")
    second = HLLV_PROFILE.parse_layer("future_hllv_layer")

    assert first.id == second.id == "future_hllv_layer"
    assert len(calls) == 1
    assert "Unknown HLLV layer id" in calls[0]
    assert HLLV_LEGACY_CATALOG_VERSION in calls[0]


def test_hllv_profile_exposes_live_role_catalog():
    assert {
        "squadleader",
        "mortarobserver",
        "mortargunner",
        "mortarsupport",
        "helicopterlogisticsofficer",
        "helicopterpilot",
    } <= HLLV_PROFILE.roles
    assert HLLV_PROFILE.role_labels["helicopterpilot"] == "Pilot"


def test_profiles_only_accept_their_supported_game_modes():
    assert HLL_PROFILE.parse_game_mode("Skirmish") is GameMode.SKIRMISH
    assert HLLV_PROFILE.parse_game_mode("Domination") is GameMode.DOMINATION

    with pytest.raises(ValueError, match="not supported by the 'hll' game profile"):
        HLL_PROFILE.parse_game_mode("Domination")

    with pytest.raises(ValueError, match="not supported by the 'hllv' game profile"):
        HLLV_PROFILE.parse_game_mode("Skirmish")


@pytest.mark.parametrize(
    (
        "controller_type",
        "game",
        "expected_modes",
        "unsupported_mode",
        "match_timer_modes",
        "warmup_timer_modes",
    ),
    [
        (
            HLLRcon,
            GameEnum.HLL_WW2,
            {"warfare", "offensive", "conquest", "skirmish", "phased", "majority"},
            "domination",
            ["offensive", "skirmish", "warfare"],
            ["skirmish", "warfare"],
        ),
        (
            HLLVRcon,
            GameEnum.HLL_VIETNAM,
            {"warfare", "offensive", "conquest", "domination"},
            "skirmish",
            ["offensive", "warfare"],
            ["warfare"],
        ),
    ],
)
def test_status_exposes_game_profile_without_requiring_connection_info_permission(
    monkeypatch,
    controller_type,
    game,
    expected_modes,
    unsupported_mode,
    match_timer_modes,
    warmup_timer_modes,
):
    controller = controller_type(ServerInfo(game=game))
    controller.get_name = Mock(return_value="Profile test")
    controller.get_slots = Mock(
        return_value={"current_players": 42, "max_players": 100}
    )
    controller.get_gamestate = Mock(return_value={"current_map": {"id": "map"}})
    monkeypatch.setattr(
        "rcon.rcon.RconServerSettingsUserConfig.load_from_db",
        lambda: SimpleNamespace(short_name="Profile"),
    )
    monkeypatch.setattr("rcon.rcon.get_server_number", lambda: 3)

    status = Rcon.get_status.__wrapped__(controller)

    assert status["game"] == game.value
    assert set(status["supported_game_modes"]) == expected_modes
    assert unsupported_mode not in status["supported_game_modes"]
    assert status["game_capabilities"] == {
        "match_timer_modes": match_timer_modes,
        "warmup_timer_modes": warmup_timer_modes,
        "sector_layout": {"read": True, "set": True, "remove": False},
    }
    assert status["server_number"] == 3


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


@pytest.mark.parametrize(
    ("controller_type", "game", "player_id"),
    [
        (HLLServerCtl, GameEnum.HLL_WW2, "76561198036685843"),
        (
            HLLVServerCtl,
            GameEnum.HLL_VIETNAM,
            "00026a3466a244829409f77af0a752d9",
        ),
    ],
)
def test_report_bot_moderation_commands_share_the_game_advertised_contract(
    controller_type, game, player_id
):
    controller = controller_type(ServerInfo(game=game), Mock())
    controller.exchange_success = Mock(return_value=True)

    assert controller.message_player(player_id, "Message") is True
    assert controller.punish(player_id, "Reason") is True
    assert controller.kick(player_id, "Reason") is True
    assert controller.temp_ban(player_id, 2, "Reason", "Moderator") is True
    assert controller.perma_ban(player_id, "Reason", "Moderator") is True
    assert controller.remove_player_from_squad(player_id, "Reason") is True

    controller.exchange_success.assert_has_calls(
        [
            call("MessagePlayer", 2, {"Message": "Message", "PlayerId": player_id}),
            call("PunishPlayer", 2, {"PlayerId": player_id, "Reason": "Reason"}),
            call("KickPlayer", 2, {"PlayerId": player_id, "Reason": "Reason"}),
            call(
                "TemporaryBanPlayer",
                2,
                {
                    "PlayerId": player_id,
                    "Duration": 2,
                    "Reason": "Reason",
                    "AdminName": "Moderator",
                },
            ),
            call(
                "PermanentBanPlayer",
                2,
                {
                    "PlayerId": player_id,
                    "Reason": "Reason",
                    "AdminName": "Moderator",
                },
            ),
            call(
                "RemovePlayerFromPlatoon",
                2,
                {"PlayerId": player_id, "Reason": "Reason"},
            ),
        ]
    )


def test_rcon_internal_error_retries_message_player_once(monkeypatch):
    controller = HLLServerCtl(ServerInfo(game=GameEnum.HLL_WW2), Mock())
    handle = Mock()
    handle.request = SimpleNamespace(
        name="MessagePlayer",
        version=2,
        content={"PlayerId": "player-id", "Message": "Hello"},
    )
    handle.receive.side_effect = HLLCommandError(
        500, "Unable to perform request. The server encountered an error."
    )
    retry_response = Mock()
    retry_response.is_successful.return_value = True
    retry_connection = Mock()
    retry_connection.exchange.return_value = retry_response
    controller.with_connection = Mock(return_value=nullcontext(retry_connection))
    sleep = Mock()
    monkeypatch.setattr("rcon.commands.time.sleep", sleep)

    assert controller.receive_success(handle) is True
    sleep.assert_called_once()
    assert 0 < sleep.call_args.args[0] <= 8
    retry_connection.exchange.assert_called_once_with(
        "MessagePlayer",
        2,
        {"PlayerId": "player-id", "Message": "Hello"},
    )


def test_rcon_internal_error_after_retry_is_not_downgraded_to_false(monkeypatch):
    controller = HLLServerCtl(ServerInfo(game=GameEnum.HLL_WW2), Mock())
    handle = Mock()
    handle.request = SimpleNamespace(name="KickPlayer", version=2, content={})
    handle.receive.side_effect = HLLCommandError(500, "first failure")
    retry_response = Mock()
    retry_response.is_successful.side_effect = HLLCommandError(500, "second failure")
    retry_connection = Mock()
    retry_connection.exchange.return_value = retry_response
    controller.with_connection = Mock(return_value=nullcontext(retry_connection))
    monkeypatch.setattr("rcon.commands.time.sleep", Mock())

    with pytest.raises(HLLCommandError, match="second failure"):
        controller.receive_success(handle)


def test_rcon_client_error_is_not_retried(monkeypatch):
    controller = HLLServerCtl(ServerInfo(game=GameEnum.HLL_WW2), Mock())
    handle = Mock()
    handle.request = SimpleNamespace(name="MessagePlayer", version=2, content={})
    handle.receive.side_effect = HLLCommandError(400, "invalid player")
    controller.with_connection = Mock()
    sleep = Mock()
    monkeypatch.setattr("rcon.commands.time.sleep", sleep)

    with pytest.raises(HLLCommandError, match="invalid player"):
        controller.receive_success(handle)
    sleep.assert_not_called()
    controller.with_connection.assert_not_called()


def test_broken_connection_retries_send_with_a_fresh_connection(monkeypatch):
    controller = HLLServerCtl(ServerInfo(game=GameEnum.HLL_WW2), Mock())
    broken_connection = Mock()
    broken_connection.send.side_effect = HLLBrokenConnectionError("connection lost")
    retry_handle = Mock()
    retry_connection = Mock()
    retry_connection.send.return_value = retry_handle
    controller.with_connection = Mock(
        side_effect=[
            nullcontext(broken_connection),
            nullcontext(retry_connection),
        ]
    )
    sleep = Mock()
    monkeypatch.setattr("rcon.commands.time.sleep", sleep)

    assert (
        controller.send("MessagePlayer", 2, {"PlayerId": "player-id"}) is retry_handle
    )
    # Retries deliberately use a bounded jittered backoff so several CRCON
    # workers do not reconnect to the game server in lockstep.
    sleep.assert_called_once()
    assert 0 < sleep.call_args.args[0] <= 1
    retry_connection.send.assert_called_once_with(
        "MessagePlayer", 2, {"PlayerId": "player-id"}
    )


def test_explicit_connection_send_is_never_retried(monkeypatch):
    controller = HLLServerCtl(ServerInfo(game=GameEnum.HLL_WW2), Mock())
    explicit_connection = Mock()
    explicit_connection.send.side_effect = OSError("socket closed")
    sleep = Mock()
    monkeypatch.setattr("rcon.commands.time.sleep", sleep)

    with pytest.raises(OSError, match="socket closed"):
        controller.send(
            "MessagePlayer",
            2,
            {"PlayerId": "player-id"},
            conn=explicit_connection,
        )
    sleep.assert_not_called()


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


def test_hllv_objective_rows_ignore_map_id_reference_parameter():
    ctl = HLLVServerCtl(ServerInfo(game=GameEnum.HLL_VIETNAM), Mock())
    ctl.exchange = Mock(
        return_value=_response(
            {
                "dialogueParameters": [
                    {"iD": "MapId", "valueMember": "wdevb_warfare_day"},
                    *[
                        {"iD": f"Sector_{index}", "valueMember": "0,1,2"}
                        for index in range(1, 6)
                    ],
                ]
            }
        )
    )

    assert ctl.get_objective_rows() == [["0", "1", "2"]] * 5
    ctl.exchange.assert_called_once_with(
        "GetClientReferenceData", 2, "SetSectorLayout"
    )


def test_hllv_objective_rows_fail_with_actionable_protocol_error():
    ctl = HLLVServerCtl(ServerInfo(game=GameEnum.HLL_VIETNAM), Mock())
    ctl.exchange = Mock(return_value=_response({"dialogueParameters": []}))

    with pytest.raises(
        HLLCommandFailedError,
        match="did not expose selectable sector-layout values",
    ):
        ctl.get_objective_rows()


def test_profiles_expose_sector_layout_capability_matrix():
    assert HLL_PROFILE.sector_layout.as_dict() == {
        "read": True,
        "set": True,
        "remove": False,
    }
    assert HLLV_PROFILE.sector_layout.as_dict() == {
        "read": True,
        "set": True,
        "remove": False,
    }


def test_hllv_set_sector_layout_includes_current_map_id_and_integer_indices():
    ctl = HLLVServerCtl(ServerInfo(game=GameEnum.HLL_VIETNAM), Mock())
    ctl.get_map = Mock(return_value="wdeve_warfare_day")
    ctl.exchange = Mock(return_value=_response({}))

    assert ctl.set_game_layout(["0", "1", "2", "1", "0"]) == [
        "0",
        "1",
        "2",
        "1",
        "0",
    ]
    ctl.exchange.assert_called_once_with(
        "SetSectorLayout",
        2,
        {
            "MapId": "wdeve_warfare_day",
            "Sector_1": 0,
            "Sector_2": 1,
            "Sector_3": 2,
            "Sector_4": 1,
            "Sector_5": 0,
        },
    )


@pytest.mark.parametrize(
    ("ctl_type", "game"),
    [
        (HLLRcon, GameEnum.HLL_WW2),
        (HLLVRcon, GameEnum.HLL_VIETNAM),
    ],
)
def test_map_sequence_replacement_keeps_one_entry_until_the_replacement_is_ready(
    monkeypatch, ctl_type, game
):
    ctl = ctl_type(ServerInfo(game=game))
    ctl.get_map_sequence = Mock(
        return_value={
            "maps": [SimpleNamespace(id="old_a"), SimpleNamespace(id="old_b")],
            "current_index": 0,
        }
    )
    remove = Mock()
    add = Mock()
    monkeypatch.setattr("rcon.rcon.ServerCtl.remove_map_from_sequence_at_index", remove)
    monkeypatch.setattr("rcon.rcon.ServerCtl.add_map_to_sequence_at_index", add)

    ctl.set_map_sequence(["new_a", "new_b", "new_c", "new_d", "new_e"])

    remove.assert_has_calls([call(1), call(0)])
    add.assert_has_calls(
        [
            call("new_a", 1),
            call("new_b", 2),
            call("new_c", 3),
            call("new_d", 4),
            call("new_e", 5),
        ]
    )


@pytest.mark.parametrize(
    ("ctl_type", "game"),
    [
        (HLLRcon, GameEnum.HLL_WW2),
        (HLLVRcon, GameEnum.HLL_VIETNAM),
    ],
)
def test_map_sequence_replacement_rejects_empty_requests_before_mutation(ctl_type, game):
    ctl = ctl_type(ServerInfo(game=game))

    with pytest.raises(HLLCommandFailedError, match="Empty map sequence"):
        ctl.set_map_sequence([])


@pytest.mark.parametrize(
    ("ctl_type", "game"),
    [
        (HLLRcon, GameEnum.HLL_WW2),
        (HLLVRcon, GameEnum.HLL_VIETNAM),
    ],
)
def test_map_sequence_replacement_handles_a_single_existing_entry(
    monkeypatch, ctl_type, game
):
    ctl = ctl_type(ServerInfo(game=game))
    ctl.get_map_sequence = Mock(
        return_value={
            "maps": [SimpleNamespace(id="old_a")],
            "current_index": 0,
        }
    )
    remove = Mock()
    add = Mock()
    monkeypatch.setattr("rcon.rcon.ServerCtl.remove_map_from_sequence_at_index", remove)
    monkeypatch.setattr("rcon.rcon.ServerCtl.add_map_to_sequence_at_index", add)

    ctl.set_map_sequence(["new_a"])

    add.assert_called_once_with("new_a", 1)
    remove.assert_called_once_with(0)


@pytest.mark.parametrize(
    ("ctl_type", "game"),
    [
        (HLLRcon, GameEnum.HLL_WW2),
        (HLLVRcon, GameEnum.HLL_VIETNAM),
    ],
)
def test_map_sequence_primitives_validate_and_normalize_indices(
    monkeypatch, ctl_type, game
):
    ctl = ctl_type(ServerInfo(game=game))
    ctl.get_map_sequence = Mock(
        return_value={
            "maps": [
                SimpleNamespace(id="first"),
                SimpleNamespace(id="second"),
                SimpleNamespace(id="third"),
            ],
            "current_index": 0,
        }
    )
    add = Mock()
    remove = Mock()
    move = Mock()
    monkeypatch.setattr("rcon.rcon.ServerCtl.add_map_to_sequence_at_index", add)
    monkeypatch.setattr("rcon.rcon.ServerCtl.remove_map_from_sequence_at_index", remove)
    monkeypatch.setattr("rcon.rcon.ServerCtl.move_map_in_sequence", move)

    ctl.add_map_to_sequence_at_index("last", -1)
    ctl.remove_map_from_sequence_at_index(-1)
    ctl.move_map_in_sequence(0, 2)

    add.assert_called_once_with("last", 3)
    remove.assert_called_once_with(2)
    move.assert_called_once_with(0, 2)
    with pytest.raises(ValueError, match="insertion index"):
        ctl.add_map_to_sequence_at_index("bad", 5)
    with pytest.raises(ValueError, match="removal index"):
        ctl.remove_map_from_sequence_at_index(3)
    with pytest.raises(ValueError, match="Current map sequence index"):
        ctl.move_map_in_sequence(3, 0)


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
