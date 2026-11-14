from unittest.mock import MagicMock

import pytest

from rcon import end_match_stats as stats


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
