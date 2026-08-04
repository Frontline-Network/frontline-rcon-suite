from rcon.types import PlayerStatsEnum
from rcon.user_config.legacy_scorebot import ScorebotUserConfig


def test_legacy_scorebot_stat_names_are_normalized():
    config = ScorebotUserConfig(
        stats_to_display=[
            {"type": "TOP_STAMINA", "display_format": "deaths"},
            {"type": "TOP_KILL_STREAK", "display_format": "streak"},
            {"type": "IM_CLUMSY", "display_format": "teamkills"},
            {"type": "SURVIVORS", "display_format": "life"},
        ]
    )

    assert [stat.type for stat in config.stats_to_display] == [
        PlayerStatsEnum.DEATHS,
        PlayerStatsEnum.KILLS_STREAK,
        PlayerStatsEnum.TEAMKILLS,
        PlayerStatsEnum.LONGEST_LIFE_SECS,
    ]


def test_current_scorebot_stat_names_remain_unchanged():
    config = ScorebotUserConfig(
        stats_to_display=[
            {"type": "kills", "display_format": "kills"},
            {"type": "time_seconds", "display_format": "time"},
        ]
    )

    assert [stat.type for stat in config.stats_to_display] == [
        PlayerStatsEnum.KILLS,
        PlayerStatsEnum.TIME_SECONDS,
    ]
