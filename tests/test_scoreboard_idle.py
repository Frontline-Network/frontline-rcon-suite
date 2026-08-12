import os
from unittest import mock

import pytest

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon import scoreboard
from rcon.user_config.scoreboard import ScoreboardUserConfig


class StopScoreboard(BaseException):
    pass


@pytest.mark.parametrize(
    "config, expected_warning",
    [
        (
            ScoreboardUserConfig(),
            "Public Scoreboard URL is not configured",
        ),
        (
            ScoreboardUserConfig(public_scoreboard_url="https://example.com"),
            "No Discord webhooks are configured",
        ),
    ],
)
def test_scoreboard_waits_for_missing_configuration(
    monkeypatch, config, expected_warning
):
    monkeypatch.setattr(
        scoreboard.ScoreboardUserConfig,
        "load_from_db",
        lambda: config,
    )
    monkeypatch.setattr("rcon.api_commands.get_rcon_api", lambda: object())
    warning = mock.Mock()
    monkeypatch.setattr(scoreboard.logger, "warning", warning)

    def stop_after_first_wait(seconds):
        assert seconds == scoreboard.SCOREBOARD_CONFIG_RETRY_SECONDS
        raise StopScoreboard

    monkeypatch.setattr(scoreboard.time, "sleep", stop_after_first_wait)

    with pytest.raises(StopScoreboard):
        scoreboard.run()

    warning.assert_called_once()
    assert expected_warning in warning.call_args.args[0]
