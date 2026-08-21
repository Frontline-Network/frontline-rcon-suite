import pytest

from rcon.game.hll.player_adapter import HLLPlayerInfoAdapter
from rcon.game.hll.profile import HLL_PROFILE
from rcon.game.hllv.player_adapter import HLLVPlayerInfoAdapter
from rcon.game.hllv.profile import HLLV_PROFILE
from rcon.game.player_adapter import PlayerResponseAdapterError


def test_hll_adapter_normalizes_legacy_hll_packet_to_canonical_dto():
    player = HLLPlayerInfoAdapter().adapt(
        {
            "iD": "76561198000000001",
            "eosId": "eos-hll",
            "steamId": "76561198000000001",
            "name": "HLL Player",
            "team": "2",
            "role": "5",
            "level": "42",
            "loadout": "Standard Issue",
            "platoon": "Able",
            "platoonIndex": "1",
            "scoreData": {"cOMBAT": "5", "offense": 6, "defense": 7, "support": 8},
            "stats": {
                "teamKills": 1,
                "vehicleKills": 2,
                "vehiclesDestroyed": 3,
                "infantryKills": 4,
                "deaths": 5,
            },
            "platform": "steam",
            "clanTag": "FLN",
            "worldPosition": {"x": "1.5", "y": 2, "z": 3},
        }
    )

    assert player == {
        "iD": "76561198000000001",
        "eosId": "eos-hll",
        "steamId": "76561198000000001",
        "name": "HLL Player",
        "team": 2,
        "role": 5,
        "level": 42,
        "loadout": "Standard Issue",
        "platoon": "Able",
        "platoonIndex": 1,
        "scoreData": {"cOMBAT": 5, "offense": 6, "defense": 7, "support": 8},
        "stats": {
            "teamKills": 1,
            "vehicleKills": 2,
            "vehiclesDestroyed": 3,
            "infantryKills": 4,
            "deaths": 5,
        },
        "platform": "steam",
        "clanTag": "FLN",
        "worldPosition": {"x": 1.5, "y": 2.0, "z": 3.0},
    }


def test_hllv_adapter_accepts_documented_v2_spelling_without_hll_assumptions():
    player = HLLVPlayerInfoAdapter().adapt(
        {
            "iD": "hllv-account-id",
            "Id": "hllv-eos-id",
            "SteamId": "76561198000000002",
            "Name": "HLLV Player",
            "Team": 6,
            "Role": 28,
            "Level": "99",
            "Loadout": "Rifleman",
            "Platoon": "Bravo",
            "PlatoonIndex": 2,
            "ScoreData": {"Combat": 10, "Offense": 11, "Defense": 12, "Support": 13},
            "Stats": {
                "TeamKills": 1,
                "VehicleKills": 2,
                "VehiclesDestroyed": 3,
                "InfantryKills": 4,
                "Deaths": 5,
            },
            "Platform": "steam",
            "ClanTag": "FLN",
            "WorldPosition": {"X": 4, "Y": 5.5, "Z": "6.5"},
        }
    )

    assert player["iD"] == "hllv-account-id"
    assert player["eosId"] == "hllv-eos-id"
    assert player["steamId"] == "76561198000000002"
    assert player["scoreData"] == {
        "cOMBAT": 10,
        "offense": 11,
        "defense": 12,
        "support": 13,
    }
    assert player["stats"]["infantryKills"] == 4
    assert player["worldPosition"] == {"x": 4.0, "y": 5.5, "z": 6.5}


def test_each_game_profile_owns_its_player_protocol_adapter():
    assert isinstance(HLL_PROFILE.player_adapter, HLLPlayerInfoAdapter)
    assert isinstance(HLLV_PROFILE.player_adapter, HLLVPlayerInfoAdapter)


@pytest.mark.parametrize("raw", [{}, {"iD": "player-only"}, {"name": "name-only"}])
def test_player_adapter_rejects_packets_that_cannot_be_safely_attributed(raw):
    with pytest.raises(PlayerResponseAdapterError):
        HLLVPlayerInfoAdapter().adapt(raw)
