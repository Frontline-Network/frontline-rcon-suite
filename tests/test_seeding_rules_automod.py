import time
from contextlib import contextmanager
from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest
from _pytest.fixtures import fixture

from rcon.automods.get_team_count import get_team_count
from rcon.automods.models import (
    NoSeedingViolation,
    PunishDetails,
    PunishPlayer,
    PunitionsToApply,
    WatchStatus,
)
from rcon.automods.seeding_rules import SeedingRulesAutomod, connection_key
from rcon.maps import GameMode
from rcon.types import GameStateType, StructuredLogLineWithMetaData
from rcon.user_config.auto_mod_seeding import (
    AutoModSeedingUserConfig,
    DisallowedRoles,
    DisallowedWeapons,
    EnforceCapFight,
    Roles,
)

state = {}
redis_store = {}


@fixture
def team_view():
    global state, redis_store
    state = {}
    redis_store = {}
    return {
        "allies": {
            "combat": 0,
            "commander": {
                "combat": 50,
                "country": "",
                "deaths": 6,
                "defense": 500,
                "is_vip": False,
                "kills": 6,
                "level": 123,
                "loadout": "standard issue",
                "name": "FamousCommander",
                "offense": 480,
                "profile": None,
                "role": "armycommander",
                "steam_bans": None,
                "player_id": "76561198206929556",
                "support": 264,
                "team": "allies",
                "unit_id": -1,
                "unit_name": "Commander",
            },
            "count": 0,
            "deaths": 0,
            "defense": 0,
            "kills": 0,
            "offense": 0,
            "squads": {
                "able": {
                    "combat": 135,
                    "deaths": 10,
                    "defense": 600,
                    "has_leader": False,
                    "kills": 12,
                    "offense": 960,
                    "players": [
                        {
                            "combat": 50,
                            "country": "",
                            "deaths": 6,
                            "defense": 500,
                            "is_vip": False,
                            "kills": 6,
                            "level": 123,
                            "loadout": "standard issue",
                            "name": "WilliePeter",
                            "offense": 480,
                            "profile": None,
                            "role": "tankcommander",
                            "steam_bans": None,
                            "player_id": "76561198206929555",
                            "support": 264,
                            "team": "allies",
                            "unit_id": 1,
                            "unit_name": "able",
                        },
                        {
                            "combat": 50,
                            "country": "",
                            "deaths": 6,
                            "defense": 500,
                            "is_vip": False,
                            "kills": 6,
                            "level": 123,
                            "loadout": "standard issue",
                            "name": "AnotherPeter",
                            "offense": 480,
                            "profile": None,
                            "role": "crewman",
                            "steam_bans": None,
                            "player_id": "76561198206929556",
                            "support": 264,
                            "team": "allies",
                            "unit_id": 1,
                            "unit_name": "able",
                        },
                    ],
                    "support": 264,
                    "type": "armor",
                },
            },
            "support": 0,
        },
        "axis": {
            "combat": 0,
            "commander": None,
            "count": 0,
            "deaths": 0,
            "defense": 0,
            "kills": 0,
            "offense": 0,
            "squads": {
                "able": {
                    "combat": 135,
                    "deaths": 10,
                    "defense": 600,
                    "has_leader": False,
                    "kills": 12,
                    "offense": 960,
                    "players": [
                        {
                            "combat": 50,
                            "country": "",
                            "deaths": 6,
                            "defense": 500,
                            "is_vip": False,
                            "kills": 6,
                            "level": 123,
                            "loadout": "ammo carrier",
                            "name": "WilliePeter",
                            "offense": 480,
                            "profile": None,
                            "role": "spotter",
                            "steam_bans": None,
                            "player_id": "76561198206929555",
                            "support": 264,
                            "team": "axis",
                            "unit_id": 1,
                            "unit_name": "baker",
                        },
                    ],
                    "support": 264,
                    "type": "infantry",
                },
            },
            "support": 7323,
        },
    }


game_state: GameStateType = {
    "allied_score": 3,
    "axis_score": 2,
    "current_map": {
        "id": "carentan_warfare",
        "map": {
            "id": "carentan",
            "name": "CARENTAN",
            "tag": "CAR",
            "pretty_name": "Carentan",
            "shortname": "Carentan",
            "allies": {"name": "us", "team": "allies"},
            "axis": {"name": "ger", "team": "axis"},
        },
    },
    "next_map": {
        "id": "foy_warfare",
        "map": {
            "id": "foy",
            "name": "FOY",
            "tag": "FOY",
            "pretty_name": "Foy",
            "shortname": "Foy",
            "allies": {"name": "us", "team": "allies"},
            "axis": {"name": "ger", "team": "axis"},
        },
    },
    "num_allied_players": 30,
    "num_axis_players": 30,
    "time_remaining": timedelta(10),
    "raw_time_remaining": "00:00:10",
    "game_mode": GameMode.WARFARE,
}

line = "[29:42 min (1606340690)] KILL: [CPC] [1.Fjg] FlorianSW(Allies/76561198012102485) -> Karadoc(Axis/76561198080212634) with MK2_Grenade"
lt = datetime.fromtimestamp(1606340690)
kill_event_log: StructuredLogLineWithMetaData = {
    "version": 1,
    "timestamp_ms": int(lt.timestamp() * 1000),
    "event_time": lt,
    "relative_time_ms": (lt - datetime.now()).total_seconds() * 1000,
    "raw": line,
    "line_without_time": "",
    "action": "KILL",
    "player_name_1": "[1.Fjg] FlorianSW",
    "player_id_1": "76561198012102485",
    "player_name_2": "Karadoc",
    "player_id_2": "76561198080212634",
    "weapon": "MP40",
    "message": "",
    "sub_content": "",
}

expected_warned_players = [
    PunishPlayer(
        player_id="76561198206929555",
        name="WilliePeter",
        squad="able",
        team="allies",
        role="tankcommander",
        lvl=123,
        details=PunishDetails(
            author="AutoMod_SeedingRules",
            message="",
            discord_audit_url=None,
            dry_run=False,
        ),
    ),
    PunishPlayer(
        player_id="76561198206929556",
        name="AnotherPeter",
        squad="able",
        team="allies",
        role="crewman",
        lvl=123,
        details=PunishDetails(
            author="AutoMod_SeedingRules",
            message="",
            discord_audit_url=None,
            dry_run=False,
        ),
    ),
]


@contextmanager
def fake_state(team, squad_name):
    try:
        yield state.setdefault(f"{team}{squad_name}", WatchStatus())
    except NoSeedingViolation:
        del state[f"{team}{squad_name}"]


def fake_setex(k, _, v):
    redis_store[k] = v


def fake_get(k):
    return redis_store.get(k)


def fake_exists(k):
    return redis_store.get(k, None) is not None


def fake_delete(ks: str):
    redis_store.pop(ks, None)


def mod_with_config(c: AutoModSeedingUserConfig) -> SeedingRulesAutomod:
    mod = SeedingRulesAutomod(c, Mock())
    mod.red.setex = fake_setex
    mod.red.delete = fake_delete
    mod.red.get = fake_get
    mod.red.exists = fake_exists
    mod.watch_state = fake_state
    return mod


def test_disallowed_roles_does_not_enforce_below_min_players(team_view):
    min_players = (
        get_team_count(team_view, "allies") + get_team_count(team_view, "axis") + 1
    )
    max_players = (
        get_team_count(team_view, "allies") + get_team_count(team_view, "axis") + 2
    )

    config = AutoModSeedingUserConfig(
        disallowed_roles=DisallowedRoles(
            roles={
                Roles.tank_commander: "Tanks",
                Roles.crewman: "Tanks",
            },
            min_players=min_players,
            max_players=max_players,
        ),
    )

    mod = mod_with_config(config)
    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )

    assert [] == punitions.warning
    assert [] == punitions.punish
    assert [] == punitions.kick


def test_unknown_live_roles_do_not_abort_automod_cycle(team_view):
    able = team_view["allies"]["squads"]["able"]
    able["players"][0]["role"] = "specialist"
    able["players"][1]["role"] = "grenadier"
    player_count = get_team_count(team_view, "allies") + get_team_count(
        team_view, "axis"
    )
    mod = mod_with_config(
        AutoModSeedingUserConfig(
            enabled=True,
            disallowed_roles=DisallowedRoles(
                roles={Roles.tank_commander: "Tanks"},
                min_players=0,
                max_players=player_count + 1,
            ),
        )
    )

    punitions = mod.punitions_to_apply(team_view, "able", "allies", able, game_state)

    assert punitions == PunitionsToApply()


def test_vietnam_squadleader_uses_officer_role_rules(team_view):
    able = team_view["allies"]["squads"]["able"]
    able["players"] = [able["players"][0]]
    able["players"][0]["role"] = "squadleader"
    player_count = get_team_count(team_view, "allies") + get_team_count(
        team_view, "axis"
    )
    mod = mod_with_config(
        AutoModSeedingUserConfig(
            enabled=True,
            disallowed_roles=DisallowedRoles(
                roles={Roles.squad_lead: "Squad leaders"},
                min_players=0,
                max_players=player_count + 1,
            ),
        )
    )

    punitions = mod.punitions_to_apply(team_view, "able", "allies", able, game_state)

    assert ["WilliePeter"] == [player.name for player in punitions.warning]


def test_does_nothing_when_enough_players(team_view):
    config = AutoModSeedingUserConfig(
        enabled=True,
        disallowed_roles=DisallowedRoles(
            roles={
                Roles.tank_commander: "Tanks",
                Roles.crewman: "Tanks",
            },
            min_players=0,
            max_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            - 1,
        ),
        disallowed_weapons=DisallowedWeapons(
            weapons={
                "MP40": "MP40",
            },
            min_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            - 1,
            max_players=0,
        ),
        enforce_cap_fight=EnforceCapFight(min_players=0, max_players=0),
    )
    mod = mod_with_config(config)

    assert PunitionsToApply() == mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert PunitionsToApply() == mod.on_kill(kill_event_log)


def test_individual_rule_switches_disable_enforcement_without_losing_settings(
    team_view,
):
    player_count = get_team_count(team_view, "allies") + get_team_count(
        team_view, "axis"
    )
    config = AutoModSeedingUserConfig(
        enabled=True,
        disallowed_roles=DisallowedRoles(
            enabled=False,
            roles={Roles.tank_commander: "Tanks", Roles.crewman: "Tanks"},
            min_players=0,
            max_players=player_count + 1,
        ),
        disallowed_weapons=DisallowedWeapons(
            enabled=False,
            weapons={"MP40": "MP40"},
            min_players=0,
            max_players=player_count + 1,
        ),
        enforce_cap_fight=EnforceCapFight(
            enabled=False,
            min_players=0,
            max_players=player_count + 1,
            max_caps=game_state["allied_score"],
        ),
    )
    mod = mod_with_config(config)
    squad = team_view["allies"]["squads"]["able"]

    assert config.disallowed_roles.roles
    assert config.disallowed_weapons.weapons == {"MP40": "MP40"}
    assert config.enforce_cap_fight.max_caps == game_state["allied_score"]

    assert PunitionsToApply() == mod.punitions_to_apply(
        team_view, "able", "allies", squad, game_state
    )
    squad["players"][0]["offense"] += 1
    assert PunitionsToApply() == mod.punitions_to_apply(
        team_view, "able", "allies", squad, game_state
    )
    assert PunitionsToApply() == mod.on_kill(kill_event_log)


def test_individual_seeding_rules_are_enabled_by_default():
    config = AutoModSeedingUserConfig()

    assert config.disallowed_roles.enabled is True
    assert config.disallowed_weapons.enabled is True
    assert config.enforce_cap_fight.enabled is True


def test_does_nothing_when_not_enough_players(team_view):
    mod = mod_with_config(
        AutoModSeedingUserConfig(
            enabled=True,
            disallowed_roles=DisallowedRoles(
                roles={
                    Roles.tank_commander: "Tanks",
                    Roles.crewman: "Tanks",
                },
                min_players=get_team_count(team_view, "allies")
                + get_team_count(team_view, "axis")
                + 1,
                max_players=0,
            ),
            disallowed_weapons=DisallowedWeapons(
                weapons={"MP40": "MP40"},
                min_players=get_team_count(team_view, "allies")
                + get_team_count(team_view, "axis")
                + 1,
                max_players=0,
            ),
        )
    )

    assert PunitionsToApply() == mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert PunitionsToApply() == mod.on_kill(kill_event_log)


def test_cycles_warn_punish_kick_armor_players(team_view):
    config = AutoModSeedingUserConfig(
        enabled=True,
        number_of_warnings=1,
        warning_interval_seconds=1,
        number_of_punishments=1,
        punish_interval_seconds=1,
        warning_message="",
        punish_message="",
        kick_after_max_punish=True,
        kick_message="",
        kick_grace_period_seconds=1,
        disallowed_roles=DisallowedRoles(
            roles={Roles.tank_commander: "Tanks", Roles.crewman: "Tanks"},
            min_players=0,
            max_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            + 1,
        ),
    )

    mod = mod_with_config(config)

    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert expected_warned_players == punitions.warning
    assert [] == punitions.punish
    assert [] == punitions.kick
    time.sleep(config.warning_interval_seconds)

    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert [] == punitions.warning
    assert expected_warned_players == punitions.punish
    assert [] == punitions.kick
    time.sleep(config.kick_grace_period_seconds)

    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert [] == punitions.warning
    assert [] == punitions.punish
    assert expected_warned_players == punitions.kick


def test_cycles_warn_punish_kick_cap_fight_players(team_view):
    config = AutoModSeedingUserConfig(
        enabled=True,
        number_of_warnings=1,
        warning_interval_seconds=1,
        number_of_punishments=1,
        punish_interval_seconds=1,
        warning_message="",
        punish_message="",
        kick_after_max_punish=True,
        kick_message="",
        kick_grace_period_seconds=1,
        enforce_cap_fight=EnforceCapFight(
            min_players=0,
            max_caps=3,
            max_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            + 1,
        ),
    )

    mod = mod_with_config(config)
    mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )

    team_view["allies"]["squads"]["able"]["players"][0]["offense"] += 1
    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert [expected_warned_players[0]] == punitions.warning
    assert [] == punitions.punish
    assert [] == punitions.kick
    time.sleep(config.warning_interval_seconds)

    team_view["allies"]["squads"]["able"]["players"][0]["offense"] += 1
    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert [] == punitions.warning
    assert [expected_warned_players[0]] == punitions.punish
    assert [] == punitions.kick
    time.sleep(config.kick_grace_period_seconds)

    team_view["allies"]["squads"]["able"]["players"][0]["offense"] += 1
    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert [] == punitions.warning
    assert [] == punitions.punish
    assert [expected_warned_players[0]] == punitions.kick


def position_cap_fight_mod(team_view):
    player_count = get_team_count(team_view, "allies") + get_team_count(
        team_view, "axis"
    )
    return mod_with_config(
        AutoModSeedingUserConfig(
            enabled=True,
            number_of_warnings=1,
            warning_message="",
            disallowed_roles=DisallowedRoles(enabled=False),
            disallowed_weapons=DisallowedWeapons(enabled=False),
            enforce_cap_fight=EnforceCapFight(
                min_players=0,
                max_players=player_count + 1,
                max_caps=3,
            ),
        )
    )


@pytest.mark.parametrize("squad_name", [None, "", "unassigned", " Unassigned "])
@pytest.mark.parametrize("team", ["allies", "axis"])
@pytest.mark.parametrize("signal", ["position", "offense", "role"])
def test_no_seeding_actions_before_joining_squad(team_view, squad_name, team, signal):
    squad = team_view[team]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    player["unit_name"] = squad_name
    mod = position_cap_fight_mod(team_view)
    if signal == "role":
        mod.config.disallowed_roles = DisallowedRoles(
            roles={Roles.tank_commander: "Tanks"}, max_players=100
        )
        player["role"] = "tankcommander"
    snapshot = {**game_state, "allied_score": 3, "axis_score": 3}
    # Unassigned HLL1 players were reported at the OTHER team's Carentan HQ.
    # A changing join sample or delayed offense counter is not a violation.
    x = 97_986 if team == "allies" else -96_470
    for offset in (0, 10, 20):
        if signal == "position":
            player["world_position"] = {"x": x + offset, "y": 0, "z": 450}
        player["offense"] += 10
        result = mod.punitions_to_apply(team_view, squad_name, team, squad, snapshot)
        assert not result.warning and not result.punish and not result.kick
    assert not state  # No warning/escalation history from the join screen.


@pytest.mark.parametrize("team", ["allies", "axis"])
@pytest.mark.parametrize(
    "current_map", [None, {}, {"map": {}}, game_state["current_map"]]
)
def test_unspawned_player_never_uses_offense_fallback(team_view, team, current_map):
    squad = team_view[team]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    player["world_position"] = {"x": 0, "y": 0, "z": 0}
    mod = position_cap_fight_mod(team_view)
    snapshot = {
        **game_state,
        "allied_score": 3,
        "axis_score": 3,
        "current_map": current_map,
    }
    for _ in range(3):
        player["offense"] += 10
        result = mod.punitions_to_apply(team_view, "able", team, squad, snapshot)
        assert not result.warning and not result.punish and not result.kick


@pytest.mark.parametrize("team", ["allies", "axis"])
def test_carentan_join_hq_and_boundary_are_distinct(team_view, team):
    squad = team_view[team]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    mod = position_cap_fight_mod(team_view)
    sign = 1 if team == "allies" else -1
    snapshot = {**game_state, "allied_score": 3, "axis_score": 3}
    player["unit_name"] = "unassigned"
    # Rounded real HLL1 join-screen positions, 2026-09-15, Carentan Night.
    for x in ((97_980, 97_987) if team == "allies" else (-96_460, -96_470)):
        player["world_position"] = {"x": x, "y": 0, "z": 450}
        assert not mod.punitions_to_apply(
            team_view, "unassigned", team, squad, snapshot
        )
    player["unit_name"] = "able"
    # First sample after joining can still be a bogus HQ. Wait for movement.
    assert not mod.punitions_to_apply(team_view, "able", team, squad, snapshot)
    for x in (-sign * 96_000, -sign * 50_000, 0):
        player["world_position"]["x"] = x
        assert not mod.punitions_to_apply(team_view, "able", team, squad, snapshot)
    player["world_position"]["x"] = sign * 20_161
    result = mod.punitions_to_apply(team_view, "able", team, squad, snapshot)
    assert [p.player_id for p in result.warning] == [player["player_id"]]
    assert not result.punish and not result.kick


@pytest.mark.parametrize("map_id,sign", [("carentan", 1), ("WDEV_A", -1)])
def test_commander_without_regular_squad_is_still_checked(team_view, map_id, sign):
    player = team_view["allies"]["commander"]
    squad = {"players": [player]}
    mod = position_cap_fight_mod(team_view)
    snapshot = {**game_state, "current_map": {"map": {"id": map_id}}}
    player["world_position"] = {"x": 0, "y": 0, "z": 0}
    assert not mod.punitions_to_apply(team_view, "Commander", "allies", squad, snapshot)
    player["world_position"] = {"x": sign * 30_000, "y": 0, "z": 100}
    result = mod.punitions_to_apply(team_view, "Commander", "allies", squad, snapshot)
    assert [p.player_id for p in result.warning] == [player["player_id"]]


def test_position_detection_warns_before_offense_score_changes(team_view):
    squad = team_view["allies"]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    player["world_position"] = {"x": 0, "y": 0, "z": 1}
    mod = position_cap_fight_mod(team_view)

    assert PunitionsToApply() == mod.punitions_to_apply(
        team_view, "able", "allies", squad, game_state
    )

    player["world_position"] = {"x": 20_160, "y": 0, "z": 1}
    punitions = mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)

    assert [expected_warned_players[0]] == punitions.warning


@pytest.mark.parametrize(
    "map_id", ["stmariedumont", "purpleheartlane", "kursk", "kharkov", "elsenbornridge"]
)
@pytest.mark.parametrize("team", ["allies", "axis"])
@pytest.mark.parametrize("score", [2, 3])
def test_corrected_map_allows_own_spawn_and_still_punishes_enemy_excursion(
    team_view, map_id, team, score
):
    squad = team_view[team]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    mod = position_cap_fight_mod(team_view)
    mod.config.kick_after_max_punish = False
    mod.config.number_of_warnings = 0
    # Stale offense counters must not override a valid own-side position.
    snapshot = {
        **game_state,
        "allied_score": score,
        "axis_score": 5 - score,
        "current_map": {"map": {"id": map_id}},
    }
    sign = 1 if team == "allies" else -1
    for y in (0, -sign * 96_000, -sign * 90_000, -sign * 50_000, 0):
        player["world_position"] = {"x": 0, "y": y, "z": 0 if y == 0 else 100}
        player["offense"] += 10
        result = mod.punitions_to_apply(team_view, "able", team, squad, snapshot)
        assert not result.warning and not result.punish and not result.kick
    player["world_position"] = {"x": 0, "y": sign * 25_000, "z": 100}
    result = mod.punitions_to_apply(team_view, "able", team, squad, snapshot)
    assert [p.player_id for p in result.punish] == [player["player_id"]]
    assert not result.warning and not result.kick
    player["world_position"]["y"] = -sign * 90_000
    assert not mod.punitions_to_apply(team_view, "able", team, squad, snapshot)


@pytest.mark.parametrize("team", ["allies", "axis"])
@pytest.mark.parametrize(
    "map_id,allies_x,axis_x",
    [("carentan", 20_160, -20_161), ("WDEV_A", -19_841, 19_840)],
)
@pytest.mark.parametrize("score", [2, 3])
def test_position_boundary_applies_to_both_teams_regardless_of_score(
    team_view, team, map_id, allies_x, axis_x, score
):
    squad_name = "able"
    squad = team_view[team]["squads"][squad_name]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    player["world_position"] = {"x": 0, "y": 0, "z": 1}
    score_key = "allied_score" if team == "allies" else "axis_score"
    other_key = "axis_score" if team == "allies" else "allied_score"
    snapshot = {**game_state, score_key: score, other_key: 5 - score}
    snapshot["current_map"] = {"map": {"id": map_id}}
    mod = position_cap_fight_mod(team_view)
    mod.config.number_of_warnings = 2
    mod.config.warning_interval_seconds = 60

    assert not mod.punitions_to_apply(team_view, squad_name, team, squad, snapshot)
    player["world_position"]["x"] = allies_x if team == "allies" else axis_x
    first = mod.punitions_to_apply(team_view, squad_name, team, squad, snapshot)
    assert [player["player_id"]] == [p.player_id for p in first.warning]
    assert not first.punish

    # Capturing/losing the middle must not restart the warning grace period.
    snapshot.update({score_key: 5 - score, other_key: score})
    waiting = mod.punitions_to_apply(team_view, squad_name, team, squad, snapshot)
    assert not waiting.warning and not waiting.punish
    watch_status = state[team + squad_name]
    assert len(watch_status.warned.get(player["name"], [])) == 1
    watch_status.warned[player["name"]][-1] -= timedelta(seconds=61)
    second = mod.punitions_to_apply(team_view, squad_name, team, squad, snapshot)
    assert [player["player_id"]] == [p.player_id for p in second.warning]
    assert not second.punish
    watch_status.warned[player["name"]][-1] -= timedelta(seconds=61)
    punished = mod.punitions_to_apply(team_view, squad_name, team, squad, snapshot)
    assert [player["player_id"]] == [p.player_id for p in punished.punish]

    player["world_position"]["x"] = 0
    assert not mod.punitions_to_apply(team_view, squad_name, team, squad, snapshot)
    assert player["name"] not in watch_status.warned
    assert player["name"] not in watch_status.punished


@pytest.mark.parametrize("team,squad_name", [("allies", "able"), ("axis", "able")])
@pytest.mark.parametrize("score", [2, 3])
@pytest.mark.parametrize("unknown_map", [False, True])
def test_offense_fallback_keeps_score_guard_for_both_teams(
    team_view, team, squad_name, score, unknown_map
):
    squad = team_view[team]["squads"][squad_name]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    score_key = "allied_score" if team == "allies" else "axis_score"
    snapshot = {**game_state, score_key: score}
    mod = position_cap_fight_mod(team_view)
    if unknown_map:
        snapshot["current_map"] = {"map": {"id": "unknown-map"}}
        player["world_position"] = {"x": 0, "y": 0, "z": 0}
    mod.punitions_to_apply(team_view, squad_name, team, squad, snapshot)
    if unknown_map:
        player["world_position"] = {"x": 50_000, "y": 0, "z": 1}
    player["offense"] += 1
    result = mod.punitions_to_apply(team_view, squad_name, team, squad, snapshot)
    assert len(result.warning) == (1 if score >= 3 else 0)
    assert not result.punish


@pytest.mark.parametrize("guard", ["disabled", "min_players", "max_players", "mode"])
@pytest.mark.parametrize(
    "map_id,outside_x", [("carentan", -20_161), ("WDEV_A", 19_840)]
)
def test_position_detection_still_respects_seeding_guards(
    team_view, guard, map_id, outside_x
):
    squad = team_view["axis"]["squads"]["able"]
    player = squad["players"][0]
    player["world_position"] = {"x": 0, "y": 0, "z": 0}
    mod = position_cap_fight_mod(team_view)
    snapshot = {**game_state, "axis_score": 2, "current_map": {"map": {"id": map_id}}}
    mod.punitions_to_apply(team_view, "able", "axis", squad, snapshot)
    if guard == "disabled":
        mod.config.enforce_cap_fight.enabled = False
    elif guard == "min_players":
        mod.config.enforce_cap_fight.min_players = 99
    elif guard == "max_players":
        mod.config.enforce_cap_fight.max_players = 0
    else:
        snapshot["game_mode"] = GameMode.OFFENSIVE
    player["world_position"]["x"] = outside_x
    player["world_position"]["z"] = 1
    player["offense"] += 100
    result = mod.punitions_to_apply(team_view, "able", "axis", squad, snapshot)
    assert not result.warning and not result.punish and not result.kick


def test_position_detection_ignores_offense_increase_inside_boundary(team_view):
    squad = team_view["allies"]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    player["world_position"] = {"x": 0, "y": 0, "z": 1}
    mod = position_cap_fight_mod(team_view)
    mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)

    player["world_position"] = {"x": 100, "y": 0, "z": 1}
    player["offense"] += 1

    assert PunitionsToApply() == mod.punitions_to_apply(
        team_view, "able", "allies", squad, game_state
    )


def test_position_detection_filters_random_initial_hq_sample(team_view):
    squad = team_view["allies"]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    player["world_position"] = {"x": 50_000, "y": 0, "z": 1}
    mod = position_cap_fight_mod(team_view)

    assert PunitionsToApply() == mod.punitions_to_apply(
        team_view, "able", "allies", squad, game_state
    )
    assert PunitionsToApply() == mod.punitions_to_apply(
        team_view, "able", "allies", squad, game_state
    )

    player["world_position"] = {"x": 50_001, "y": 0, "z": 1}
    punitions = mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)

    assert [expected_warned_players[0]] == punitions.warning


def test_position_detection_checks_first_spawn_after_zero_sample(team_view):
    squad = team_view["allies"]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    player["world_position"] = {"x": 0, "y": 0, "z": 0}
    mod = position_cap_fight_mod(team_view)

    assert PunitionsToApply() == mod.punitions_to_apply(
        team_view, "able", "allies", squad, game_state
    )

    player["world_position"] = {"x": 20_160, "y": 0, "z": 1}
    punitions = mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)

    assert [expected_warned_players[0]] == punitions.warning


@pytest.mark.parametrize("reconnect_signal", ["profile", "hook", "both"])
@pytest.mark.parametrize("group", ["able", "Commander"])
@pytest.mark.parametrize("team", ["allies", "axis"])
@pytest.mark.parametrize("map_id", ["stmariedumont", "WDEV_A"])
def test_reconnect_rearms_spawn_guard_and_still_enforces_boundary(
    team_view, reconnect_signal, group, team, map_id
):
    player = team_view[team]["squads"]["able"]["players"][0]
    player["profile"] = {"sessions_count": 5, "flags": []}
    player["role"] = "armycommander" if group == "Commander" else "officer"
    squad = {"players": [player]}
    mod = position_cap_fight_mod(team_view)
    mod.config.announcement_enabled = False
    snapshot = {**game_state, "current_map": {"map": {"id": map_id}}}
    axis = "y" if map_id == "stmariedumont" else "x"
    sign = (1 if team == "allies" else -1) * (1 if axis == "y" else -1)

    def sample(coordinate):
        player["world_position"] = {"x": 0, "y": 0, "z": 100}
        player["world_position"][axis] = sign * coordinate
        return mod.punitions_to_apply(team_view, group, team, squad, snapshot)

    assert not sample(-96_000)
    assert not sample(-95_000)  # Original connection has confirmed movement.
    if reconnect_signal in ("profile", "both"):
        player["profile"]["sessions_count"] += 1
    if reconnect_signal in ("hook", "both"):
        assert not mod.on_connected(player["name"], player["player_id"])
    # Rejoin in the same squad inside its 120-second watch lifetime: the game
    # initially reports an enemy HQ, even with an assigned commander role.
    assert not sample(94_000)
    assert not sample(94_000)
    assert not sample(-97_000)  # Actual spawn in own HQ.
    assert not sample(-50_000)
    result = sample(30_000)
    assert [p.player_id for p in result.warning] == [player["player_id"]]
    assert not result.punish and not result.kick


def test_hll1_recorded_reconnect_positions_do_not_warn(team_view):
    player = team_view["allies"]["commander"]
    player["profile"] = {"sessions_count": 10, "flags": []}
    mod = position_cap_fight_mod(team_view)
    snapshot = {**game_state, "current_map": {"map": {"id": "stmariedumont"}}}
    # HLL1, 2026-09-19 11:24–11:25 UTC. New connection initially reports
    # the enemy HQ, then the real Allied spawn. No actual boundary crossing.
    for count, position in [
        (10, (39488.68359375, -96258.2265625, 169.6443328857422)),
        (10, (40091.0078125, -96382.34375, 155.8644256591797)),
        (11, (-48477.5, 93779.0390625, 167.74635314941406)),
        (11, (-48477.5, 93779.0390625, 167.74635314941406)),
        (11, (2094.5400390625, -97370.3515625, 312.76263427734375)),
        (11, (237.60140991210938, -96763.375, 417.2548828125)),
    ]:
        player["profile"]["sessions_count"] = count
        player["world_position"] = dict(zip(("x", "y", "z"), position))
        assert not mod.punitions_to_apply(
            team_view, "Commander", "allies", {"players": [player]}, snapshot
        )


def test_connection_marker_expiry_does_not_reset_confirmed_movement(team_view):
    mod = position_cap_fight_mod(team_view)
    player = team_view["allies"]["commander"]
    player["profile"] = {"sessions_count": 2, "flags": []}
    key = connection_key(player["player_id"])
    redis_store[key] = b"connection-a"
    watch = WatchStatus()
    player["world_position"] = {"x": 0, "y": 0, "z": 1}
    assert mod._position_cap_violation(watch, player, "allies", game_state) is False
    player["world_position"]["x"] = 100
    assert mod._position_cap_violation(watch, player, "allies", game_state) is False
    del redis_store[key]
    player["world_position"]["x"] = 30_000
    assert mod._position_cap_violation(watch, player, "allies", game_state) is True


@pytest.mark.parametrize("legacy_pickle", [False, True])
def test_reconnect_clears_only_target_players_old_progress(team_view, legacy_pickle):
    mod = position_cap_fight_mod(team_view)
    player = team_view["allies"]["commander"]
    player["profile"] = {"sessions_count": 7, "flags": []}
    pid, name = player["player_id"], player["name"]
    watch = WatchStatus(
        world_position_map_id="carentan",
        initial_world_positions={pid: None, "other": None},
        combat_area_outside_player_ids={pid, "other"},
        position_tracking_context={pid: (6, None)},
        offensive_points={name: 500, "other": 500},
        warned={name: [datetime.now()], "other": [datetime.now()]},
        punished={name: [datetime.now()], "other": [datetime.now()]},
        noted={name: [datetime.now()], "other": [datetime.now()]},
    )
    if legacy_pickle:
        del watch.position_tracking_context
    player["world_position"] = {"x": 94_000, "y": 0, "z": 1}
    assert mod._position_cap_violation(watch, player, "allies", game_state) is False
    assert watch.initial_world_positions[pid] == (94_000, 0, 1)
    assert watch.combat_area_outside_player_ids == {"other"}
    for entries in (watch.noted, watch.warned, watch.punished, watch.offensive_points):
        assert name not in entries and "other" in entries


def test_reconnect_without_position_does_not_use_old_offense_points(team_view):
    mod = position_cap_fight_mod(team_view)
    player = team_view["allies"]["commander"]
    player["profile"] = {"sessions_count": 2, "flags": []}
    player["world_position"] = None
    watch = WatchStatus(
        position_tracking_context={player["player_id"]: (1, None)},
        offensive_points={player["name"]: 100},
    )
    assert mod._position_cap_violation(watch, player, "allies", game_state) is False
    assert player["name"] not in watch.offensive_points


def position_cap_fight_skip_warning_mod(team_view, *, punishments=2):
    player_count = get_team_count(team_view, "allies") + get_team_count(
        team_view, "axis"
    )
    return mod_with_config(
        AutoModSeedingUserConfig(
            enabled=True,
            number_of_warnings=2,
            warning_interval_seconds=60,
            number_of_punishments=punishments,
            punish_interval_seconds=60,
            kick_after_max_punish=False,
            disallowed_roles=DisallowedRoles(enabled=False),
            disallowed_weapons=DisallowedWeapons(enabled=False),
            enforce_cap_fight=EnforceCapFight(
                skip_warning=True,
                min_players=0,
                max_players=player_count + 1,
                max_caps=3,
            ),
        )
    )


def test_position_skip_warning_state_stays_bounded_while_outside(team_view):
    squad = team_view["allies"]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    player["world_position"] = {"x": 0, "y": 0, "z": 1}
    mod = position_cap_fight_skip_warning_mod(team_view)
    mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)

    player["world_position"] = {"x": 20_160, "y": 0, "z": 1}
    mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)
    for _ in range(5):
        mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)

    watch_status = state["alliesable"]
    assert len(watch_status.warned[player["name"]]) == 2
    assert len(watch_status.punished[player["name"]]) == 1


def test_position_progress_resets_after_returning_inside(team_view):
    squad = team_view["allies"]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    player["world_position"] = {"x": 0, "y": 0, "z": 1}
    mod = position_cap_fight_skip_warning_mod(team_view, punishments=1)
    mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)

    player["world_position"] = {"x": 20_160, "y": 0, "z": 1}
    first = mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)
    assert [player["player_id"]] == [target.player_id for target in first.punish]

    player["world_position"] = {"x": 100, "y": 0, "z": 1}
    assert PunitionsToApply() == mod.punitions_to_apply(
        team_view, "able", "allies", squad, game_state
    )
    watch_status = state["alliesable"]
    assert player["name"] not in watch_status.warned
    assert player["name"] not in watch_status.punished
    assert player["player_id"] not in watch_status.combat_area_outside_player_ids

    player["world_position"] = {"x": 20_160, "y": 0, "z": 1}
    second = mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)
    assert [player["player_id"]] == [target.player_id for target in second.punish]


def test_position_repeats_punishment_when_kick_is_disabled(team_view):
    squad = team_view["allies"]["squads"]["able"]
    squad["players"] = [squad["players"][0]]
    player = squad["players"][0]
    player["world_position"] = {"x": 0, "y": 0, "z": 1}
    mod = position_cap_fight_skip_warning_mod(team_view, punishments=2)
    mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)

    player["world_position"] = {"x": 20_160, "y": 0, "z": 1}
    first = mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)
    assert [player["player_id"]] == [target.player_id for target in first.punish]

    watch_status = state["alliesable"]
    watch_status.punished[player["name"]][-1] -= timedelta(seconds=61)
    second = mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)
    assert [player["player_id"]] == [target.player_id for target in second.punish]

    watch_status.punished[player["name"]][-1] -= timedelta(seconds=61)
    repeated = mod.punitions_to_apply(team_view, "able", "allies", squad, game_state)
    assert [player["player_id"]] == [target.player_id for target in repeated.punish]
    assert len(watch_status.punished[player["name"]]) == 2


def test_punishes_commander_cap_fight(team_view):
    config = AutoModSeedingUserConfig(
        enabled=True,
        number_of_warnings=1,
        warning_interval_seconds=1,
        number_of_punishments=1,
        punish_interval_seconds=1,
        warning_message="",
        punish_message="",
        kick_after_max_punish=True,
        kick_message="",
        kick_grace_period_seconds=1,
        enforce_cap_fight=EnforceCapFight(
            min_players=0,
            max_caps=3,
            max_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            + 1,
        ),
    )

    mod = mod_with_config(config)
    mod.punitions_to_apply(
        team_view,
        "Commander",
        "allies",
        {"players": [team_view["allies"]["commander"]]},
        game_state,
    )

    team_view["allies"]["commander"]["offense"] += 1
    punitions = mod.punitions_to_apply(
        team_view,
        "Commander",
        "allies",
        {"players": [team_view["allies"]["commander"]]},
        game_state,
    )

    assert [
        PunishPlayer(
            player_id="76561198206929556",
            name="FamousCommander",
            squad="Commander",
            team="allies",
            role="armycommander",
            lvl=123,
            details=PunishDetails(
                author="AutoMod_SeedingRules",
                message="",
                discord_audit_url=None,
                dry_run=False,
            ),
        )
    ] == punitions.warning
    assert [] == punitions.punish
    assert [] == punitions.kick


def test_skips_warning_when_disabled(team_view):
    config = AutoModSeedingUserConfig(
        enabled=True,
        number_of_warnings=1,
        warning_interval_seconds=1,
        number_of_punishments=1,
        punish_interval_seconds=1,
        warning_message="",
        punish_message="",
        kick_after_max_punish=True,
        kick_message="",
        kick_grace_period_seconds=1,
        enforce_cap_fight=EnforceCapFight(
            skip_warning=True,
            min_players=0,
            max_caps=3,
            max_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            + 1,
        ),
    )

    mod = mod_with_config(config)
    mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )

    team_view["allies"]["squads"]["able"]["players"][0]["offense"] += 1
    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert [] == punitions.warning
    assert [expected_warned_players[0]] == punitions.punish
    assert [] == punitions.kick


def test_cap_fight_does_not_enforce_below_min_players(team_view):
    min_players = (
        get_team_count(team_view, "allies") + get_team_count(team_view, "axis") + 1
    )
    max_players = (
        get_team_count(team_view, "allies") + get_team_count(team_view, "axis") + 2
    )
    config = AutoModSeedingUserConfig(
        enabled=True,
        number_of_warnings=1,
        warning_interval_seconds=1,
        number_of_punishments=1,
        punish_interval_seconds=1,
        warning_message="",
        punish_message="",
        kick_after_max_punish=True,
        kick_message="",
        kick_grace_period_seconds=1,
        enforce_cap_fight=EnforceCapFight(
            min_players=min_players,
            max_players=max_players,
            max_caps=game_state["allied_score"],
        ),
    )

    mod = mod_with_config(config)
    mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )

    team_view["allies"]["squads"]["able"]["players"][0]["offense"] += 1

    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert [] == punitions.warning
    assert [] == punitions.punish
    assert [] == punitions.kick


def test_does_nothing_when_cap_not_reached(team_view):
    config = AutoModSeedingUserConfig(
        enabled=True,
        number_of_warnings=1,
        warning_interval_seconds=1,
        number_of_punishments=1,
        punish_interval_seconds=1,
        warning_message="",
        punish_message="",
        kick_after_max_punish=True,
        kick_message="",
        kick_grace_period_seconds=1,
        enforce_cap_fight=EnforceCapFight(
            max_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            + 1,
            max_caps=game_state["allied_score"] + 1,
        ),
    )

    mod = mod_with_config(config)
    mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )

    team_view["allies"]["squads"]["able"]["players"][0]["offense"] += 1
    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert [] == punitions.warning
    assert [] == punitions.punish
    assert [] == punitions.kick


def test_stops_when_players_reached(team_view):
    config = AutoModSeedingUserConfig(
        enabled=True,
        number_of_warnings=1,
        warning_interval_seconds=1,
        number_of_punishments=1,
        punish_interval_seconds=1,
        warning_message="",
        punish_message="",
        kick_after_max_punish=True,
        kick_message="",
        kick_grace_period_seconds=1,
        enforce_cap_fight=EnforceCapFight(
            max_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            - 1,
            max_caps=3,
        ),
    )

    mod = mod_with_config(config)
    mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )

    team_view["allies"]["squads"]["able"]["players"][0]["offense"] += 1
    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert [] == punitions.warning
    assert [] == punitions.punish
    assert [] == punitions.kick


def test_stops_when_no_violations_anymore(team_view):
    config = AutoModSeedingUserConfig(
        enabled=True,
        number_of_warnings=1,
        warning_interval_seconds=1,
        number_of_punishments=1,
        punish_interval_seconds=1,
        warning_message="",
        punish_message="",
        kick_after_max_punish=False,
        kick_message="",
        kick_grace_period_seconds=1,
        disallowed_roles=DisallowedRoles(
            min_players=0,
            max_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            + 1,
            roles={Roles.tank_commander: "Tanks", Roles.crewman: "Tanks"},
        ),
    )

    mod = mod_with_config(config)

    punitions = mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )
    assert expected_warned_players == punitions.warning
    assert [] == punitions.punish
    assert [] == punitions.kick
    time.sleep(config.warning_interval_seconds)

    able = team_view["allies"]["squads"]["able"]
    for p in able["players"]:
        p["role"] = "rifleman"
    punitions = mod.punitions_to_apply(team_view, "able", "allies", able, game_state)
    assert [] == punitions.warning
    assert [] == punitions.punish
    assert [] == punitions.kick


def test_disallowed_weapons_does_not_enforce_below_min_players(team_view):
    min_players = (
        get_team_count(team_view, "allies") + get_team_count(team_view, "axis") + 1
    )
    max_players = (
        get_team_count(team_view, "allies") + get_team_count(team_view, "axis") + 2
    )

    mod = mod_with_config(
        AutoModSeedingUserConfig(
            enabled=True,
            disallowed_weapons=DisallowedWeapons(
                weapons={"MP40": "MP40"},
                min_players=min_players,
                max_players=max_players,
            ),
        )
    )
    mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )

    punitions = mod.on_kill(kill_event_log)
    assert [] == punitions.warning
    assert [] == punitions.punish
    assert [] == punitions.kick


def test_punishes_when_weapon_disallowed(team_view):
    mod = mod_with_config(
        AutoModSeedingUserConfig(
            enabled=True,
            disallowed_weapons=DisallowedWeapons(
                weapons={"MP40": "MP40"},
                min_players=get_team_count(team_view, "allies")
                + get_team_count(team_view, "axis")
                - 1,
                max_players=get_team_count(team_view, "allies")
                + get_team_count(team_view, "axis")
                + 1,
            ),
        )
    )
    mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )

    punitions = mod.on_kill(kill_event_log)
    assert 1 == len(punitions.punish)


def test_does_not_punish_when_weapon_allowed(team_view):
    mod = mod_with_config(
        AutoModSeedingUserConfig(
            enabled=True,
            disallowed_weapons=DisallowedWeapons(
                weapons={"MK2_Grenade": "Grenade"},
                min_players=get_team_count(team_view, "allies")
                + get_team_count(team_view, "axis")
                - 1,
                max_players=get_team_count(team_view, "allies")
                + get_team_count(team_view, "axis")
                + 1,
            ),
        )
    )
    mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )

    punitions = mod.on_kill(kill_event_log)
    assert 0 == len(punitions.punish)


def test_announces_on_connect(team_view):
    mod = mod_with_config(
        AutoModSeedingUserConfig(
            enabled=True,
            announcement_enabled=True,
            announcement_message="",
            disallowed_weapons=DisallowedWeapons(
                weapons={"MK2_Grenade": "Grenade"},
            ),
            disallowed_roles=DisallowedRoles(
                roles={Roles.tank_commander: "Tanks", Roles.crewman: "Tanks"}
            ),
        )
    )

    punitions = mod.on_connected("A_NAME", "A_STEAM_ID")
    assert 1 == len(punitions.warning)


def test_does_not_announces_when_all_disabled(team_view):
    config = AutoModSeedingUserConfig(
        enabled=True,
        announcement_enabled=True,
        announcement_message="",
        number_of_warnings=0,
        number_of_punishments=0,
        disallowed_weapons=DisallowedWeapons(
            weapons={"MK2_Grenade": "Grenade"},
            min_players=0,
            max_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            - 1,
        ),
        disallowed_roles=DisallowedRoles(
            roles={Roles.tank_commander: "Tanks", Roles.crewman: "Tanks"},
            min_players=0,
            max_players=get_team_count(team_view, "allies")
            + get_team_count(team_view, "axis")
            - 1,
        ),
        enforce_cap_fight=EnforceCapFight(min_players=0, max_players=0),
    )
    mod = mod_with_config(config)
    mod.punitions_to_apply(
        team_view, "able", "allies", team_view["allies"]["squads"]["able"], game_state
    )

    punitions = mod.on_connected("A_NAME", "A_STEAM_ID")
    assert 0 == len(punitions.warning)


def test_non_existing_roles_raises():
    with pytest.raises(ValueError):
        AutoModSeedingUserConfig(
            disallowed_roles=DisallowedRoles(roles={Roles("does_not_exist"): ""})
        )
