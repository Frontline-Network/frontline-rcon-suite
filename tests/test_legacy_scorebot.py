import logging

from rcon.types import PlayerStatsEnum
from rcon.user_config.legacy_scorebot import ScorebotUserConfig
from rcon.user_config import utils as user_config_utils


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


def test_missing_legacy_scorebot_config_is_an_info_fallback(monkeypatch, caplog):
    monkeypatch.setenv("HLL_DB_URL", "postgresql://example.invalid/crcon")
    monkeypatch.setattr(user_config_utils, "get_user_config", lambda *_args, **_kwargs: None)

    with caplog.at_level(logging.INFO):
        config = ScorebotUserConfig.load_from_db()

    assert config == ScorebotUserConfig()
    matching_records = [
        record
        for record in caplog.records
        if ScorebotUserConfig.KEY() in record.getMessage()
    ]
    assert matching_records
    assert all(record.levelno < logging.ERROR for record in matching_records)
