from unittest.mock import Mock
from types import SimpleNamespace
import pytest

from rcon.seed_vip import service


def test_failed_webhook_does_not_stop_other_hooks_or_expose_url(monkeypatch, caplog):
    secret = "https://example.invalid/token-secret"
    failed = Mock()
    failed.send.side_effect = RuntimeError(secret)
    success = Mock()
    create = Mock(side_effect=[failed, success])
    monkeypatch.setattr(service.discord.SyncWebhook, "from_url", create)
    embed = object()

    service.send_seed_hooks([SimpleNamespace(url=secret), SimpleNamespace(url="other")], embed)

    success.send.assert_called_once_with(embed=embed)
    assert "RuntimeError" in caplog.text
    assert secret not in caplog.text


def test_seed_service_error_does_not_leak_exception_details(monkeypatch, caplog):
    secret = "fake-webhook-secret"
    config = SimpleNamespace(language=None, player_announce_thresholds=[])
    monkeypatch.setattr(service.SeedVIPUserConfig, "load_from_db", Mock(side_effect=[config, RuntimeError(secret)]))
    monkeypatch.setattr(service, "get_rcon_api", Mock())
    monkeypatch.setattr(service, "NotificationOutbox", Mock())
    monkeypatch.setattr(service, "get_server_number", Mock(return_value="1"))
    with pytest.raises(RuntimeError) as error:
        service.run()
    assert secret not in str(error.value)
    assert error.value.__suppress_context__ is True
    assert secret not in caplog.text


def test_initial_seed_configuration_error_is_sanitized(monkeypatch):
    secret = "fake-webhook-secret"
    monkeypatch.setattr(service.SeedVIPUserConfig, "load_from_db", Mock(side_effect=RuntimeError(secret)))
    with pytest.raises(RuntimeError) as error:
        service.run()
    assert secret not in str(error.value)
    assert error.value.__suppress_context__ is True


def test_get_server_snapshot_returns_players_and_gamestate(monkeypatch):
    players = object()
    gamestate = {"num_allied_players": 2, "num_axis_players": 3}
    monkeypatch.setattr(service, "get_online_players", Mock(return_value=players))
    monkeypatch.setattr(service, "get_gamestate", Mock(return_value=gamestate))

    assert service.get_server_snapshot(Mock()) == (players, gamestate)


def test_get_server_snapshot_tolerates_transient_rcon_failure(monkeypatch):
    monkeypatch.setattr(
        service,
        "get_online_players",
        Mock(side_effect=RuntimeError("temporary RCON failure")),
    )
    get_gamestate = Mock()
    monkeypatch.setattr(service, "get_gamestate", get_gamestate)
    warning = Mock()
    monkeypatch.setattr(service.logger, "warning", warning)

    assert service.get_server_snapshot(Mock()) is None
    get_gamestate.assert_not_called()
    warning.assert_called_once()
    assert "retrying on the next poll" in warning.call_args.args[0]


def test_get_server_snapshot_retries_incomplete_result(monkeypatch):
    monkeypatch.setattr(service, "get_online_players", Mock(return_value=None))
    monkeypatch.setattr(service, "get_gamestate", Mock(return_value={}))
    warning = Mock()
    monkeypatch.setattr(service.logger, "warning", warning)

    assert service.get_server_snapshot(Mock()) is None
    warning.assert_called_once_with(
        "HLL RCON returned an incomplete Seed VIP snapshot; retrying"
    )
