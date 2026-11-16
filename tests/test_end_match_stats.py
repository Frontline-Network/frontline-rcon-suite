from unittest.mock import MagicMock

import pytest

from rcon import end_match_stats as stats
from rcon.types import GameEnum


@pytest.fixture
def setup_match(monkeypatch):
    monkeypatch.setenv("FRONTLINE_END_MATCH_STATS_SERVERS", "1")
    monkeypatch.setattr(stats, "get_server_number", lambda: 1)
    monkeypatch.setattr(stats.EndMatchStatsUserConfig, "load_from_db", classmethod(lambda cls, **kwargs: cls()))
    monkeypatch.setattr(stats.time, "time", lambda: 1000)
    monkeypatch.setattr(stats, "MapsHistory", lambda: [{"start": 100, "name": "foy", "guessed": False}])
    monkeypatch.setattr(stats, "layer_matches_match_log", lambda layer, raw: "Foy" in raw)
    redis = MagicMock()
    redis.set.return_value = True
    monkeypatch.setattr(stats, "get_redis_client", lambda: redis)
    rcon = MagicMock()
    rcon.get_detailed_players.return_value = {"fail_count": 0, "players": {}}
    rcon.get_team_view.return_value = {"fail_count": 0, "allies": {"squads": {
        "Able": {"type": "infantry", "players": [
            {"name": "Alice", "kills": 10, "defense": 2, "support": 0},
            {"name": "Bob", "kills": 5, "defense": 9, "support": 12},
        ]},
    }}}
    rcon.message_all_players.return_value = True
    return rcon, redis, {"timestamp_ms": 1000000, "raw": "MATCH ENDED `Foy WARFARE` ALLIED (3 - 2) AXIS"}


def test_sends_once_to_all_without_chat(setup_match):
    rcon, redis, log = setup_match
    stats.send_end_match_stats(rcon, log)
    rcon.message_all_players.assert_called_once_with(
        "MATCH TOP PLAYERS\nKills: Alice (10)\nDefense: Bob (9)\nSupport: Bob (12)"
    )
    redis.set.assert_called_once_with("end-match-stats:1:100", "1", nx=True, ex=86400)


def test_duplicate_or_disabled_does_not_send(setup_match, monkeypatch):
    rcon, redis, log = setup_match
    redis.set.return_value = False
    stats.send_end_match_stats(rcon, log)
    monkeypatch.setenv("FRONTLINE_END_MATCH_STATS_SERVERS", "2")
    stats.send_end_match_stats(rcon, log)
    rcon.message_all_players.assert_not_called()


@pytest.mark.parametrize("history,match_start,expected", [
    ([{"start": 100, "guessed": False}], 100, True),
    ([{"start": 101, "guessed": False}], 100, False),
    ([{"start": 100, "guessed": True}], 100, False),
    ([], 100, False),
    ([{"start": 100, "guessed": False}], None, False),
])
def test_delayed_squad_ranking_requires_same_known_match(monkeypatch, history, match_start, expected):
    from rcon import rcon as rcon_module
    sender = MagicMock()
    monkeypatch.setattr(stats.time, "time", lambda: 1000)
    monkeypatch.setattr(stats, "MapsHistory", lambda: history)
    monkeypatch.setattr(stats.EndMatchStatsUserConfig, "load_from_db", classmethod(
        lambda cls, **kwargs: cls(enabled=True, include_squads=True)))
    monkeypatch.setattr(rcon_module, "get_rcon", lambda: sender)
    stats.send_delayed_squad_message("Squad ranking", 990, match_start)
    assert sender.message_all_players.call_count == int(expected)


def test_delayed_squad_job_records_match_identity(setup_match, monkeypatch):
    rcon, redis, log = setup_match
    rcon.get_team_view.return_value["allies"]["squads"]["Able"]["kills"] = 15
    monkeypatch.setattr(stats.EndMatchStatsUserConfig, "load_from_db", classmethod(
        lambda cls, **kwargs: cls(enabled=True, include_players=True, include_squads=True)))
    schedule = MagicMock()
    monkeypatch.setattr(stats, "schedule_squad_message", schedule)
    stats.send_end_match_stats(rcon, log)
    assert schedule.call_count == 1
    assert schedule.call_args.args[1:] == (1000, 15, 100)


@pytest.mark.parametrize("case", ["old", "wrong_map", "incomplete", "new_match"])
def test_unsafe_snapshot_is_not_sent(setup_match, monkeypatch, case):
    rcon, redis, log = setup_match
    if case == "old":
        log["timestamp_ms"] = 900000
    elif case == "wrong_map":
        log["raw"] = "Utah Beach"
    elif case == "incomplete":
        rcon.get_team_view.return_value["fail_count"] = 1
    else:
        histories = iter([[{"start": 100, "name": "foy"}], [{"start": 999}]])
        monkeypatch.setattr(stats, "MapsHistory", lambda: next(histories))
    stats.send_end_match_stats(rcon, log)
    rcon.message_all_players.assert_not_called()
    redis.set.assert_not_called()


def test_empty_or_zero_values_are_omitted():
    assert stats.format_stats([{"name": "Alice", "kills": 0}]) is None


def test_vietnam_squad_types_and_members_are_included_when_selected():
    config = stats.EndMatchStatsUserConfig(include_players=True, include_squads=True)
    assert {"mortar", "helicopter"}.issubset(config.unit_types)
    teams = {"allies": {"squads": {
        "Mortar": {"type": "mortar", "kills": 5, "players": [{"name": "Mortar player", "kills": 5}]},
        "Air": {"type": "helicopter", "kills": 8, "players": [{"name": "Pilot", "kills": 8}]},
    }}}
    players, squads = stats.extract_team_view(teams, config, game=GameEnum.HLL_VIETNAM)
    assert {p["name"] for p in players} == {"Mortar player", "Pilot"}
    assert {s["name"] for s in squads} == {"Mortar (allies)", "Air (allies)"}
    player_message, squad_message = stats.format_sections(players, config, squads)
    assert "Pilot (8)" in player_message and "Air (allies) (8)" in squad_message


def test_existing_explicit_unit_selection_remains_unchanged():
    old = ["commander", "infantry", "armor", "artillery", "recon"]
    assert stats.EndMatchStatsUserConfig.model_validate({"unit_types": old}).unit_types == old
    assert stats.EndMatchStatsUserConfig(unit_types=["mortar", "helicopter"]).unit_types == ["mortar", "helicopter"]


def test_squadless_players_count_individually_without_creating_a_squad():
    config = stats.EndMatchStatsUserConfig(include_players=True, include_squads=True)
    player = {"player_id": "p1", "name": "Solo", "kills": 25}
    teams = {"allies": {"squads": {None: {"type": "infantry", "players": [player]}}}}
    players, squads = stats.extract_team_view(teams, config)
    assert players == [player]
    assert squads == []
    assert "Solo (25)" in stats.format_sections(players, config, squads)[0]


def test_squadless_players_hidden_by_commander_are_recovered_once():
    commander = {"player_id": "c1", "name": "Commander", "role": "Army Commander", "unit_name": None, "team": "allies"}
    solo = {"player_id": "p1", "name": "Solo", "role": "Rifleman", "unit_name": None, "team": "allies", "kills": 25}
    lobby = {"player_id": "p2", "name": "Lobby", "unit_name": None, "team": None}
    teams = {"allies": {"commander": commander, "squads": {}}}
    config = stats.EndMatchStatsUserConfig()
    players, squads = stats.extract_team_view(teams, config, detailed_players={"c1": commander, "p1": solo, "p2": lobby}, game=GameEnum.HLL_WW2)
    assert [p["name"] for p in players] == ["Commander", "Solo"]
    assert not squads
    assert "Solo (25)" in stats.format_sections(players, config)[0]
    without_infantry = config.model_copy(update={"unit_types": ["commander"]})
    players, _ = stats.extract_team_view(teams, without_infantry, detailed_players={"c1": commander, "p1": solo}, game=GameEnum.HLL_WW2)
    assert [p["name"] for p in players] == ["Commander"]


@pytest.mark.parametrize(
    ("language", "allies_label", "axis_label"),
    [("en", "allies", "axis"), ("de", "Alliierte", "Achsenmächte"), ("fr", "Alliés", "Axe")],
)
def test_squad_team_names_follow_message_language(language, allies_label, axis_label):
    squad = {"type": "infantry", "players": [{"name": "Player", "kills": 3}], "kills": 3}
    teams = {"allies": {"squads": {"Able": squad}}, "axis": {"squads": {"Baker": squad}}}
    config = stats.EndMatchStatsUserConfig(language=language, include_squads=True, top_count=2)
    _, squads = stats.extract_team_view(teams, config)
    assert [squad["name"] for squad in squads] == [
        f"Able ({allies_label})", f"Baker ({axis_label})"
    ]
    assert all(squad["name"] in stats.format_stats([], config, squads) for squad in squads)
