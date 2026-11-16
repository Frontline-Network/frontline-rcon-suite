import os
from datetime import datetime, timedelta, timezone
import time

import pytest

os.environ["HLL_MAINTENANCE_CONTAINER"] = "1"
from rcon.models import Maps, PlayerID, PlayerSoldier, PlayerStats, calc_weapon_type_usage
from rcon.player_stats import BaseStats, LiveStats, Streaks
from rcon.types import AllLogTypes, PlayerTeamAssociation, PlayerTeamConfidence
from rcon.utils import get_default_player_stats
from rcon.maps import Team


def test_teamkill_death_ends_kill_streak():
    calc = BaseStats.__new__(BaseStats)
    stats = get_default_player_stats()
    streaks = Streaks()
    player = {"name": "test", "player_id": "one"}
    for index, (action, attacker, victim) in enumerate([
        (AllLogTypes.kill, "one", "enemy"),
        (AllLogTypes.team_kill, "ally", "one"),
        (AllLogTypes.kill, "one", "enemy"),
    ]):
        calc._calc_streaks(stats, player, {"action": action, "timestamp_ms": index * 1000,
            "player_id_1": attacker, "player_id_2": victim}, streaks)
    assert stats["kills_streak"] == 1
    assert streaks.kill == 1


def test_shortest_life_records_first_positive_duration_and_tracks_minimum():
    calc = BaseStats.__new__(BaseStats)
    stats = get_default_player_stats()
    stats["last_spawn"] = datetime(2026, 1, 1)
    calc._process_death_time(stats["last_spawn"] + timedelta(seconds=120), stats)
    assert stats["shortest_life_secs"] == 120
    calc._process_death_time(stats["last_spawn"] + timedelta(seconds=180), stats)
    calc._process_death_time(stats["last_spawn"] + timedelta(seconds=60), stats)
    assert stats["shortest_life_secs"] == 60
    assert stats["longest_life_secs"] == 180


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="requires POSIX timezone support")
@pytest.mark.parametrize("zone", ["UTC", "Europe/Berlin", "America/New_York"])
@pytest.mark.parametrize("start", [
    datetime(2026, 1, 15, 12, tzinfo=timezone.utc),
    datetime(2026, 10, 25, 0, 59, tzinfo=timezone.utc),
])
def test_lifetime_uses_actual_event_instants_across_timezones(monkeypatch, zone, start):
    original_tz = os.environ.get("TZ")
    try:
        monkeypatch.setenv("TZ", zone)
        time.tzset()
        calc = BaseStats.__new__(BaseStats)
        stats = get_default_player_stats()
        stats["last_spawn"] = start.astimezone(timezone(timedelta(hours=2)))
        player = {"name": "Player", "player_id": "p"}
        log = {"action": AllLogTypes.kill,
               "timestamp_ms": int((start + timedelta(seconds=120)).timestamp() * 1000),
               "player_id_1": "enemy", "player_id_2": "p"}
        calc._calc_streaks(stats, player, log, Streaks())
        assert stats["longest_life_secs"] == 120
        assert stats["shortest_life_secs"] == 120
    finally:
        if original_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original_tz
        time.tzset()


def test_missing_event_timestamp_does_not_break_streak_or_change_life():
    calc = BaseStats.__new__(BaseStats)
    stats = get_default_player_stats()
    stats["last_spawn"] = datetime(2026, 1, 1, tzinfo=timezone.utc)
    streaks = Streaks()
    calc._calc_streaks(stats, {"name": "Player", "player_id": "p"},
        {"action": AllLogTypes.kill, "player_id_1": "enemy", "player_id_2": "p"}, streaks)
    assert streaks.death == 1
    assert stats["last_spawn"] is None
    assert stats["longest_life_secs"] == 0


def test_live_first_appearance_preserves_aware_session_instant():
    start = datetime(2026, 1, 1, 13, tzinfo=timezone(timedelta(hours=1)))
    calc = LiveStats.__new__(LiveStats)
    assert calc._get_player_first_appearance({"profile": {"sessions": [{"start": start}]}}) == datetime(2026, 1, 1, 12, tzinfo=timezone.utc)


@pytest.mark.skipif(not hasattr(time, "tzset"), reason="requires POSIX timezone support")
def test_live_first_appearance_converts_legacy_local_wall_time(monkeypatch):
    original_tz = os.environ.get("TZ")
    try:
        monkeypatch.setenv("TZ", "Europe/Berlin")
        time.tzset()
        calc = LiveStats.__new__(LiveStats)
        player = {"profile": {"sessions": [{"start": datetime(2026, 1, 1, 13)}]}}
        assert calc._get_player_first_appearance(player) == datetime(2026, 1, 1, 12, tzinfo=timezone.utc)
    finally:
        if original_tz is None:
            os.environ.pop("TZ", None)
        else:
            os.environ["TZ"] = original_tz
        time.tzset()


def test_canadian_weapon_identifies_allied_team():
    stats = PlayerStats(weapons={"Canadian Sten Mk.II": 5}, death_by_weapons={})
    assert stats.detect_team()["side"] == Team.ALLIES


def test_vietnam_stats_use_the_match_game_catalog():
    stats = PlayerStats(
        player=PlayerID(player_id="test-player"),
        map=Maps(game=2),
        weapons={"M16A1": 5},
        death_by_weapons={"M16A1": 2},
    )
    assert calc_weapon_type_usage(stats.weapons, game=2) == {"infantry": 5}
    assert stats.detect_team()["side"] == Team.ALLIES
    result = stats.to_dict()
    assert result["kills_by_type"] == {"infantry": 5}
    assert result["deaths_by_type"] == {"infantry": 2}
    assert result["team"]["side"] == Team.ALLIES


def test_unknown_game_does_not_guess_a_catalog():
    assert calc_weapon_type_usage({"M1 GARAND": 1}, game=999) == {}


class StaticStats(BaseStats):
    def _get_player_session_time(self, player):
        return 0

    def _get_player_first_appearance(self, player):
        return None


def test_computed_stats_include_profile_platform():
    profile = PlayerID(player_id="player-id")
    profile.soldier = PlayerSoldier(platform="xbl")
    stats = StaticStats.__new__(StaticStats).get_stats_by_player(
        indexed_logs={},
        players=[{"name": "Player", "player_id": "player-id"}],
        profiles_by_id={"player-id": profile},
    )

    assert stats["player-id"]["platform"] == "xbl"


def test_computed_stats_prefer_current_platform():
    profile = PlayerID(player_id="player-id")
    profile.soldier = PlayerSoldier(platform="xbl")
    stats = StaticStats.__new__(StaticStats).get_stats_by_player(
        indexed_logs={},
        players=[
            {
                "name": "Player",
                "player_id": "player-id",
                "platform": "steam",
            }
        ],
        profiles_by_id={"player-id": profile},
    )

    assert stats["player-id"]["platform"] == "steam"


def test_persisted_stats_include_profile_platform():
    player = PlayerID(player_id="player-id")
    player.soldier = PlayerSoldier(platform="steam")
    stats = PlayerStats(name="Player", weapons={}, death_by_weapons={})
    stats.player = player

    assert stats.to_dict()["platform"] == "steam"


def test_detects_no_kills_no_deaths():
    p = PlayerStats(weapons=dict(), death_by_weapons=dict())

    assert p.detect_team() == PlayerTeamAssociation(side=Team.UNKNOWN, confidence=PlayerTeamConfidence.STRONG, ratio=0)


@pytest.mark.parametrize(
    "weapon, expected", [
        ('M1A1 THOMPSON', Team.ALLIES),
        ('PPSH 41', Team.ALLIES),
        ('Sten Gun Mk.V', Team.ALLIES),
        ('GEWEHR 43', Team.AXIS),
    ]
)
def test_detects_weapons(weapon, expected):
    p = PlayerStats(weapons={weapon: 1}, death_by_weapons=dict())

    assert p.detect_team() == PlayerTeamAssociation(side=expected, confidence=PlayerTeamConfidence.STRONG, ratio=100)


@pytest.mark.parametrize(
    "death, expected", [
        ('M1A1 THOMPSON', Team.AXIS),
        ('PPSH 41', Team.AXIS),
        ('Sten Gun Mk.V', Team.AXIS),
        ('GEWEHR 43', Team.ALLIES),
    ]
)
def test_detects_death_by_weapon(death, expected):
    p = PlayerStats(weapons=dict(), death_by_weapons={death: 1})

    assert p.detect_team() == PlayerTeamAssociation(side=expected, confidence=PlayerTeamConfidence.STRONG, ratio=100)


def test_same_numbers():
    p = PlayerStats(weapons={'M1A1 THOMPSON': 1}, death_by_weapons={'M1A1 THOMPSON': 1})

    assert p.detect_team() == PlayerTeamAssociation(side=Team.UNKNOWN, confidence=PlayerTeamConfidence.MIXED, ratio=50)


def test_multiple_sides():
    p = PlayerStats(weapons={'M1A1 THOMPSON': 4, 'GEWEHR 43': 3, 'STG44': 3}, death_by_weapons={'GEWEHR 43': 1})

    assert p.detect_team() == PlayerTeamAssociation(side=Team.AXIS, confidence=PlayerTeamConfidence.MIXED, ratio=54.55)


def test_prefer_more_kills():
    p = PlayerStats(weapons={'M1A1 THOMPSON': 1, 'GEWEHR 43': 2}, death_by_weapons=dict())

    assert p.detect_team() == PlayerTeamAssociation(side=Team.AXIS, confidence=PlayerTeamConfidence.MIXED, ratio=66.67)


def test_detect_complex():
    p = PlayerStats(weapons={
        '88 KWK 36 L/56 [Sd.Kfz.181 Tiger 1]': 21,
        'COAXIAL MG34 [Sd.Kfz.181 Tiger 1]': 3,
        'COAXIAL MG34': 1,
        '50mm KwK 39/1 [Sd.Kfz.234 Puma]': 1,
    }, death_by_weapons={
        'BAZOOKA': 2,
        'SATCHEL': 1,
        'M1 GARAND': 1,
    })

    assert p.detect_team() == PlayerTeamAssociation(side=Team.AXIS, confidence=PlayerTeamConfidence.STRONG, ratio=100)


def test_detect_complex_inf():
    p = PlayerStats(weapons={
        'M1 GARAND': 31,
        'BAZOOKA': 1,
        'MK2 GRENADE': 1,
        'M1A1 THOMPSON': 1,
        'BROWNING M1919': 2,
    }, death_by_weapons={
        'GEWEHR 43': 9,
        'MG42': 3,
        'MP40': 1,
        'STG44': 1,
        'FG42 x4': 2,
        '150MM HOWITZER [sFH 18]': 1,
        '20MM KWK 30 [Sd.Kfz.121 Luchs]': 1,
    })

    assert p.detect_team() == PlayerTeamAssociation(side=Team.ALLIES, confidence=PlayerTeamConfidence.STRONG, ratio=100)
    assert calc_weapon_type_usage(p.weapons) == {
        'bazooka': 1,
        'grenade': 1,
        'machine_gun': 2,
        'infantry': 32,
    }
    assert calc_weapon_type_usage(p.death_by_weapons) == {
        'artillery': 1,
        'armor': 1,
        'infantry': 11,
        'machine_gun': 3,
        'sniper': 2,
    }


def test_detect_ignores_some_other_side():
    p = PlayerStats(weapons={
        'M1 GARAND': 45,
        'M1A1 THOMPSON': 4,
        'MK2 GRENADE': 3,
        'BAZOOKA': 2,
    }, death_by_weapons={
        'GEWEHR 43': 28,
        'MP40': 7,
        'KARABINER 98K': 7,
        'FG42 x4': 6,
        '150MM HOWITZER [sFH 18]': 5,
        'STG44': 3,
        'COAXIAL MG34 [Sd.Kfz.181 Tiger 1]': 2,
        '88 KWK 36 L/56 [Sd.Kfz.181 Tiger 1]': 2,
        'MG42': 1,
        'SATCHEL': 1,
        'BOMBING RUN': 1,
        # this is a teamkill or a wrongly attributed kill or a kill by an explosion of a vehicle or something
        # it should not result in a MIXED team confidence
        'Sherman M4A3(75)W': 1,
    })

    assert p.detect_team() == PlayerTeamAssociation(side=Team.ALLIES, confidence=PlayerTeamConfidence.STRONG, ratio=99.12)
