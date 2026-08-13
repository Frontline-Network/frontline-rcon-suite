import pytest

from rcon.types import GetDetailedPlayer, GameEnum
from rcon.utils import get_squad_leader_roles, parse_raw_player_info


def mock_get_detailed_player(
    name="",
    clan_tag="GH",
    eos_id="",
    steam_id=None,
    platform="steam",
    world_position={},
    player_id="0",
    team="",
    faction="",
    role="",
    unit_id=0,
    unit_name="",
    loadout="",
    kills=0,
    deaths=0,
    team_kills=0,
    vehicle_kills=0,
    vehicles_destroyed=0,
    combat=0,
    defense=0,
    offense=0,
    support=0,
    level=1,
    is_vip=False,
    profile=None,
    map_playtime_seconds=0,
) -> GetDetailedPlayer:
    return {
        "name": name,
        "clan_tag": clan_tag,
        "eos_id": eos_id,
        "platform": platform,
        "world_position": world_position,
        "player_id": player_id,
        "steam_id": steam_id,
        "team": team,
        "faction": faction,
        "role": role,
        "unit_id": unit_id,
        "unit_name": unit_name,
        "combat": combat,
        "deaths": deaths,
        "kills": kills,
        "team_kills": team_kills,
        "vehicle_kills": vehicle_kills,
        "vehicles_destroyed": vehicles_destroyed,
        "defense": defense,
        "level": level,
        "loadout": loadout,
        "offense": offense,
        "support": support,
        "is_vip": is_vip,
        "profile": profile,
        "map_playtime_seconds": map_playtime_seconds,
    }


@pytest.mark.parametrize(
    "raw, expected",
    [
        (
            {
                "iD": "76561199502921234",
                "team": 0,
                "role": 5,
                "level": "16",
                "loadout": "Standard Issue",
                "name": "MasterShake",
                "platoon": "JIG",
                "scoreData": {
                    "cOMBAT": 72,
                    "offense": 100,
                    "defense": 220,
                    "support": 65,
                },
                "stats": {
                    "teamKills": 1,
                    "vehicleKills": 2,
                    "vehiclesDestroyed": 3,
                    "infantryKills": 11,
                    "deaths": 9,
                },
                "platform": "steam",
                "clanTag": "GH",
                "eosId": "",
                "worldPosition": {},
            },
            mock_get_detailed_player(
                name="MasterShake",
                clan_tag="GH",
                eos_id="",
                platform="steam",
                world_position={},
                player_id="76561199502921234",
                steam_id="76561199502921234",
                team="axis",
                faction="ger",
                role="support",
                unit_id=9,
                unit_name="jig",
                loadout="standard issue",
                kills=11,
                deaths=9,
                combat=72,
                offense=100,
                defense=220,
                support=65,
                level=16,
                team_kills=1,
                vehicle_kills=2,
                vehicles_destroyed=3,
            ),
        ),
        (
            {
                "iD": "a21af8b5-59df-5vbr-88gf-ab4239r4g6f4",
                "team": 1,
                "role": 0,
                "level": "16",
                "loadout": "Standard Issue",
                "name": "MasterShake",
                "platoon": "ABLE",
                "scoreData": {
                    "cOMBAT": 72,
                    "offense": 100,
                    "defense": 220,
                    "support": 65,
                },
                "stats": {
                    "teamKills": 1,
                    "vehicleKills": 2,
                    "vehiclesDestroyed": 3,
                    "infantryKills": 11,
                    "deaths": 9,
                },
                "platform": "steam",
                "clanTag": "GH",
                "eosId": "",
                "worldPosition": {},
            },
            mock_get_detailed_player(
                name="MasterShake",
                clan_tag="GH",
                eos_id="",
                platform="steam",
                world_position={},
                player_id="a21af8b5-59df-5vbr-88gf-ab4239r4g6f4",
                team="allies",
                faction="us",
                role="rifleman",
                unit_id=0,
                unit_name="able",
                loadout="standard issue",
                kills=11,
                deaths=9,
                combat=72,
                offense=100,
                defense=220,
                support=65,
                level=16,
                team_kills=1,
                vehicle_kills=2,
                vehicles_destroyed=3,
            ),
        ),
    ],
)
def test_parse_raw_player_info(raw, expected):
    assert parse_raw_player_info(raw=raw, game=GameEnum.HLL_WW2) == expected


@pytest.mark.parametrize(
    "raw_team, faction, team",
    [
        (1, "us", "allies"),
        (6, "nva", "axis"),
    ],
)
def test_parse_hllv_player_uses_crcon_logical_team_names(raw_team, faction, team):
    raw = {
        "iD": "hllv-player-id",
        "steamId": "76561199502921234",
        "team": raw_team,
        "role": 0,
        "level": 16,
        "loadout": "Standard Issue",
        "name": "MasterShake",
        "platoon": "ABLE",
        "scoreData": {
            "cOMBAT": 72,
            "offense": 100,
            "defense": 220,
            "support": 65,
        },
        "stats": {
            "teamKills": 1,
            "vehicleKills": 2,
            "vehiclesDestroyed": 3,
            "infantryKills": 11,
            "deaths": 9,
        },
        "platform": "steam",
        "clanTag": "GH",
        "worldPosition": {},
    }

    parsed = parse_raw_player_info(raw=raw, game=GameEnum.HLL_VIETNAM)

    assert parsed["faction"] == faction
    assert parsed["team"] == team


def test_hllv_squad_leader_roles_include_vietnam_unit_leaders():
    leader_roles = get_squad_leader_roles(GameEnum.HLL_VIETNAM)

    assert {
        "squadleader",
        "tankcommander",
        "spotter",
        "mortarobserver",
        "helicopterlogisticsofficer",
    } <= leader_roles


def test_hll_squad_leader_roles_keep_ww2_officers():
    leader_roles = get_squad_leader_roles(GameEnum.HLL_WW2)

    assert {"officer", "tankcommander", "spotter", "artilleryobserver"} <= leader_roles
