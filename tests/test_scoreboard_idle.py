import os
import logging
import threading
from types import SimpleNamespace
from unittest import mock

import pytest
from sqlalchemy import text

os.environ.setdefault("SERVER_NUMBER", "1")
os.environ.setdefault("HLL_MAINTENANCE_CONTAINER", "1")

from rcon import scoreboard
from rcon.user_config.scoreboard import ScoreboardUserConfig
from rcon.user_config import scoreboard as scoreboard_config


class StopScoreboard(BaseException):
    pass


def test_webhook_repr_does_not_reveal_url():
    secret = "https://example.invalid/webhook-token"
    hook = scoreboard.Webhook(url=secret, server_number="1")
    assert secret not in repr(hook)
    assert secret not in str(hook)
    assert "<redacted>" in repr(hook)


def test_legacy_scoreboard_migration_does_not_log_urls(monkeypatch, caplog):
    secret = "fake-webhook-token"
    legacy = SimpleNamespace(base_scoreboard_url="https://example.invalid/private-" + secret,
                             webhook_urls=["https://example.invalid/" + secret])
    monkeypatch.setattr(scoreboard_config.ScoreboardUserConfig, "load_from_db", lambda: ScoreboardUserConfig())
    monkeypatch.setattr(scoreboard_config.ScorebotUserConfig, "load_from_db", lambda: legacy)
    saved = mock.Mock()
    monkeypatch.setattr(scoreboard_config.ScoreboardUserConfig, "save_to_db", saved)
    with caplog.at_level(logging.INFO, logger=scoreboard_config.logger.name):
        scoreboard_config._port_legacy_scorebot_urls()
    saved.assert_called_once()
    assert "migration" in caplog.text
    assert secret not in caplog.text


def test_scoreboard_failure_does_not_leak_secret_to_logs_or_supervisor(monkeypatch, caplog):
    secret = "fake-webhook-secret"
    monkeypatch.setattr("rcon.api_commands.get_rcon_api", lambda: object())
    monkeypatch.setattr(scoreboard.ScoreboardUserConfig, "load_from_db", mock.Mock(side_effect=RuntimeError(secret)))
    with pytest.raises(RuntimeError) as error:
        scoreboard.run()
    assert secret not in str(error.value)
    assert error.value.__suppress_context__ is True
    assert secret not in caplog.text


def test_vip_count_uses_compact_live_roster():
    rcon_api = mock.Mock()
    rcon_api.get_team_view.return_value = {
        "allies": {
            "squads": {
                "able": {"players": [{"is_vip": True}, {"is_vip": False}]}
            },
            "commander": {"is_vip": True},
        },
        "axis": {"squads": {}, "commander": None},
    }

    assert scoreboard.get_vip_count_by_team(rcon_api) == {
        "allies": 2,
        "axis": 0,
        "none": 0,
    }
    rcon_api.get_team_view.assert_called_once_with(compact=True)


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

    def stop_after_first_wait(_stop_event, seconds):
        assert seconds == scoreboard.SCOREBOARD_CONFIG_RETRY_SECONDS
        raise StopScoreboard

    monkeypatch.setattr(scoreboard, "wait", stop_after_first_wait)

    with pytest.raises(StopScoreboard):
        scoreboard.run()

    warning.assert_called_once()
    assert expected_warning in warning.call_args.args[0]


def test_scoreboard_database_can_be_reused_after_runtime_thread_restart(
    monkeypatch, tmp_path
):
    monkeypatch.setattr(scoreboard, "VOLUME_PATH", tmp_path)
    monkeypatch.setattr(
        scoreboard,
        "DB_PATH",
        f"{tmp_path.as_posix()}/scoreboard.db",
    )
    monkeypatch.setattr(scoreboard, "ENGINE", None)
    engine = scoreboard.initialize_database()
    errors = []

    def use_database_from_replacement_thread():
        try:
            with scoreboard.enter_session() as session:
                session.execute(text("SELECT 1"))
        except Exception as exc:  # pragma: no cover - asserted below
            errors.append(exc)

    replacement = threading.Thread(target=use_database_from_replacement_thread)
    replacement.start()
    replacement.join(timeout=2)

    engine.dispose()
    assert not replacement.is_alive()
    assert errors == []
